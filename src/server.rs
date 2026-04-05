use crate::router::{Method, Router};
use bytes::Bytes;
use futures_util::TryStreamExt;
use http_body_util::{BodyStream, Full};
use hyper::body::Incoming;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request as HyperRequest, Response as HyperResponse};
use pyo3::prelude::*;
use std::collections::HashMap;
use std::convert::Infallible;
use std::net::SocketAddr;
use std::pin::Pin;
use std::sync::Arc;
use std::task::{Context, Poll};
use std::time::Instant;
use tokio::net::TcpListener;
use tokio::runtime::Runtime;
use tracing::{info, instrument};

// ── Streaming-capable response body ─────────────────────────────────────

/// A response body that is either a buffered `Full<Bytes>` or a streaming
/// channel-backed body.  Implements `http_body::Body` so hyper can send it.
pub(crate) enum AppBody {
    Full(Full<Bytes>),
    Stream {
        rx: tokio::sync::mpsc::Receiver<Bytes>,
    },
}

impl AppBody {
    pub fn full(data: impl Into<Bytes>) -> Self {
        AppBody::Full(Full::new(data.into()))
    }
}

impl http_body::Body for AppBody {
    type Data = Bytes;
    type Error = Infallible;

    fn poll_frame(
        self: Pin<&mut Self>,
        cx: &mut Context<'_>,
    ) -> Poll<Option<Result<http_body::Frame<Self::Data>, Self::Error>>> {
        match self.get_mut() {
            AppBody::Full(inner) => Pin::new(inner).poll_frame(cx),
            AppBody::Stream { rx } => match rx.poll_recv(cx) {
                Poll::Ready(Some(chunk)) => Poll::Ready(Some(Ok(http_body::Frame::data(chunk)))),
                Poll::Ready(None) => Poll::Ready(None),
                Poll::Pending => Poll::Pending,
            },
        }
    }

    fn is_end_stream(&self) -> bool {
        match self {
            AppBody::Full(inner) => inner.is_end_stream(),
            AppBody::Stream { .. } => false,
        }
    }

