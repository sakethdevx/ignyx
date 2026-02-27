use crate::router::{Method, Router};
use bytes::Bytes;
use http_body_util::Full;
use hyper::body::Incoming;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request as HyperRequest, Response as HyperResponse};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString, PyTuple};
use std::collections::HashMap;
use std::convert::Infallible;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio::runtime::Runtime;
use futures_util::{SinkExt, StreamExt};
use tokio_tungstenite::tungstenite::Message as WsMessage;

/// Route handler entry: stores the Python callable and metadata.
struct RouteEntry {
    method: Method,
    path: String,
    handler: PyObject,
}

/// Pre-computed signature for a Python handler
struct HandlerSignature {
    handler: PyObject,
    param_types: HashMap<String, PyObject>,
    is_async: bool,
    param_names: Vec<String>,
    has_depends: bool,
    pydantic_body_model: Option<PyObject>,
}

/// Shared state for the async server.
struct ServerState {
    router: Router,
    handlers: Vec<HandlerSignature>,
    middlewares: Vec<PyObject>,
    pub ws_routes: Vec<(String, PyObject)>,
    pub req_proxy_class: Option<PyObject>,
    pub json_dumps: Option<PyObject>,
    pub asyncio_mod: Option<PyObject>,
    pub new_event_loop: Option<PyObject>,
    pub set_event_loop: Option<PyObject>,
}

