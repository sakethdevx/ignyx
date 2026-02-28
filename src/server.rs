use crate::router::{Method, Router};
use bytes::Bytes;
use http_body_util::Full;
use hyper::body::Incoming;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request as HyperRequest, Response as HyperResponse};
use pyo3::prelude::*;
use std::collections::HashMap;
use std::convert::Infallible;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::runtime::Runtime;
// use futures_util::{SinkExt, StreamExt}; // Removed unused
// use tokio_tungstenite::tungstenite::Message as WsMessage; // Removed unused

/// Route handler entry: stores the Python callable and metadata.
struct RouteEntry {
    method: Method,
    path: String,
    handler: PyObject,
}

use crate::handler::HandlerSignature;

/// Shared state for the async server.
pub struct ServerState {
    pub router: Router,
    pub handlers: Vec<HandlerSignature>,
    pub middlewares: Vec<PyObject>,
    pub ws_routes: Vec<(String, PyObject)>,
    pub not_found_handler: Option<PyObject>,
    pub shutdown_handlers: Vec<PyObject>,
    pub py_refs: crate::pyref::PythonCachedRefs,
    pub asyncio_mod: Option<PyObject>,
}

thread_local! {
    pub static ASYNCIO_LOOP: std::cell::RefCell<Option<(PyObject, PyObject)>> = const { std::cell::RefCell::new(None) };
}

/// The Rust HTTP server exposed to Python via PyO3.
#[pyclass]
pub struct Server {
    routes: Vec<RouteEntry>,
}

#[pymethods]
impl Server {
    #[new]
    pub fn new() -> Self {
        Self { routes: Vec::new() }
    }

    /// Register a route handler. Called from Python side.
    pub fn add_route(&mut self, method: &str, path: &str, handler: PyObject) -> PyResult<()> {
        let method_enum = Method::from_str(method).ok_or_else(|| {
            pyo3::exceptions::PyValueError::new_err(format!("Unsupported method: {method}"))
        })?;

        self.routes.push(RouteEntry {
            method: method_enum,
            path: path.to_string(),
            handler,
        });

        Ok(())
    }

