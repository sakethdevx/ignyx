use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString, PyTuple};
use std::collections::HashMap;

/// Pre-computed signature for a Python handler
pub struct HandlerSignature {
    pub handler: PyObject,
    pub param_types: std::collections::HashMap<String, PyObject>,
    pub is_async: bool,
    pub param_names: Vec<String>,
    pub has_depends: bool,
    pub pydantic_body_model: Option<PyObject>,
    pub resolve_deps_fn: Option<PyObject>,
}

/// Call a Python handler with the real request data.
pub(crate) fn call_python_handler(
    py: Python<'_>,
    handler_sig: &HandlerSignature,
    method: &str,
    path: &str,
    path_params: &HashMap<String, String>,
    query_string: &str,
    headers: &hyper::HeaderMap,
    body_bytes: &[u8],
    form_fields: &HashMap<String, String>,
    form_files: &HashMap<String, (String, String, Vec<u8>)>,
    state: &crate::server::ServerState,
) -> PyResult<(String, String, u16, Option<HashMap<String, String>>, Option<PyObject>)> {
    let handler = &handler_sig.handler;
    let mut call_kwargs_opt: Option<pyo3::Bound<'_, pyo3::types::PyDict>> = None;
    let param_names = &handler_sig.param_names;
    let needs_request = !state.middlewares.is_empty() || param_names.iter().any(|n| n == "request");
    
    let mut py_request_wrapped_opt: Option<PyObject> = None;
    let mut injected_task: Option<PyObject> = None;
    
    let mut query_params_map = HashMap::new();
    let has_query_args = param_names.iter().any(|n| n != "body" && n != "request" && !path_params.contains_key(n));
    if (needs_request || has_query_args) && !query_string.is_empty() {
        query_params_map = crate::request::parse_query(query_string);
    }
    
    if needs_request {
        let mut req_headers = HashMap::new();
        for (k, v) in headers.iter() {
            req_headers.insert(k.to_string(), v.to_str().unwrap_or("").to_string());
        }
        
        let request_obj = crate::request::Request::new(
            method.to_string(),
            path.to_string(),
            req_headers,
            query_params_map.clone(),
            path_params.clone(),
            body_bytes.to_vec(),
        );
        let py_request_raw = Py::new(py, request_obj)?;
        let mut py_request_wrapped = py_request_raw.into_any();
        
        let proxy_class_obj = state.py_refs.request_class.clone_ref(py);
        if !proxy_class_obj.is_none(py) {
            let proxy_class = proxy_class_obj.bind(py);
            if let Ok(wrapper) = proxy_class.call1((&py_request_wrapped,)) {
                py_request_wrapped = wrapper.into();
            }
        }
        py_request_wrapped_opt = Some(py_request_wrapped);
    }

    // Wrap the entire execution in a result to catch all exceptions
    let execution_res = (|| -> PyResult<PyObject> {
        // Before Middlewares
        if let Some(req) = py_request_wrapped_opt.as_ref() {
            let modified = crate::middleware::execute_before_middlewares(py, &state.middlewares, req.clone_ref(py))?;
            py_request_wrapped_opt = Some(modified);
        }

        // Populate Kwargs
        for (key, value) in path_params {
            if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
            if let Some(annotation) = handler_sig.param_types.get(key) {
                let coerced = annotation.bind(py).call1((value,))?;
                call_kwargs_opt.as_ref().unwrap().set_item(key, coerced)?;
            } else {
                call_kwargs_opt.as_ref().unwrap().set_item(key, value)?;
            }
        }

        // Dependencies
        if handler_sig.has_depends {
            if let Some(ref resolve_fn_obj) = handler_sig.resolve_deps_fn {
                let resolve_fn = resolve_fn_obj.bind(py);
                let args = if let Some(ref req) = py_request_wrapped_opt {
                    PyTuple::new(py, vec![handler.clone_ref(py), req.clone_ref(py)])?
                } else {
                    PyTuple::new(py, vec![handler.clone_ref(py)])?
                };
                let resolved_dict = resolve_fn.call1(args)?;
                if let Ok(dict) = resolved_dict.downcast::<PyDict>() {
                    if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                    for (k, v) in dict {
                        call_kwargs_opt.as_ref().unwrap().set_item(k, v)?;
                    }
                }
            }
        }

        // Injection (Request, BG Task, Uploads, Form)
        for name in param_names {
            let is_injected = call_kwargs_opt.as_ref().map_or(false, |k| k.contains(name).unwrap_or(false));
            if is_injected { continue; }

            if name == "request" {
                if let Some(ref req_obj) = py_request_wrapped_opt {
                    if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                    call_kwargs_opt.as_ref().unwrap().set_item(name, req_obj)?;
                }
            } else if let Some(annotation) = handler_sig.param_types.get(name) {
                if let Ok(type_name) = annotation.getattr(py, "__name__") {
                    if let Ok(name_str) = type_name.extract::<String>(py) {
                        if name_str == "BackgroundTask" {
                            if let Ok(depends_mod) = py.import("ignyx.depends") {
                                if let Ok(bg_class) = depends_mod.getattr("BackgroundTask") {
                                    if let Ok(bg_instance) = bg_class.call0() {
                                        let obj: PyObject = bg_instance.into();
                                        if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                                        call_kwargs_opt.as_ref().unwrap().set_item(name, &obj)?;
                                        injected_task = Some(obj);
                                    }
                                }
                            }
                        } else if name_str == "UploadFile" {
                            if let Some((f, ct, d)) = form_files.get(name) {
                                if let Ok(u_mod) = py.import("ignyx.uploads") {
                                    if let Ok(u_cls) = u_mod.getattr("UploadFile") {
                                        let b = pyo3::types::PyBytes::new(py, d);
                                        if let Ok(u_obj) = u_cls.call1((f, ct, b)) {
                                            if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                                            call_kwargs_opt.as_ref().unwrap().set_item(name, u_obj)?;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } else if let Some(text) = form_fields.get(name) {
                if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                call_kwargs_opt.as_ref().unwrap().set_item(name, text)?;
            }
        }

        // Body Injection
        let needs_body = param_names.iter().any(|n| n == "body") && call_kwargs_opt.as_ref().map_or(true, |k| !k.contains("body").unwrap_or(false));
        if needs_body {
            let is_json = headers.iter().find(|(k, _)| k.as_str().eq_ignore_ascii_case("content-type")).map(|(_, v)| v.to_str().unwrap_or("").contains("application/json")).unwrap_or(false);
            if is_json && !body_bytes.is_empty() {
                if let Ok(v) = serde_json::from_slice::<serde_json::Value>(body_bytes) {
                    if let Ok(py_obj) = crate::request::json_value_to_py(py, &v) {
                        let mut used_pd = false;
                        if let Some(ref mc) = handler_sig.pydantic_body_model {
                            used_pd = true;
                            match mc.bind(py).call_method1("model_validate", (&py_obj,)) {
                                Ok(mi) => {
                                    if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                                    call_kwargs_opt.as_ref().unwrap().set_item("body", mi)?;
                                }
                                Err(ve) => {
                                    let err_obj = ve.value(py);
                                    let dt = if let Ok(em) = err_obj.call_method0("errors") {
                                        state.py_refs.json_dumps.bind(py).call1((em,))?.extract::<String>()?
                                    } else { err_obj.str()?.extract::<String>()? };
                                    let error_body = format!("{{\"error\": \"Validation failed\", \"detail\": {}}}", dt);
                                    let eb_obj = error_body.into_pyobject(py)?;
                                    let sc_obj = 422u16.into_pyobject(py)?;
                                    return Ok(pyo3::types::PyTuple::new(py, vec![eb_obj.into_any().unbind(), sc_obj.into_any().unbind()])?.into_any().unbind());
                                }
                            }
                        }
                        if !used_pd {
                            if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                            call_kwargs_opt.as_ref().unwrap().set_item("body", py_obj)?;
                        }
                    }
                }
            }
        }

        // Query
        for (k, v) in &query_params_map {
            if param_names.contains(k) {
                if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                let kw = call_kwargs_opt.as_ref().unwrap();
                if !kw.contains(k)? {
                    if let Some(ann) = handler_sig.param_types.get(k) {
                        let c = ann.bind(py).call1((v,)).unwrap_or_else(|_| v.into_pyobject(py).unwrap().into_any().unbind().bind(py).clone());
                        kw.set_item(k, c)?;
                    } else { kw.set_item(k, v)?; }
                }
            }
        }

        // Call
        let res = if let Some(kw) = call_kwargs_opt { handler.call(py, (), Some(&kw))? } else { handler.call0(py)? };

        // Handle Async
        if handler_sig.is_async {
            crate::server::ASYNCIO_LOOP.with(|loop_cell| {
                let mut loop_opt = loop_cell.borrow_mut();
                if loop_opt.is_none() {
                    let nf = state.py_refs.new_event_loop.clone_ref(py);
                    if let Ok(nl) = nf.bind(py).call0() {
                        let sf = state.py_refs.set_event_loop.clone_ref(py);
                        let _ = sf.bind(py).call1((&nl,));
                        if let Ok(rm) = nl.getattr("run_until_complete") { *loop_opt = Some((nl.unbind(), rm.unbind())); }
                    }
                }
                if let Some(ref c) = *loop_opt {
                    c.1.bind(py).call1((&res,)).map(|v| v.unbind())
                } else {
                    py.import("asyncio").and_then(|a| a.call_method1("run", (&res,))).map(|v| v.unbind())
                }
            })
        } else { Ok(res) }
    })();

    let result = match execution_res {
        Ok(res) => res,
        Err(err) => {
            let mut err_res: Option<PyObject> = None;
            for mw in &state.middlewares {
                if let Ok(m) = mw.getattr(py, "on_error") {
                    if let Some(ref r) = py_request_wrapped_opt {
                        if let Ok(or) = m.call1(py, (r, err.clone_ref(py))) {
                            if !or.is_none(py) { err_res = Some(or); break; }
                        }
                    }
                }
            }
            if let Some(er) = err_res { er } else {
                if let Ok(em) = py.import("ignyx.exceptions") {
                    if let Ok(ec) = em.getattr("HTTPException") {
                        if err.value(py).is_instance(&ec).unwrap_or(false) {
                            let eo = err.value(py);
                            let sc: u16 = eo.getattr("status_code")?.extract()?;
                            let dt: String = eo.getattr("detail")?.to_string();
                            let mut ch = None;
                            if let Ok(ho) = eo.getattr("headers") {
                                if let Ok(hd) = ho.downcast::<PyDict>() {
                                    let mut hmap = HashMap::new();
                                    for (k, v) in hd { if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) { hmap.insert(ks, vs); } }
                                    if !hmap.is_empty() { ch = Some(hmap); }
                                }
                            }
                            let eb = serde_json::json!({"detail": dt}).to_string();
                            return Ok((eb, "application/json".to_string(), sc, ch, None));
                        }
                    }
                }
                return Err(err);
            }
        }
    };

    // After Middlewares
    let mut final_res = result;
    if let Some(ref r) = py_request_wrapped_opt {
        final_res = crate::middleware::execute_after_middlewares(py, &state.middlewares, r, final_res)?;
    }

    // Parse Tuple/Response
    let bound = final_res.into_bound(py);
    let mut actual = bound.clone();
    let mut sc = 200;
    let mut ch = None;

    if bound.is_instance_of::<PyTuple>() {
        let t = bound.downcast::<PyTuple>()?;
        if t.len() >= 2 { 
            actual = t.get_item(0)?; 
            sc = t.get_item(1)?.extract::<u16>().unwrap_or(200); 
        }
        if t.len() >= 3 {
             if let Ok(hd) = t.get_item(2)?.downcast::<PyDict>() {
                 let mut hmap = HashMap::new();
                 for (k, v) in hd { 
                     if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) {
                         hmap.insert(ks, vs);
                     }
                 }
                 ch = Some(hmap);
             }
        }
        if t.len() >= 4 {
            let task_obj = t.get_item(3)?;
            if !task_obj.is_none() {
                injected_task = Some(task_obj.unbind());
            }
        }
    }

    if actual.hasattr("content_type")? && actual.hasattr("render")? && !actual.is_instance_of::<PyDict>() && !actual.is_instance_of::<PyString>() {
        let ct: String = actual.getattr("content_type")?.extract()?;
        let s_c: u16 = actual.getattr("status_code")?.extract()?;
        let rd = actual.call_method0("render")?;
        let bs: String = if let Ok(s) = rd.extract::<String>() {
            s
        } else if let Ok(b) = rd.extract::<Vec<u8>>() {
            // FileResponse/bytes — convert to string safely or return as is
            String::from_utf8_lossy(&b).to_string()
        } else {
            rd.str()?.extract::<String>()?
        };
        let resp_headers: Option<HashMap<String, String>> = if let Ok(hdict) = actual.getattr("headers") {
            if let Ok(dict) = hdict.downcast::<PyDict>() {
                 let mut hmap = ch.unwrap_or_default();
                 for (k, v) in dict { 
                     if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) {
                         hmap.insert(ks, vs);
                     }
                 }
                 if hmap.is_empty() { None } else { Some(hmap) }
            } else { ch }
        } else { ch };
        return Ok((bs, ct, s_c, resp_headers, injected_task));
    }

    let (bs, ct) = if actual.is_instance_of::<PyDict>() || actual.is_instance_of::<pyo3::types::PyList>() || actual.is_instance_of::<pyo3::types::PyBool>() || actual.is_instance_of::<pyo3::types::PyLong>() || actual.is_instance_of::<pyo3::types::PyFloat>() {
        let s: String = state.py_refs.json_dumps.bind(py).call1((&actual,))?.extract()?;
        (s, "application/json".to_string())
    } else if actual.is_instance_of::<PyString>() {
        let s: String = actual.extract()?;
        if s.trim_start().starts_with('<') { (s, "text/html; charset=utf-8".to_string()) }
        else { let js: String = state.py_refs.json_dumps.bind(py).call1((&actual,))?.extract()?; (js, "application/json".to_string()) }
    } else {
        let s: String = state.py_refs.json_dumps.bind(py).call1((&actual,))?.extract()?;
        (s, "application/json".to_string())
    };

    Ok((bs, ct, sc, ch, injected_task))
}