thread_local! {
    static ASYNCIO_LOOP: std::cell::RefCell<Option<(PyObject, PyObject)>> = std::cell::RefCell::new(None);
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
        Self {
            routes: Vec::new(),
        }
    }

    /// Register a route handler. Called from Python side.
    pub fn add_route(
        &mut self,
        method: &str,
        path: &str,
        handler: PyObject,
    ) -> PyResult<()> {
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
    pub fn run(&self, py: Python<'_>, host: &str, port: u16, middlewares: Vec<PyObject>, ws_routes: Vec<(String, PyObject)>) -> PyResult<()> {
        let addr: SocketAddr = format!("{host}:{port}")
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
        ).unwrap();

        let get_param_types = py.eval(&code, None, None)?;

        // Build the router and collect handler PyObjects
        let mut router = Router::new();
        let mut handlers: Vec<HandlerSignature> = Vec::new();

        let inspect = py.import("inspect")?;

        for entry in &self.routes {
            let index = router.insert(entry.method, &entry.path).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(e)
            })?;
            while handlers.len() <= index {
                handlers.push(HandlerSignature {
                    handler: py.None(), param_types: HashMap::new(),
                    is_async: false, param_names: Vec::new(),
                    has_depends: false, pydantic_body_model: None,
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
            let is_async = inspect.call_method1("iscoroutinefunction", (&handler,))
                .and_then(|v| v.extract::<bool>())
                .unwrap_or(false);

            // Cache: parameter names
            let mut param_names = Vec::new();
            if let Ok(sig) = inspect.call_method1("signature", (&handler,)) {
                if let Ok(params_proxy) = sig.getattr("parameters") {
                    if let Ok(keys_iter) = params_proxy.call_method0("keys") {
                        if let Ok(iter) = keys_iter.try_iter() {
                            for item in iter {
                                if let Ok(k) = item {
                                    if let Ok(name) = k.extract::<String>() {
                                        param_names.push(name);
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Cache: does this handler have Depends() defaults?
            let has_depends = if let Ok(sig) = inspect.call_method1("signature", (&handler,)) {
                if let Ok(params_proxy) = sig.getattr("parameters") {
                    if let Ok(values_iter) = params_proxy.call_method0("values") {
                        if let Ok(iter) = values_iter.try_iter() {
                            let depends_mod = py.import("ignyx.depends").ok();
                            let depends_class = depends_mod.and_then(|m| m.getattr("Depends").ok());
                            let mut found = false;
                            for item in iter {
                                if let Ok(param) = item {
                                    if let Ok(default) = param.getattr("default") {
                                        if let Some(ref dep_cls) = depends_class {
                                            if default.is_instance(dep_cls).unwrap_or(false) {
                                                found = true;
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                            found
                        } else { false }
                    } else { false }
                } else { false }
            } else { false };

            // Cache: is the body param a Pydantic BaseModel?
            let pydantic_body_model = if let Some(annotation) = param_types.get("body") {
                let is_basemodel = (|| -> PyResult<bool> {
                    let pydantic = py.import("pydantic")?;
                    let base_model = pydantic.getattr("BaseModel")?;
                    let is_sub = py.import("builtins")?
                        .getattr("issubclass")?
                        .call1((annotation.bind(py), base_model))?
                        .extract::<bool>()?;
                    Ok(is_sub)
                })().unwrap_or(false);
                if is_basemodel {
                    Some(annotation.clone_ref(py))
                } else {
                    None
                }
            } else {
                None
            };

            handlers[index] = HandlerSignature {
                handler, param_types, is_async, param_names,
                has_depends, pydantic_body_model,
            };
        }

        let req_proxy_class = py.import("ignyx.request").ok()
            .and_then(|m| m.getattr("Request").ok())
            .map(|c| c.into());
            
        let json_dumps = py.import("json").ok()
            .and_then(|m| m.getattr("dumps").ok())
            .map(|f| f.into());

        let asyncio_mod = py.import("asyncio").ok().map(|m| m.into());
        let new_event_loop = asyncio_mod.as_ref().and_then(|m: &PyObject| m.getattr(py, "new_event_loop").ok());
        let set_event_loop = asyncio_mod.as_ref().and_then(|m: &PyObject| m.getattr(py, "set_event_loop").ok());

        let state = Arc::new(ServerState {
            router,
            handlers,
            middlewares,
            ws_routes,
            req_proxy_class,
            json_dumps,
            asyncio_mod,
            new_event_loop,
            set_event_loop,
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

            rt.block_on(async move {
                run_server(addr, state).await
            })
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

    loop {
        let (stream, _) = listener.accept().await?;
        let io = hyper_util::rt::TokioIo::new(stream);
        let state = state.clone();

        if has_ws {
            // WebSocket-capable connection handler (with upgrade support)
            tokio::task::spawn(async move {
                if let Err(_err) = http1::Builder::new()
                    .serve_connection(
                        io,
                        service_fn(move |req| {
                            let state = state.clone();
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
                            let state = state.clone();
                            async move { handle_request(req, state).await }
                        }),
                    )
                    .await
                {
                }
            });
        }
    }
}

async fn handle_request(
    req: HyperRequest<Incoming>,
    state: Arc<ServerState>,
) -> Result<HyperResponse<Full<Bytes>>, Infallible> {
    // Check for WebSocket upgrade BEFORE consuming the body
    let is_ws_upgrade = req.headers()
        .get("upgrade")
        .map(|v| v.to_str().unwrap_or("").eq_ignore_ascii_case("websocket"))
        .unwrap_or(false);

    if is_ws_upgrade {
        // Find matching WebSocket route — clone handler with GIL
        let ws_handler_clone: Option<PyObject> = Python::with_gil(|py| {
            for (ws_path, ws_h) in &state.ws_routes {
                if ws_path == req.uri().path() {
                    return Some(ws_h.clone_ref(py));
                }
            }
            None
        });
        
        if let Some(handler) = ws_handler_clone {

            // Extract the WebSocket accept key BEFORE moving req
            let ws_key = req.headers()
                .get("sec-websocket-key")
                .map(|v| v.to_str().unwrap_or("").to_string())
                .unwrap_or_default();
            
            // Use tungstenite's built-in accept key derivation (RFC 6455 compliant)
            let accept_value = tokio_tungstenite::tungstenite::handshake::derive_accept_key(ws_key.as_bytes());

            // Spawn the WebSocket upgrade task (runs AFTER we return the 101 response)
            tokio::task::spawn(async move {
                match hyper::upgrade::on(req).await {
                    Ok(upgraded) => {
                        let io = hyper_util::rt::TokioIo::new(upgraded);
                        let ws_stream = tokio_tungstenite::WebSocketStream::from_raw_socket(
                            io,
                            tokio_tungstenite::tungstenite::protocol::Role::Server,
                            None,
                        ).await;

                        let (mut ws_write, mut ws_read) = ws_stream.split();

                        // Create mpsc channels for Python <-> Rust WebSocket bridging
                        let (send_tx, mut send_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
                        let (recv_tx, recv_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
                        let recv_rx = Arc::new(std::sync::Mutex::new(recv_rx));
                        let (close_tx, mut close_rx) = tokio::sync::mpsc::unbounded_channel::<u16>();

                        // Spawn a task to forward outgoing messages from Python to the WebSocket
                        let write_task = tokio::spawn(async move {
                            loop {
                                tokio::select! {
                                    msg = send_rx.recv() => {
                                        match msg {
                                            Some(text) => {
                                                if ws_write.send(WsMessage::Text(text.into())).await.is_err() {
                                                    break;
                                                }
                                            }
                                            None => break,
                                        }
                                    }
                                    code = close_rx.recv() => {
                                        let close_frame = tokio_tungstenite::tungstenite::protocol::CloseFrame {
                                            code: tokio_tungstenite::tungstenite::protocol::frame::coding::CloseCode::from(code.unwrap_or(1000)),
                                            reason: "".into(),
                                        };
                                        let _ = ws_write.send(WsMessage::Close(Some(close_frame))).await;
                                        break;
                                    }
                                }
                            }
                        });

                        // Spawn a task to forward incoming messages from WebSocket to Python
                        let recv_tx_clone = recv_tx.clone();
                        let read_task = tokio::spawn(async move {
                            while let Some(Ok(msg)) = ws_read.next().await {
                                match msg {
                                    WsMessage::Text(text) => {
                                        let _ = recv_tx_clone.send(text.to_string());
                                    }
                                    WsMessage::Close(_) => break,
                                    _ => {}
                                }
                            }
                        });

                        // Run the Python handler in a blocking thread
                        let send_tx_for_py = send_tx.clone();
                        let recv_rx_for_py = recv_rx.clone();
                        let close_tx_for_py = close_tx.clone();
                        let state_clone = state.clone();

                        tokio::task::spawn_blocking(move || {
                            Python::with_gil(|py| {
                                // Ensure an asyncio event loop is set for this thread
                                ASYNCIO_LOOP.with(|cell| {
                                    let mut loop_ref = cell.borrow_mut();
                                    if loop_ref.is_none() {
                                        if let Some(new_loop_fn) = &state_clone.new_event_loop {
                                            if let Ok(new_loop) = new_loop_fn.call0(py) {
                                                if let Some(set_loop_fn) = &state_clone.set_event_loop {
                                                    let _ = set_loop_fn.call1(py, (new_loop.clone_ref(py),));
                                                }
                                                if let Ok(run_method) = new_loop.getattr(py, "run_until_complete") {
                                                    *loop_ref = Some((new_loop, run_method));
                                                }
                                            }
                                        }
                                    }
                                });

                                // Create Python callback functions using Bound types (PyO3 0.23)
                                let send_tx_inner = send_tx_for_py.clone();
                                let send_fn = pyo3::types::PyCFunction::new_closure(
                                    py,
                                    Some(c"send"),
                                    None,
                                    move |args: &pyo3::Bound<'_, pyo3::types::PyTuple>, _kwargs: Option<&pyo3::Bound<'_, pyo3::types::PyDict>>| -> PyResult<()> {
                                        let text: String = args.get_item(0)?.extract()?;
                                        let _ = send_tx_inner.send(text);
                                        Ok(())
                                    },
                                ).unwrap();

                                let recv_rx_inner = recv_rx_for_py.clone();
                                let recv_fn = pyo3::types::PyCFunction::new_closure(
                                    py,
                                    Some(c"recv"),
                                    None,
                                    move |_args: &pyo3::Bound<'_, pyo3::types::PyTuple>, _kwargs: Option<&pyo3::Bound<'_, pyo3::types::PyDict>>| -> PyResult<String> {
                                        let mut rx = recv_rx_inner.lock().unwrap();
                                        match rx.blocking_recv() {
                                            Some(text) => Ok(text),
                                            None => Err(pyo3::exceptions::PyConnectionError::new_err("WebSocket closed")),
                                        }
                                    },
                                ).unwrap();

                                let close_tx_inner = close_tx_for_py.clone();
                                let close_fn = pyo3::types::PyCFunction::new_closure(
                                    py,
                                    Some(c"close"),
                                    None,
                                    move |args: &pyo3::Bound<'_, pyo3::types::PyTuple>, _kwargs: Option<&pyo3::Bound<'_, pyo3::types::PyDict>>| -> PyResult<()> {
                                        let code: u16 = args.get_item(0).and_then(|v| v.extract()).unwrap_or(1000);
                                        let _ = close_tx_inner.send(code);
                                        Ok(())
                                    },
                                ).unwrap();

                                let accept_fn = pyo3::types::PyCFunction::new_closure(
                                    py,
                                    Some(c"accept"),
                                    None,
                                    move |_args: &pyo3::Bound<'_, pyo3::types::PyTuple>, _kwargs: Option<&pyo3::Bound<'_, pyo3::types::PyDict>>| -> PyResult<()> {
                                        Ok(())
                                    },
                                ).unwrap();

                                // Create the Python WebSocket wrapper
                                if let Ok(ws_mod) = py.import("ignyx.websocket") {
                                    if let Ok(ws_class) = ws_mod.getattr("WebSocket") {
                                        if let Ok(ws_instance) = ws_class.call1((send_fn, recv_fn, close_fn, accept_fn)) {
                                            if let Ok(coro) = handler.call1(py, (ws_instance,)) {
                                                let inspect = py.import("inspect").unwrap();
                                                let is_coro: bool = inspect.call_method1("iscoroutine", (&coro,))
                                                    .and_then(|v| v.extract())
                                                    .unwrap_or(false);
                                                if is_coro {
                                                    ASYNCIO_LOOP.with(|cell| {
                                                        if let Some(ref cached) = *cell.borrow() {
                                                            let _ = cached.1.call1(py, (&coro,));
                                                        } else if let Some(asyncio_mod) = &state_clone.asyncio_mod {
                                                            let _ = asyncio_mod.call_method1(py, "run", (&coro,));
                                                        }
                                                    });
                                                }
                                            }
                                        }
                                    }
                                }
                            });
                        }).await.ok();

                        // Cleanup
                        drop(send_tx);
                        drop(recv_tx);
                        drop(close_tx);
                        write_task.abort();
                        read_task.abort();
                    }
                    Err(_e) => {
                        // eprintln!("WebSocket upgrade error: {e}");
                    }
                }
            });

            // Return 101 Switching Protocols
            let response = HyperResponse::builder()
                .status(101)
                .header("upgrade", "websocket")
                .header("connection", "Upgrade")
                .header("sec-websocket-accept", accept_value)
                .body(Full::new(Bytes::new()))
                .unwrap();

            return Ok(response);
        }
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
                py_request_wrapped.into()
            } else {
                py.None()
            };

            let empty_body = pyo3::types::PyString::new_bound(py, "");
            let status = 200u16.into_py(py);
            let headers_dict = pyo3::types::PyDict::new_bound(py);
            let mut result_obj: PyObject = pyo3::types::PyTuple::new_bound(py, &[empty_body.into_py(py), status, headers_dict.into_py(py)]).into();

            for mw in state.middlewares.iter().rev() {
                if let Ok(method) = mw.getattr(py, "after_request") {
                    if let Ok(modified_res) = method.call1(py, (&py_req, &result_obj)) {
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
                .header("server", "Ignyx/1.0.3");
                
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
        let needs_request = !state.middlewares.is_empty() || handler.param_names.iter().any(|n| n == "request");
        let is_multipart = parts.headers.get("content-type")
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
            if let Some(content_type) = parts.headers.get("content-type").and_then(|v| v.to_str().ok()) {
                if let Some(boundary) = multer::parse_boundary(content_type).ok() {
                    let bytes_clone = body_bytes.clone();
                    let stream = futures_util::stream::once(async move {
                        Ok::<bytes::Bytes, std::convert::Infallible>(bytes::Bytes::from(bytes_clone))
                    });
                    let mut multipart = multer::Multipart::new(stream, boundary);
                    while let Some(mut field) = multipart.next_field().await.unwrap_or(None) {
                        let name = field.name().unwrap_or("").to_string();
                        if let Some(filename_ref) = field.file_name() {
                            let filename = filename_ref.to_string();
                            let c_type = field.content_type().map(|c| c.to_string()).unwrap_or_else(|| "application/octet-stream".to_string());
                            let data = field.bytes().await.unwrap_or_default().to_vec();
                            form_files.insert(name, (filename, c_type, data));
                        } else {
                            let text = field.text().await.unwrap_or_default();
                            form_fields.insert(name, text);
                        }
                    }
                }
            }
        }

        // HONEST PATH: ship GIL execution to a background blocking thread
        // to prevent holding up the Tokio runtime reactor with Python execution lock
        let state_clone = state.clone();
        
        // Spawn blocking to decouple the Tokio reactor from Python GIL
        let result = tokio::task::spawn_blocking(move || {
            Python::with_gil(|py| -> PyResult<(String, String, u16, Option<HashMap<String, String>>, Option<PyObject>)> {
                // Ensure an asyncio event loop is set for this thread
                ASYNCIO_LOOP.with(|cell| {
                    let mut loop_ref = cell.borrow_mut();
                    if loop_ref.is_none() {
                        if let Some(new_loop_fn) = &state_clone.new_event_loop {
                            if let Ok(loop_obj) = new_loop_fn.call0(py) {
                                if let Ok(run_method) = loop_obj.getattr(py, "run_until_complete") {
                                    *loop_ref = Some((loop_obj, run_method));
                                }
                            }
                        }
                    }
                });

                let handler = &state_clone.handlers[handler_index];
                match call_python_handler(
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
        }).await.unwrap();

        match result {
                Ok((body, content_type, status, custom_headers, bg_task)) => {
                    let mut builder = HyperResponse::builder()
                        .status(status)
                        .header("content-type", &content_type)
                        .header("server", "Ignyx/1.0.3");
                        
                    if let Some(h) = custom_headers {
                        for (k, v) in h {
                            builder = builder.header(k, v);
                        }
                    }

                    let response = builder.body(Full::new(Bytes::from(body))).unwrap();

                    // If there's a background task, spawn it to run AFTER response
                    if let Some(task) = bg_task {
                        tokio::spawn(async move {
                            // Delay by 150ms to ensure the HTTP response flushes to the client first
                            tokio::time::sleep(std::time::Duration::from_millis(150)).await;
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
                        .header("server", "Ignyx/1.0.3")
                        .body(Full::new(Bytes::from(error_body)))
                        .unwrap();
                    return Ok(response);
                }
            }
        }
    }

    // 404 Not Found
    let body = serde_json::json!({
        "error": "Not Found",
        "detail": "No route found"
    })
    .to_string();

    let response = HyperResponse::builder()
        .status(404)
        .header("content-type", "application/json")
        .header("server", "Ignyx/1.0.3")
        .body(Full::new(Bytes::from(body)))
        .unwrap();

    Ok(response)
}

/// Call a Python handler with the real request data.
/// Uses the cached handler signature to inject path params and coerce types.
/// Returns (body_str, content_type, status_code, optional_headers).
fn call_python_handler(
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
    state: &ServerState,
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
        
        if let Some(ref proxy_class_obj) = state.req_proxy_class {
            let proxy_class = proxy_class_obj.bind(py);
            if let Ok(wrapper) = proxy_class.call1((&py_request_wrapped,)) {
                py_request_wrapped = wrapper.into();
            }
        }

        // 1. Execute Before Middlewares
        for mw in &state.middlewares {
            if let Ok(method) = mw.getattr(py, "before_request") {
                if let Ok(modified_req) = method.call1(py, (&py_request_wrapped,)) {
                    py_request_wrapped = modified_req;
                }
            }
        }
        
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
        if let Ok(depends_mod) = py.import("ignyx.depends") {
            if let Ok(resolve_fn) = depends_mod.getattr("resolve_dependencies") {
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
                let awaited = ASYNCIO_LOOP.with(|loop_cell| {
                    let mut loop_opt = loop_cell.borrow_mut();
                    
                    // Create loop on this thread if it doesn't exist
                    if loop_opt.is_none() {
                        if let Some(ref new_loop_func) = state.new_event_loop {
                            if let Ok(new_loop) = new_loop_func.call0(py) {
                                if let Some(ref set_loop_func) = state.set_event_loop {
                                    let _ = set_loop_func.call1(py, (&new_loop,));
                                }
                                if let Ok(run_method) = new_loop.getattr(py, "run_until_complete") {
                                    *loop_opt = Some((new_loop, run_method));
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
                return Err(err);
            }
        }
    };

    // 2. Execute After Middlewares (in reverse order)
    for mw in state.middlewares.iter().rev() {
        if let Ok(method) = mw.getattr(py, "after_request") {
            if let Some(ref req_obj) = py_request_wrapped_opt {
                if let Ok(modified_res) = method.call1(py, (req_obj, &result)) {
                    result = modified_res;
                }
            }
        }
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
        let json_str: String = if let Some(ref dumps_obj) = state.json_dumps {
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