    /// Start the HTTP server. This blocks the calling thread.
    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (host, port, middlewares, ws_routes, not_found_handler, shutdown_handlers))]
    pub fn run(
        &self,
        py: Python<'_>,
        host: &str,
        port: u16,
        middlewares: Vec<PyObject>,
        ws_routes: Vec<(String, PyObject)>,
        not_found_handler: Option<PyObject>,
        shutdown_handlers: Vec<PyObject>,
    ) -> PyResult<()> {
        let addr: SocketAddr =
            format!("{host}:{port}")
                .parse()
                .map_err(|e: std::net::AddrParseError| {
                    pyo3::exceptions::PyValueError::new_err(e.to_string())
                })?;

        // Helper to extract type annotations
        let code = std::ffi::CString::new(
            r#"
(lambda handler: {
    k: v.annotation
    for k, v in __import__('inspect').signature(handler).parameters.items()
    if v.annotation is not __import__('inspect').Parameter.empty
} if callable(handler) else {})
"#,
        )
        .unwrap();

        let get_param_types = py.eval(&code, None, None)?;

        // Build the router and collect handler PyObjects
        let mut router = Router::new();
        let mut handlers: Vec<HandlerSignature> = Vec::new();

        let inspect = py.import("inspect")?;

        for entry in &self.routes {
            let index = router
                .insert(entry.method, &entry.path)
                .map_err(pyo3::exceptions::PyValueError::new_err)?;
            while handlers.len() <= index {
                handlers.push(HandlerSignature {
                    handler: py.None(),
                    param_types: HashMap::new(),
                    is_async: false,
                    param_names: Vec::new(),
                    has_depends: false,
                    pydantic_body_model: None,
                    resolve_deps_fn: None,
                });
            }

            let handler = entry.handler.clone_ref(py);
            let mut param_types = HashMap::new();

            if let Ok(types_dict) = get_param_types.call1((&handler,)) {
                if let Ok(dict) = types_dict.downcast::<pyo3::types::PyDict>() {
                    for (k, v) in dict {
                        if let Ok(key_str) = k.extract::<String>() {
                            param_types.insert(key_str, v.unbind());
                        }
                    }
                }
            }

            // Cache: is this an async handler?
            let is_async = inspect
                .call_method1::<&str, _>("iscoroutinefunction", (&handler,))
                .and_then(|v| v.extract::<bool>())
                .unwrap_or(false);

            // Cache: parameter names
            let mut param_names = Vec::new();
            if let Ok(sig) = inspect.call_method1("signature", (&handler,)) {
                if let Ok(params_proxy) = sig.getattr("parameters") {
                    if let Ok(keys_iter) = params_proxy.call_method0("keys") {
                        for k in keys_iter.try_iter().unwrap().flatten() {
                            if let Ok(name) = k.extract::<String>() {
                                param_names.push(name);
                            }
                        }
                    }
                }
            }

            // Cache: does this handler have Depends() defaults?
            let has_depends = if let Ok(sig) = inspect.call_method1("signature", (&handler,)) {
                if let Ok(params_proxy) = sig.getattr("parameters") {
                    if let Ok(values_iter) = params_proxy.call_method0("values") {
                        if let Ok(_iter) = values_iter.try_iter() {
                            let depends_mod = py.import("ignyx.depends").ok();
                            let depends_class = depends_mod.and_then(|m| m.getattr("Depends").ok());
                            let mut found = false;
                            for param in values_iter.try_iter().unwrap().flatten() {
                                if let Ok(default) = param.getattr("default") {
                                    if let Some(ref dep_cls) = depends_class {
                                        if default.is_instance(dep_cls).unwrap_or(false) {
                                            found = true;
                                            break;
                                        }
                                    }
                                }
                            }
                            found
                        } else {
                            false
                        }
                    } else {
                        false
                    }
                } else {
                    false
                }
            } else {
                false
            };

            // Cache: is the body param a Pydantic BaseModel?
            let pydantic_body_model = if let Some(annotation) = param_types.get("body") {
                let is_basemodel = (|| -> PyResult<bool> {
                    let pydantic = py.import("pydantic")?;
                    let base_model = pydantic.getattr("BaseModel")?;
                    let is_sub = py
                        .import("builtins")?
                        .getattr("issubclass")?
                        .call1((annotation.bind(py), base_model))?
                        .extract::<bool>()?;
                    Ok(is_sub)
                })()
                .unwrap_or(false);
                if is_basemodel {
                    Some(annotation.clone_ref(py))
                } else {
                    None
                }
            } else {
                None
            };
            let resolve_deps_fn = if has_depends {
                py.import("ignyx.depends")
                    .ok()
                    .and_then(|m| m.getattr("resolve_dependencies").ok())
                    .map(|f| f.unbind())
            } else {
                None
            };

            handlers[index] = HandlerSignature {
                handler,
                param_types,
                is_async,
                param_names,
                has_depends,
                pydantic_body_model,
                resolve_deps_fn,
            };
        }

        let req_proxy_class = py
            .import("ignyx.request")
            .ok()
            .and_then(|m| m.getattr("Request").ok())
            .map(|c| c.into());

        let json_dumps = py
            .import("json")
            .ok()
            .and_then(|m| m.getattr("dumps").ok())
            .map(|f| f.into());

        let asyncio_mod = py.import("asyncio").ok().map(|m| m.into());
        let new_event_loop = asyncio_mod
            .as_ref()
            .and_then(|m: &PyObject| m.getattr(py, "new_event_loop").ok());
        let set_event_loop = asyncio_mod
            .as_ref()
            .and_then(|m: &PyObject| m.getattr(py, "set_event_loop").ok());

        let state = Arc::new(ServerState {
            router,
            handlers,
            middlewares,
            ws_routes,
            not_found_handler,
            shutdown_handlers,
            py_refs: crate::pyref::PythonCachedRefs {
                request_class: req_proxy_class.unwrap_or_else(|| py.None()),
                json_dumps: json_dumps.unwrap_or_else(|| py.None()),
                new_event_loop: new_event_loop.unwrap_or_else(|| py.None()),
                set_event_loop: set_event_loop.unwrap_or_else(|| py.None()),
            },
            asyncio_mod,
        });

        println!("\n🔥 Ignyx server running at http://{addr}\n");

        // Flush Python stdout so the banner prints (from app.py) appear immediately
        // before GIL is released. Without this, Python's buffered stdout only flushes
        // when the GIL is re-acquired on the first request, making banner + background
        // task output appear together (falsely suggesting the task ran at startup).
        if let Ok(sys) = py.import("sys") {
            if let Ok(stdout) = sys.getattr("stdout") {
                let _ = stdout.call_method0("flush");
            }
        }

        // Release the GIL during server execution
        py.allow_threads(|| {
            let rt = Runtime::new().map_err(|e| {
                pyo3::exceptions::PyRuntimeError::new_err(format!(
                    "Failed to create Tokio runtime: {e}"
                ))
            })?;

            rt.block_on(async move { run_server(addr, state).await })
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
        })
    }
}

