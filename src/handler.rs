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
/// Uses the cached handler signature to inject path params and coerce types.
/// Returns (body_str, content_type, status_code, optional_headers).
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

    // Skip building Request object for simple handlers if no middlewares exist
    let param_names = &handler_sig.param_names;
    let needs_request = !state.middlewares.is_empty() || param_names.iter().any(|n| n == "request");
    
    let mut py_request_wrapped_opt: Option<PyObject> = None;
    
    // Only allocate query string HashMap if there's a param request AND there's actually a query string
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

        // 1. Execute Before Middlewares
        py_request_wrapped = crate::middleware::execute_before_middlewares(py, &state.middlewares, py_request_wrapped);
        py_request_wrapped_opt = Some(py_request_wrapped.clone_ref(py));
    }

    // Populate kwargs based on handler signature expected names
    // 1. Path Params (coerced)
    for (key, value) in path_params {
        if call_kwargs_opt.is_none() {
            call_kwargs_opt = Some(PyDict::new(py));
        }
        if let Some(annotation) = handler_sig.param_types.get(key) {
            let coerced = annotation.bind(py).call1((value,))?;
            call_kwargs_opt.as_ref().unwrap().set_item(key, coerced)?;
        } else {
            call_kwargs_opt.as_ref().unwrap().set_item(key, value)?;
        }
    }

    // Use cached parameter names (computed once at startup)

    // Resolve Dependencies (only for handlers that use Depends)
    if handler_sig.has_depends {
        if let Some(ref resolve_fn_obj) = handler_sig.resolve_deps_fn {
            let resolve_fn = resolve_fn_obj.bind(py);
            if let Ok(resolved_dict) = resolve_fn.call1((handler,)) {
                if let Ok(dict) = resolved_dict.downcast::<PyDict>() {
                    if call_kwargs_opt.is_none() {
                        call_kwargs_opt = Some(PyDict::new(py));
                    }
                    for (k, v) in dict {
                        call_kwargs_opt.as_ref().unwrap().set_item(k, v)?;
                    }
                }
            }
        }
    }

    // 2. Request / BackgroundTask object injection
    let mut injected_task: Option<PyObject> = None;
    for name in param_names {
        let is_injected = call_kwargs_opt.as_ref().map_or(false, |k| k.contains(name).unwrap_or(false));
        if is_injected {
            continue;
        }

        if name == "request" {
            if let Some(ref req_obj) = py_request_wrapped_opt {
                if call_kwargs_opt.is_none() {
                    call_kwargs_opt = Some(PyDict::new(py));
                }
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
                                    if call_kwargs_opt.is_none() {
                                        call_kwargs_opt = Some(PyDict::new(py));
                                    }
                                    call_kwargs_opt.as_ref().unwrap().set_item(name, &obj)?;
                                    injected_task = Some(obj);
                                }
                            }
                        }
                    } else if name_str == "UploadFile" {
                        if let Some((filename, content_type, file_data)) = form_files.get(name) {
                            if let Ok(uploads_mod) = py.import("ignyx.uploads") {
                                if let Ok(upload_cls) = uploads_mod.getattr("UploadFile") {
                                    let data_bytes = pyo3::types::PyBytes::new(py, file_data);
                                    if let Ok(upload_obj) = upload_cls.call1((filename, content_type, data_bytes)) {
                                        if call_kwargs_opt.is_none() {
                                            call_kwargs_opt = Some(PyDict::new(py));
                                        }
                                        call_kwargs_opt.as_ref().unwrap().set_item(name, upload_obj)?;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        } else if let Some(text) = form_fields.get(name) {
            if call_kwargs_opt.is_none() {
                call_kwargs_opt = Some(PyDict::new(py));
            }
            call_kwargs_opt.as_ref().unwrap().set_item(name, text)?;
        }
    }

    // 3. Body Injection (with Pydantic v2 validation support)
    let needs_body_inject = param_names.iter().any(|n| n == "body")
        && call_kwargs_opt.as_ref().map_or(true, |k| !k.contains("body").unwrap_or(false));

    if needs_body_inject {
        let is_json = headers
            .iter()
            .find(|(k, _)| k.as_str().eq_ignore_ascii_case("content-type"))
            .map(|(_, v)| v.to_str().unwrap_or("").contains("application/json"))
            .unwrap_or(false);
        
        if is_json && !body_bytes.is_empty() {
            if let Ok(value) = serde_json::from_slice::<serde_json::Value>(body_bytes) {
                if let Ok(py_obj) = crate::request::json_value_to_py(py, &value) {
                    // Use cached Pydantic model check (computed once at startup)
                    let mut used_pydantic = false;
                    if let Some(ref model_class_obj) = handler_sig.pydantic_body_model {
                        used_pydantic = true;
                        let model_class = model_class_obj.bind(py);
                        match model_class.call_method1("model_validate", (&py_obj,)) {
                            Ok(model_instance) => {
                                if call_kwargs_opt.is_none() {
                                    call_kwargs_opt = Some(PyDict::new(py));
                                }
                                call_kwargs_opt.as_ref().unwrap().set_item("body", model_instance)?;
                            }
                            Err(validation_err) => {
                                let err_obj = validation_err.value(py);
                                let detail = if let Ok(errors_method) = err_obj.call_method0("errors") {
                                    let json_mod = py.import("json")?;
                                    json_mod.call_method1("dumps", (errors_method,))?.extract::<String>()?
                                } else {
                                    err_obj.str()?.extract::<String>()?
                                };
                                let error_body = format!(
                                    "{{\"error\": \"Validation failed\", \"detail\": {}}}",
                                    detail
                                );
                                return Ok((error_body, "application/json".to_string(), 422, None, None));
                            }
                        }
                    }

                    if !used_pydantic {
                        if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                        call_kwargs_opt.as_ref().unwrap().set_item("body", py_obj)?;
                    }
                } else {
                    if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                    call_kwargs_opt.as_ref().unwrap().set_item("body", py.None())?;
                }
            } else {
                if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                call_kwargs_opt.as_ref().unwrap().set_item("body", py.None())?;
            }
        } else {
            // Raw text or bytes fallback
            if let Ok(text) = String::from_utf8(body_bytes.to_vec()) {
                if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                call_kwargs_opt.as_ref().unwrap().set_item("body", text)?;
            } else {
                if call_kwargs_opt.is_none() { call_kwargs_opt = Some(PyDict::new(py)); }
                call_kwargs_opt.as_ref().unwrap().set_item("body", py.None())?;
            }
        }
    }

    // 4. Query Params Injection
    for (key, value) in &query_params_map {
        if param_names.contains(key) {
            // Check if key already exists in kwargs (e.g., from path params or dependencies)
            if call_kwargs_opt.is_none() {
                call_kwargs_opt = Some(PyDict::new(py));
            }
            let kwargs = call_kwargs_opt.as_ref().unwrap();
            if !kwargs.contains(key)? {
                if let Some(annotation) = handler_sig.param_types.get(key) {
                    if let Ok(coerced) = annotation.bind(py).call1((value,)) {
                        kwargs.set_item(key, coerced)?;
                    } else {
                        kwargs.set_item(key, value)?;
                    }
                } else {
                    kwargs.set_item(key, value)?;
                }
            }
        }
    }

    // Call the handler
    let mut result = match if let Some(kwargs) = call_kwargs_opt {
        handler.call(py, (), Some(&kwargs))
    } else {
        handler.call0(py)
    } {
        Ok(res) => {
            // Use cached is_async flag (computed once at startup, not per-request)
            if handler_sig.is_async {
                let awaited = crate::server::ASYNCIO_LOOP.with(|loop_cell| {
                    let mut loop_opt = loop_cell.borrow_mut();
                    
                    // Create loop on this thread if it doesn't exist
                    if loop_opt.is_none() {
                        let new_loop_func = state.py_refs.new_event_loop.clone_ref(py);
                        if !new_loop_func.is_none(py) {
                            if let Ok(new_loop) = new_loop_func.bind(py).call0() {
                                let set_loop_func = state.py_refs.set_event_loop.clone_ref(py);
                                if !set_loop_func.is_none(py) {
                                    let _ = set_loop_func.bind(py).call1((&new_loop,));
                                }
                                if let Ok(run_method) = new_loop.getattr("run_until_complete") {
                                    *loop_opt = Some((new_loop.unbind(), run_method.unbind()));
                                }
                            }
                        }
                    }
                    
                    // Execute the coroutine on the thread-local persistent loop
                    if let Some(ref cached) = *loop_opt {
                        Ok::<PyObject, PyErr>(cached.1.bind(py).call1((&res,))?.unbind())
                    } else {
                        // Extreme fallback
                        let asyncio = py.import("asyncio")?;
                        Ok::<PyObject, PyErr>(asyncio.call_method1("run", (&res,))?.unbind())
                    }
                })?;
                
                awaited
            } else {
                res
            }
        }
        Err(err) => {
            // On Error Middlewares
            let mut error_response: Option<PyObject> = None;
            for mw in &state.middlewares {
                if let Ok(method) = mw.getattr(py, "on_error") {
                    if let Some(ref req_obj) = py_request_wrapped_opt {
                        if let Ok(res) = method.call1(py, (req_obj, err.clone_ref(py))) {
                            if !res.is_none(py) {
                                error_response = Some(res);
                                break;
                            }
                        }
                    }
                }
            }
            if let Some(res) = error_response {
                res
            } else {
                if let Ok(exceptions_mod) = py.import("ignyx.exceptions") {
                    if let Ok(http_exc_class) = exceptions_mod.getattr("HTTPException") {
                        if err.value(py).is_instance(&http_exc_class).unwrap_or(false) {
                            let exc_obj = err.value(py);
                            let status_code: u16 = exc_obj.getattr("status_code").and_then(|v| v.extract()).unwrap_or(500);
                            
                            // Get detail, maybe None
                            let detail = exc_obj.getattr("detail").map(|v| v.to_string()).unwrap_or_else(|_| "".to_string());
                            
                            let mut custom_headers = None;
                            if let Ok(headers_obj) = exc_obj.getattr("headers") {
                                if let Ok(headers_dict) = headers_obj.downcast::<PyDict>() {
                                    let mut hmap = HashMap::new();
                                    for (k, v) in headers_dict {
                                        if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) {
                                            hmap.insert(ks, vs);
                                        }
                                    }
                                    if !hmap.is_empty() {
                                        custom_headers = Some(hmap);
                                    }
                                }
                            }
                            
                            let error_body = serde_json::json!({"detail": detail}).to_string();
                            return Ok((error_body, "application/json".to_string(), status_code, custom_headers, None));
                        }
                    }
                }
                return Err(err);
            }
        }
    };

    // 2. Execute After Middlewares (in reverse order)
    if let Some(ref req_obj) = py_request_wrapped_opt {
        result = crate::middleware::execute_after_middlewares(py, &state.middlewares, req_obj, result);
    }

    // Parse the result
    // Can be a tuple: (body, status) or (body, status, headers)
    let bound_result = result.into_bound(py);
    
    let mut actual_result: Bound<'_, PyAny> = bound_result.clone();
    let mut status_code = 200;
    let mut custom_headers = None;

    if bound_result.is_instance_of::<PyTuple>() {
        let tuple = bound_result.downcast::<PyTuple>()?;
        let len = tuple.len();
        if len >= 2 {
            actual_result = tuple.get_item(0)?.clone();
            status_code = tuple.get_item(1)?.extract::<u16>()?;
        }
        if len >= 3 {
            if let Ok(headers_dict) = tuple.get_item(2)?.downcast::<PyDict>() {
                let mut hmap = HashMap::new();
                for (k, v) in headers_dict {
                    let ks: String = k.extract::<String>()?;
                    let vs: String = v.extract::<String>()?;
                    hmap.insert(ks, vs);
                }
                custom_headers = Some(hmap);
            }
        }
    }

    // Check if result is a BaseResponse instance (has content_type attr + render method)
    if actual_result.hasattr("content_type")? && actual_result.hasattr("render")? && !actual_result.is_instance_of::<PyDict>() && !actual_result.is_instance_of::<PyString>() {
        let ct: String = actual_result.getattr("content_type")?.extract()?;
        let sc: u16 = actual_result.getattr("status_code")?.extract()?;
        let rendered = actual_result.call_method0("render")?;
        let body_str: String = if let Ok(s) = rendered.extract::<String>() {
            s
        } else if let Ok(b) = rendered.extract::<Vec<u8>>() {
            // FileResponse returns bytes — convert to string (lossy)
            String::from_utf8_lossy(&b).to_string()
        } else {
            rendered.str()?.extract::<String>()?
        };
        // Extract headers from the response object
        let resp_headers: Option<HashMap<String, String>> = if let Ok(hdict) = actual_result.getattr("headers") {
            if let Ok(dict) = hdict.downcast::<PyDict>() {
                let mut hmap = HashMap::new();
                for (k, v) in dict {
                    if let (Ok(ks), Ok(vs)) = (k.extract::<String>(), v.extract::<String>()) {
                        hmap.insert(ks, vs);
                    }
                }
                if hmap.is_empty() { custom_headers } else {
                    // Merge with any existing custom_headers
                    match custom_headers {
                        Some(mut existing) => { existing.extend(hmap); Some(existing) }
                        None => Some(hmap)
                    }
                }
            } else {
                custom_headers
            }
        } else {
            custom_headers
        };
        return Ok((body_str, ct, sc, resp_headers, injected_task));
    }

    // Convert the actual body result to a response string
    let (body_str, content_type) = if actual_result.is_instance_of::<PyDict>() || actual_result.is_instance_of::<pyo3::types::PyList>() {
        // Dict/List → JSON
        let dumps_obj = state.py_refs.json_dumps.clone_ref(py);
        let json_str: String = if !dumps_obj.is_none(py) {
            dumps_obj.bind(py).call1((&actual_result,))?.extract()?
        } else {
            let json_mod = py.import("json")?;
            json_mod.call_method1("dumps", (&actual_result,))?.extract()?
        };
        (json_str, "application/json".to_string())
    } else if actual_result.is_instance_of::<PyString>() {
        let s: String = actual_result.extract()?;
        // Auto-detect HTML
        let ct = if s.trim_start().starts_with('<') {
            "text/html; charset=utf-8".to_string()
        } else {
            "text/plain; charset=utf-8".to_string()
        };
        (s, ct)
    } else {
        // Fallback: str() conversion
        let s = actual_result.str()?.extract::<String>()?;
        (s, "text/plain; charset=utf-8".to_string())
    };

    Ok((body_str, content_type, status_code, custom_headers, injected_task))
}