    fn size_hint(&self) -> http_body::SizeHint {
        match self {
            AppBody::Full(inner) => inner.size_hint(),
            AppBody::Stream { .. } => http_body::SizeHint::default(),
        }
    }
}

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
    pub rust_middlewares: Arc<crate::middleware::RustMiddlewares>,
    pub pubsub: Option<crate::pubsub::PubSub>,
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
    #[pyo3(signature = (host, port, middlewares, ws_routes, not_found_handler, shutdown_handlers, pubsub=None, rate_limit_requests=None, rate_limit_window=None))]
    pub fn run(
        &self,
        py: Python<'_>,
        host: &str,
        port: u16,
        middlewares: Vec<PyObject>,
        ws_routes: Vec<(String, PyObject)>,
        not_found_handler: Option<PyObject>,
        shutdown_handlers: Vec<PyObject>,
        pubsub: Option<PyRef<'_, crate::pubsub::PubSub>>,
        rate_limit_requests: Option<u32>,
        rate_limit_window: Option<u64>,
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
                    pydantic_json_schema: None,
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

            // Cache: does this handler declare any Depends() (default or Annotated)?
            let has_depends = if let Ok(sig) = inspect.call_method1("signature", (&handler,)) {
                if let Ok(params_proxy) = sig.getattr("parameters") {
                    if let Ok(values_iter) = params_proxy.call_method0("values") {
                        if let Ok(_iter) = values_iter.try_iter() {
                            let depends_mod = py.import("ignyx.depends").ok();
                            let depends_class = depends_mod.and_then(|m| m.getattr("Depends").ok());
                            let (get_origin, get_args, annotated) = py
                                .import("typing")
                                .ok()
                                .map(|m| {
                                    (
                                        m.getattr("get_origin").ok(),
                                        m.getattr("get_args").ok(),
                                        m.getattr("Annotated").ok(),
                                    )
                                })
                                .unwrap_or((None, None, None));
                            let mut found = false;
                            for param in values_iter.try_iter().unwrap().flatten() {
                                let Some(ref dep_cls) = depends_class else {
                                    break;
                                };

                                // FastAPI-style: user = Depends(get_user)
                                if let Ok(default) = param.getattr("default") {
                                    if default.is_instance(dep_cls).unwrap_or(false) {
                                        found = true;
                                        break;
                                    }
                                }

                                // Modern: user: Annotated[User, Depends(get_user)]
                                if let (Some(go), Some(ga), Some(ann_form)) =
                                    (&get_origin, &get_args, &annotated)
                                {
                                    if let Ok(annotation) = param.getattr("annotation") {
                                        if let Ok(origin) = go.call1((annotation.clone(),)) {
                                            if origin.is(ann_form) {
                                                if let Ok(args_obj) = ga.call1((annotation,)) {
                                                    if let Ok(args) =
                                                        args_obj.downcast::<pyo3::types::PyTuple>()
                                                    {
                                                        for meta in args.iter().skip(1) {
                                                            if meta
                                                                .is_instance(dep_cls)
                                                                .unwrap_or(false)
                                                            {
                                                                found = true;
                                                                break;
                                                            }
                                                        }
                                                        if found {
                                                            break;
                                                        }
                                                    }
                                                }
                                            }
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

            // Cache: extract Pydantic JSON schema for pre-GIL structural validation
            let pydantic_json_schema = if let Some(ref model) = pydantic_body_model {
                model
                    .call_method0(py, "model_json_schema")
                    .ok()
                    .and_then(|schema_dict| {
                        crate::request::py_to_json_value(py, schema_dict.bind(py)).ok()
                    })
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
                pydantic_json_schema,
            };
        }

        let req_proxy_class = py
            .import("ignyx.request")
            .ok()
            .and_then(|m| m.getattr("Request").ok())
            .map(|c| c.into());

        let asyncio_mod = py.import("asyncio").ok().map(|m| m.into());
        let new_event_loop = asyncio_mod
            .as_ref()
            .and_then(|m: &PyObject| m.getattr(py, "new_event_loop").ok());
        let set_event_loop = asyncio_mod
            .as_ref()
            .and_then(|m: &PyObject| m.getattr(py, "set_event_loop").ok());

        // ── Extract Rust-native middleware configs from Python objects ──
        let mut cors_config: Option<crate::middleware::RustCORSConfig> = None;
        let mut rate_limit_config: Option<crate::middleware::RustRateLimitConfig> = None;
        let mut gzip_config: Option<crate::middleware::RustGZipConfig> = None;
        let mut session_config: Option<crate::middleware::RustSessionConfig> = None;
        let mut python_middlewares: Vec<PyObject> = Vec::new();

        for mw in middlewares {
            let (cors, rl, gz, sess, keep) = crate::middleware::extract_rust_middleware(py, &mw);
            if cors.is_some() {
                cors_config = cors;
            }
            if rl.is_some() {
                rate_limit_config = rl;
            }
            if gz.is_some() {
                gzip_config = gz;
            }
            if sess.is_some() {
                session_config = sess;
            }
            if keep {
                python_middlewares.push(mw);
            }
        }

        // Rate limit config from explicit Ignyx app params takes precedence
        if let Some(max_req) = rate_limit_requests {
            rate_limit_config = Some(crate::middleware::RustRateLimitConfig {
                max_requests: max_req,
                window_secs: rate_limit_window.unwrap_or(60),
            });
        }

        let rust_middlewares = Arc::new(crate::middleware::RustMiddlewares::new(
            cors_config,
            rate_limit_config,
            gzip_config,
            session_config,
        ));

        let state = Arc::new(ServerState {
            router,
            handlers,
            middlewares: python_middlewares,
            ws_routes,
            not_found_handler,
            shutdown_handlers,
            py_refs: crate::pyref::PythonCachedRefs {
                request_class: req_proxy_class.unwrap_or_else(|| py.None()),
                new_event_loop: new_event_loop.unwrap_or_else(|| py.None()),
                set_event_loop: set_event_loop.unwrap_or_else(|| py.None()),
            },
            asyncio_mod,
            rust_middlewares,
            pubsub: pubsub.map(|p| crate::pubsub::PubSub {
                channels: p.channels.clone(),
            }),
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

#[instrument(
    skip(state, req),
    fields(method = %req.method(), path = %req.uri().path())
)]
async fn handle_request(
    req: HyperRequest<Incoming>,
    state: Arc<ServerState>,
) -> Result<HyperResponse<AppBody>, Infallible> {
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

    // ── Rust rate-limit check (no GIL needed) ──────────────────────────
    let client_ip = parts
        .headers
        .get("x-forwarded-for")
        .or_else(|| parts.headers.get("x-real-ip"))
        .and_then(|v| v.to_str().ok())
        .unwrap_or("unknown")
        .to_string();
    let rate_limit_key = parts
        .headers
        .get("authorization")
        .and_then(|v| v.to_str().ok())
        .map(|v| format!("token:{v}"))
        .unwrap_or_else(|| format!("ip:{client_ip}"));

    if let Err((rl_status, rl_body, rl_headers)) =
        state.rust_middlewares.check_rate_limit(&rate_limit_key)
    {
        let mut builder = HyperResponse::builder()
            .status(rl_status)
            .header("server", "Ignyx/3.0.0");
        for (k, v) in &rl_headers {
            builder = builder.header(k.as_str(), v.as_str());
        }
        let mut response = builder.body(AppBody::full(rl_body)).unwrap();
        state
            .rust_middlewares
            .apply_cors_headers(response.headers_mut());
        return Ok(response);
    }

    // Extract accept-encoding for post-handler GZip (before parts is moved)
    let accept_encoding = parts
        .headers
        .get("accept-encoding")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();

    if parts.method.as_str() == "OPTIONS" {
        return Python::with_gil(|py| -> Result<HyperResponse<AppBody>, Infallible> {
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
                .header("server", "Ignyx/3.0.0");

            if let Some(h) = custom_headers {
                for (k, v) in h {
                    builder = builder.header(k, v);
                }
            }
            let mut response = builder.body(AppBody::full("")).unwrap();
            state
                .rust_middlewares
                .apply_cors_headers(response.headers_mut());
            Ok(response)
        });
    }

    if let Some(router_method) = crate::router::Method::from_str(parts.method.as_str()) {
        let routing_start = Instant::now();
        if let Some(route_match) = state.router.find(router_method, parts.uri.path()) {
            let routing_elapsed = routing_start.elapsed();
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

            let mut form_fields: HashMap<String, String> = HashMap::new();
            let mut form_files: HashMap<String, (String, String, std::path::PathBuf)> =
                HashMap::new();

            let body_bytes = if is_multipart {
                let need_body_bytes = needs_body || needs_request;
                let collector = if need_body_bytes {
                    Some(std::sync::Arc::new(std::sync::Mutex::new(Vec::new())))
                } else {
                    None
                };

                if let Some(content_type) = parts
                    .headers
                    .get("content-type")
                    .and_then(|v| v.to_str().ok())
                {
                    let collector_clone = collector.clone();
                    let stream = BodyStream::new(body)
                        .map_ok(|frame| frame.into_data().unwrap_or_default())
                        .map_err(std::io::Error::other)
                        .map_ok(move |chunk| {
                            if let Some(ref buf) = collector_clone {
                                if let Ok(mut guard) = buf.lock() {
                                    guard.extend_from_slice(&chunk);
                                }
                            }
                            chunk
                        });

                    if let Err(err) = crate::multipart::parse_multipart(
                        content_type,
                        stream,
                        &mut form_fields,
                        &mut form_files,
                    )
                    .await
                    {
                        let mut response = HyperResponse::builder()
                            .status(400)
                            .header("content-type", "text/plain")
                            .header("server", "Ignyx/3.0.0")
                            .body(AppBody::full(format!("Malformed multipart data: {err}")))
                            .unwrap();
                        state
                            .rust_middlewares
                            .apply_cors_headers(response.headers_mut());
                        return Ok(response);
                    }

                    if let Some(buf) = collector {
                        buf.lock().map(|v| v.clone()).unwrap_or_default()
                    } else {
                        Vec::new()
                    }
                } else {
                    Vec::new()
                }
            } else if needs_body || needs_request {
                use http_body_util::BodyExt;
                match body.collect().await {
                    Ok(collected) => collected.to_bytes().to_vec(),
                    Err(_) => Vec::new(),
                }
            } else {
                Vec::new() // Zero-cost if endpoint doesn't accept body
            };

            // HONEST PATH: ship GIL execution to a background blocking thread
            // to prevent holding up the Tokio runtime reactor with Python execution lock
            let state_clone = state.clone();

            // Pre-GIL: fast schema validation (checks required fields without Python GIL)
            let is_json_body = parts
                .headers
                .get("content-type")
                .and_then(|v| v.to_str().ok())
                .map(|v| v.contains("application/json"))
                .unwrap_or(false);

            if is_json_body && !body_bytes.is_empty() {
                if let Some(ref schema) = handler.pydantic_json_schema {
                    let mut json_buf = body_bytes.clone();
                    if let Ok(ref json_val) =
                        simd_json::from_slice::<serde_json::Value>(&mut json_buf)
                    {
                        if let Err(errors) = crate::handler::validate_json_schema(json_val, schema)
                        {
                            let error_body = simd_json::to_string(&serde_json::json!({
                                "error": "Validation failed",
                                "detail": errors
                            }))
                            .unwrap_or_else(|_| "{\"error\":\"Validation failed\"}".to_string());
                            let mut response = HyperResponse::builder()
                                .status(422)
                                .header("content-type", "application/json")
                                .header("server", "Ignyx/3.0.0")
                                .body(AppBody::full(error_body))
                                .unwrap();
                            state
                                .rust_middlewares
                                .apply_cors_headers(response.headers_mut());
                            return Ok(response);
                        }
                    }
                }
            }

            // Spawn blocking to decouple the Tokio reactor from Python GIL
            let py_exec_start = Instant::now();
            let result = tokio::task::spawn_blocking(move || {
                Python::with_gil(|py| -> crate::handler::HandlerResult {
                    let handler = &state_clone.handlers[handler_index];

                    // Only initialize asyncio event loop for async handlers
                    // (avoids overhead for synchronous def handlers)
                    if handler.is_async {
                        ASYNCIO_LOOP.with(|cell| {
                            let mut loop_ref = cell.borrow_mut();
                            if loop_ref.is_none() {
                                let new_loop_fn = state_clone.py_refs.new_event_loop.clone_ref(py);
                                if !new_loop_fn.is_none(py) {
                                    if let Ok(loop_obj) = new_loop_fn.bind(py).call0() {
                                        if let Ok(run_method) =
                                            loop_obj.getattr::<&str>("run_until_complete")
                                        {
                                            *loop_ref =
                                                Some((loop_obj.unbind(), run_method.unbind()));
                                        }
                                    }
                                }
                            }
                        });
                    }

                    // Sync handlers: securely wrapped in spawn_blocking — cannot block Tokio reactor
                    // Async handlers: coroutine is awaited via cached per-thread asyncio event loop
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
            let py_exec_elapsed = py_exec_start.elapsed();
            info!(
                routing_ms = routing_elapsed.as_millis(),
                python_ms = py_exec_elapsed.as_millis(),
                "request timings"
            );

            match result {
                Ok(crate::handler::HandlerOutput::Full(
                    body,
                    content_type,
                    status,
                    custom_headers,
                    bg_task,
                )) => {
                    let body_bytes = Bytes::from(body);

                    // Rust GZip compression (no GIL)
                    let (final_body, is_gzipped) = if let Some(compressed) = state
                        .rust_middlewares
                        .maybe_gzip(&body_bytes, &accept_encoding)
                    {
                        (Bytes::from(compressed), true)
                    } else {
                        (body_bytes, false)
                    };

                    let mut builder = HyperResponse::builder()
                        .status(status)
                        .header("content-type", &content_type)
                        .header("server", "Ignyx/3.0.0");

                    if is_gzipped {
                        builder = builder.header("content-encoding", "gzip");
                    }

                    if let Some(h) = custom_headers {
                        for (k, v) in h {
                            builder = builder.header(k, v);
                        }
                    }

                    let mut response = builder.body(AppBody::full(final_body)).unwrap();

                    // Rust CORS headers (no GIL)
                    state
                        .rust_middlewares
                        .apply_cors_headers(response.headers_mut());

                    // If there's a background task, spawn it to run AFTER response
                    if let Some(task) = bg_task {
                        tokio::spawn(async move {
                            tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                            tokio::task::spawn_blocking(move || {
                                Python::with_gil(|py| {
                                    let _ = task.call_method0(py, "execute");
                                });
                            });
                        });
                    }

                    return Ok(response);
                }
                Ok(crate::handler::HandlerOutput::Streaming(
                    content_type,
                    status,
                    custom_headers,
                    iterator,
                    is_async,
                )) => {
                    // ── Streaming / SSE response path ────────────────────────
                    let (tx, rx) = tokio::sync::mpsc::channel::<Bytes>(32);

                    let state_for_stream = state.clone();
                    tokio::task::spawn_blocking(move || {
                        Python::with_gil(|py| {
                            // Ensure asyncio event loop for async iterators
                            if is_async {
                                ASYNCIO_LOOP.with(|cell| {
                                    let mut loop_ref = cell.borrow_mut();
                                    if loop_ref.is_none() {
                                        let new_loop_fn =
                                            state_for_stream.py_refs.new_event_loop.clone_ref(py);
                                        if !new_loop_fn.is_none(py) {
                                            if let Ok(loop_obj) = new_loop_fn.bind(py).call0() {
                                                if let Ok(run_method) =
                                                    loop_obj.getattr::<&str>("run_until_complete")
                                                {
                                                    *loop_ref = Some((
                                                        loop_obj.unbind(),
                                                        run_method.unbind(),
                                                    ));
                                                }
                                            }
                                        }
                                    }
                                });
                            }

                            let iter_bound = iterator.bind(py);

                            if is_async {
                                // Iterate an async generator
                                if let Ok(aiter) = iter_bound.call_method0("__aiter__") {
                                    loop {
                                        match aiter.call_method0("__anext__") {
                                            Ok(coro) => {
                                                let run_result = ASYNCIO_LOOP.with(|cell| {
                                                    if let Some(ref c) = *cell.borrow() {
                                                        c.1.bind(py).call1((&coro,)).ok()
                                                    } else {
                                                        None
                                                    }
                                                });
                                                if let Some(chunk_obj) = run_result {
                                                    if let Ok(chunk_str) =
                                                        chunk_obj.extract::<String>()
                                                    {
                                                        let chunk_bytes = Bytes::from(chunk_str);
                                                        // Release GIL while waiting for channel
                                                        let send_ok = py.allow_threads(|| {
                                                            tx.blocking_send(chunk_bytes).is_ok()
                                                        });
                                                        if !send_ok {
                                                            break;
                                                        }
                                                    }
                                                } else {
                                                    break;
                                                }
                                            }
                                            Err(e) => {
                                                if e.is_instance_of::<
                                                    pyo3::exceptions::PyStopAsyncIteration,
                                                >(py) {
                                                    break;
                                                }
                                                break;
                                            }
                                        }
                                    }
                                }
                            } else {
                                // Iterate a sync generator / iterator
                                if let Ok(sync_iter) = iter_bound.call_method0("__iter__") {
                                    loop {
                                        match sync_iter.call_method0("__next__") {
                                            Ok(chunk_obj) => {
                                                if let Ok(chunk_str) = chunk_obj.extract::<String>()
                                                {
                                                    let chunk_bytes = Bytes::from(chunk_str);
                                                    let send_ok = py.allow_threads(|| {
                                                        tx.blocking_send(chunk_bytes).is_ok()
                                                    });
                                                    if !send_ok {
                                                        break;
                                                    }
                                                }
                                            }
                                            Err(e) => {
                                                if e.is_instance_of::<
                                                    pyo3::exceptions::PyStopIteration,
                                                >(py) {
                                                    break;
                                                }
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        });
                    });

                    let mut builder = HyperResponse::builder()
                        .status(status)
                        .header("content-type", &content_type)
                        .header("server", "Ignyx/3.0.0")
                        .header("transfer-encoding", "chunked")
                        .header("cache-control", "no-cache");

                    if let Some(h) = custom_headers {
                        for (k, v) in h {
                            builder = builder.header(k, v);
                        }
                    }

                    let mut response = builder.body(AppBody::Stream { rx }).unwrap();
                    state
                        .rust_middlewares
                        .apply_cors_headers(response.headers_mut());
                    return Ok(response);
                }
                Err(e) => {
                    let error_body = serde_json::json!({
                        "error": "Internal Server Error",
                        "detail": e.to_string()
                    })
                    .to_string();
                    let mut response = HyperResponse::builder()
                        .status(500)
                        .header("content-type", "application/json")
                        .header("server", "Ignyx/3.0.0")
                        .body(AppBody::full(error_body))
                        .unwrap();
                    state
                        .rust_middlewares
                        .apply_cors_headers(response.headers_mut());
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
                    pydantic_json_schema: None,
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

        if let Ok(crate::handler::HandlerOutput::Full(
            body,
            content_type,
            status,
            custom_headers,
            bg_task,
        )) = result
        {
            let mut builder = HyperResponse::builder()
                .status(status)
                .header("content-type", &content_type)
                .header("server", "Ignyx/3.0.0");

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

            let mut response = builder.body(AppBody::full(body)).unwrap();
            state
                .rust_middlewares
                .apply_cors_headers(response.headers_mut());
            return Ok(response);
        }
    }

    // Default 404 Fallback
    let body = serde_json::json!({
        "error": "Not Found",
        "detail": "No route found"
    })
    .to_string();

    let mut response = HyperResponse::builder()
        .status(404)
        .header("content-type", "application/json")
        .header("server", "Ignyx/3.0.0")
        .body(AppBody::full(body))
        .unwrap();
    state
        .rust_middlewares
        .apply_cors_headers(response.headers_mut());

    Ok(response)
}