async fn run_server(
    addr: SocketAddr,
    state: Arc<ServerState>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let listener = TcpListener::bind(addr).await?;
    let has_ws = !state.ws_routes.is_empty();

    let state_for_signal = state.clone();

    tokio::select! {
        res = async {
            loop {
                let (stream, _) = listener.accept().await?;
                let io = hyper_util::rt::TokioIo::new(stream);
                let state_clone = state.clone();

                if has_ws {
                    // WebSocket-capable connection handler (with upgrade support)
                    tokio::task::spawn(async move {
                        if let Err(_err) = http1::Builder::new()
                            .serve_connection(
                                io,
                                service_fn(move |req| {
                                    let state = state_clone.clone();
                                    async move { handle_request(req, state).await }
                                }),
                            )
                            .with_upgrades()
                            .await
                        {
                        }
                    });
                } else {
                    // Fast path: no WebSocket routes, skip upgrade overhead
                    tokio::task::spawn(async move {
                        if let Err(_err) = http1::Builder::new()
                            .serve_connection(
                                io,
                                service_fn(move |req| {
                                    let state = state_clone.clone();
                                    async move { handle_request(req, state).await }
                                }),
                            )
                            .await
                        {
                        }
                    });
                }
            }
            #[allow(unreachable_code)]
            Ok::<_, Box<dyn std::error::Error + Send + Sync>>(())
        } => res,

        _ = tokio::signal::ctrl_c() => {
            println!("\\nShutting down Ignyx server...");
            if !state_for_signal.shutdown_handlers.is_empty() {
                let bg_state = state_for_signal.clone();
                let _ = tokio::task::spawn_blocking(move || {
                    Python::with_gil(|py| {
                        let asyncio = py.import("asyncio").ok();
                        for handler in &bg_state.shutdown_handlers {
                            let is_coro = py.import("inspect")
                                .and_then(|m| m.call_method1("iscoroutinefunction", (handler,)))
                                .and_then(|v| v.extract::<bool>())
                                .unwrap_or(false);
                            if is_coro {
                                if let Some(asyncio_mod) = &asyncio {
                                    if let Ok(coro) = handler.call0(py) {
                                        let _ = asyncio_mod.call_method1("run", (coro,));
                                    }
                                }
                            } else {
                                let _ = handler.call0(py);
                            }
                        }
                    });
                }).await;
            }
            Ok(())
        }
    }
}

async fn handle_request(
    req: HyperRequest<Incoming>,
    state: Arc<ServerState>,
) -> Result<HyperResponse<Full<Bytes>>, Infallible> {
    // Check for WebSocket upgrade BEFORE consuming the body
    let is_ws_upgrade = req
        .headers()
        .get("upgrade")
        .map(|v| v.to_str().unwrap_or("").eq_ignore_ascii_case("websocket"))
        .unwrap_or(false);

    if is_ws_upgrade {
        return crate::websocket::handle_websocket(req, state).await;
    }

    let method = req.method().clone();

    // Deconstruct req right here to avoid lifetime issues or moving `req` into closure
    let (parts, body) = req.into_parts();

    if parts.method.as_str() == "OPTIONS" {
        return Python::with_gil(|py| -> Result<HyperResponse<Full<Bytes>>, Infallible> {
            let mut req_headers = HashMap::new();
            for (k, v) in parts.headers.iter() {
                req_headers.insert(k.to_string(), v.to_str().unwrap_or("").to_string());
            }
            let query_params_map = crate::request::parse_query(parts.uri.query().unwrap_or(""));
            let request_obj = crate::request::Request::new(
                method.to_string(),
                parts.uri.path().to_string(),
                req_headers,
                query_params_map,
                HashMap::new(),
                Vec::new(),
            );

            let py_req: PyObject = if let Ok(py_request_raw) = Py::new(py, request_obj) {
                let mut py_request_wrapped = py_request_raw.into_any();
                if let Ok(ignyx_req_mod) = py.import("ignyx.request") {
                    if let Ok(req_class) = ignyx_req_mod.getattr("Request") {
                        if let Ok(wrapper) = req_class.call1((&py_request_wrapped,)) {
                            py_request_wrapped = wrapper.into();
                        }
                    }
                }
                py_request_wrapped
            } else {
                py.None()
            };

            let empty_body = pyo3::types::PyString::new(py, "");
            let status = 200u16.into_pyobject(py).unwrap();
            let headers_dict = pyo3::types::PyDict::new(py);
            let mut result_obj: PyObject = pyo3::types::PyTuple::new(
                py,
                &[
                    empty_body.into_pyobject(py).unwrap().into_any().unbind(),
                    status.into_any().unbind(),
                    headers_dict.into_pyobject(py).unwrap().into_any().unbind(),
                ],
            )
            .unwrap()
            .into();

            for mw in state.middlewares.iter().rev() {
                if let Ok(method) = mw.getattr::<&str>(py, "after_request") {
                    if let Ok(modified_res) = method.call1::<_>(py, (&py_req, &result_obj)) {
                        result_obj = modified_res;
                    }
                }
            }

            let mut custom_headers = None;
            let bound_result = result_obj.into_bound(py);
            if bound_result.is_instance_of::<pyo3::types::PyTuple>() {
                if let Ok(tuple) = bound_result.downcast::<pyo3::types::PyTuple>() {
                    if tuple.len() >= 3 {
                        if let Ok(item) = tuple.get_item(2) {
                            if let Ok(hdict) = item.downcast::<pyo3::types::PyDict>() {
                                let mut hmap = HashMap::new();
                                for (k, v) in hdict {
                                    if let Ok(ks) = k.extract::<String>() {
                                        if let Ok(vs) = v.extract::<String>() {
                                            hmap.insert(ks, vs);
                                        }
                                    }
                                }
                                custom_headers = Some(hmap);
                            }
                        }
                    }
                }
            }

            let mut builder = HyperResponse::builder()
                .status(200)
                .header("content-type", "text/plain")
                .header("server", "Ignyx/1.1.1");

            if let Some(h) = custom_headers {
                for (k, v) in h {
                    builder = builder.header(k, v);
                }
            }
            Ok(builder.body(Full::new(Bytes::from(""))).unwrap())
        });
    }

    if let Some(router_method) = crate::router::Method::from_str(parts.method.as_str()) {
        if let Some(route_match) = state.router.find(router_method, parts.uri.path()) {
            let handler_index = route_match.handler_index;
            let path_params = route_match.params;
            let handler = &state.handlers[handler_index];

            // Zero-allocation body check
            let needs_body = handler.param_names.iter().any(|n| n == "body");
            let needs_request =
                !state.middlewares.is_empty() || handler.param_names.iter().any(|n| n == "request");
            let is_multipart = parts
                .headers
                .get("content-type")
                .and_then(|v| v.to_str().ok())
                .map(|v| v.contains("multipart/form-data"))
                .unwrap_or(false);

            let body_bytes = if needs_body || needs_request || is_multipart {
                use http_body_util::BodyExt;
                match body.collect().await {
                    Ok(collected) => collected.to_bytes().to_vec(),
                    Err(_) => Vec::new(),
                }
            } else {
                Vec::new() // Zero-cost if endpoint doesn't accept body
            };

            let mut form_fields: HashMap<String, String> = HashMap::new();
            let mut form_files: HashMap<String, (String, String, Vec<u8>)> = HashMap::new();

            if is_multipart {
                if let Some(content_type) = parts
                    .headers
                    .get("content-type")
                    .and_then(|v| v.to_str().ok())
                {
                    crate::multipart::parse_multipart(
                        content_type,
                        &body_bytes,
                        &mut form_fields,
                        &mut form_files,
                    )
                    .await;
                }
            }

            // HONEST PATH: ship GIL execution to a background blocking thread
            // to prevent holding up the Tokio runtime reactor with Python execution lock
            let state_clone = state.clone();

            // Spawn blocking to decouple the Tokio reactor from Python GIL
            let result = tokio::task::spawn_blocking(move || {
                Python::with_gil(|py| -> crate::handler::HandlerResult {
                    // Ensure an asyncio event loop is set for this thread
                    ASYNCIO_LOOP.with(|cell| {
                        let mut loop_ref = cell.borrow_mut();
                        if loop_ref.is_none() {
                            let new_loop_fn = state_clone.py_refs.new_event_loop.clone_ref(py);
                            if !new_loop_fn.is_none(py) {
                                if let Ok(loop_obj) = new_loop_fn.bind(py).call0() {
                                    if let Ok(run_method) =
                                        loop_obj.getattr::<&str>("run_until_complete")
                                    {
                                        *loop_ref = Some((loop_obj.unbind(), run_method.unbind()));
                                    }
                                }
                            }
                        }
                    });

                    let handler = &state_clone.handlers[handler_index];
                    match crate::handler::call_python_handler(
                        py,
                        handler,
                        parts.method.as_str(),
                        parts.uri.path(),
                        &path_params,
                        parts.uri.query().unwrap_or(""),
                        &parts.headers,
                        &body_bytes,
                        &form_fields,
                        &form_files,
                        &state_clone,
                    ) {
                        Ok(res) => Ok(res),
                        Err(e) => {
                            e.print_and_set_sys_last_vars(py);
                            Err(e)
                        }
                    }
                })
            })
            .await
            .unwrap();

            match result {
                Ok((body, content_type, status, custom_headers, bg_task)) => {
                    let mut builder = HyperResponse::builder()
                        .status(status)
                        .header("content-type", &content_type)
                        .header("server", "Ignyx/2.1.4");

                    if let Some(h) = custom_headers {
                        for (k, v) in h {
                            builder = builder.header(k, v);
                        }
                    }

                    let response = builder.body(Full::new(Bytes::from(body))).unwrap();

                    // If there's a background task, spawn it to run AFTER response
                    if let Some(task) = bg_task {
                        tokio::spawn(async move {
                            // TODO: Replace this sleep with proper tokio::sync::oneshot flush signaling
                            // once we implement a custom http_body wrapper.
                            // Delay by 500ms to ensure the HTTP response flushes to the client first.
                            tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                            tokio::task::spawn_blocking(move || {
                                Python::with_gil(|py| {
                                    // BackgroundTask executes synchronous functions locally right now
                                    // (We fallback to pyo3_asyncio for real async later)
                                    let _ = task.call_method0(py, "execute");
                                });
                            });
                        });
                    }

                    return Ok(response);
                }
                Err(e) => {
                    let error_body = serde_json::json!({
                        "error": "Internal Server Error",
                        "detail": e.to_string()
                    })
                    .to_string();
                    let response = HyperResponse::builder()
                        .status(500)
                        .header("content-type", "application/json")
                        .header("server", "Ignyx/1.1.2")
                        .body(Full::new(Bytes::from(error_body)))
                        .unwrap();
                    return Ok(response);
                }
            }
        }
    }

    // 404 Not Found Handling
    let state_clone = state.clone();
    let has_nf_handler = state_clone.not_found_handler.is_some();
    if has_nf_handler {
        let result = tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| -> crate::handler::HandlerResult {
                let handler_obj = state_clone
                    .not_found_handler
                    .as_ref()
                    .unwrap()
                    .clone_ref(py);
                let param_names = vec!["request".to_string(), "path".to_string()];
                let param_types = HashMap::new();

                let dummy_sig = crate::handler::HandlerSignature {
                    handler: handler_obj,
                    param_types,
                    is_async: false,
                    param_names,
                    has_depends: false,
                    pydantic_body_model: None,
                    resolve_deps_fn: None,
                };

                crate::handler::call_python_handler(
                    py,
                    &dummy_sig,
                    parts.method.as_str(),
                    parts.uri.path(),
                    &HashMap::new(),
                    parts.uri.query().unwrap_or(""),
                    &parts.headers,
                    &Vec::new(), // Send empty body bytes to 404 handler
                    &HashMap::new(),
                    &HashMap::new(),
                    &state_clone,
                )
            })
        })
        .await
        .unwrap();

        if let Ok((body, content_type, status, custom_headers, bg_task)) = result {
            let mut builder = HyperResponse::builder()
                .status(status)
                .header("content-type", &content_type)
                .header("server", "Ignyx/1.1.2");

            if let Some(h) = custom_headers {
                for (k, v) in h {
                    builder = builder.header(k, v);
                }
            }

            if let Some(task) = bg_task {
                tokio::spawn(async move {
                    tokio::time::sleep(std::time::Duration::from_millis(150)).await;
                    tokio::task::spawn_blocking(move || {
                        Python::with_gil(|py| {
                            let _ = task.call_method0(py, "execute");
                        });
                    });
                });
            }

            return Ok(builder.body(Full::new(Bytes::from(body))).unwrap());
        }
    }

    // Default 404 Fallback
    let body = serde_json::json!({
        "error": "Not Found",
        "detail": "No route found"
    })
    .to_string();

    let response = HyperResponse::builder()
        .status(404)
        .header("content-type", "application/json")
        .header("server", "Ignyx/1.1.1")
        .body(Full::new(Bytes::from(body)))
        .unwrap();

    Ok(response)
}
