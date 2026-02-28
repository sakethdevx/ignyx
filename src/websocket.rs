use pyo3::prelude::*;
use std::sync::Arc;
// use tokio::net::TcpStream; // Removed unused
use crate::server::ServerState;
use bytes::Bytes;
use futures_util::{SinkExt, StreamExt};
use http_body_util::Full;
use hyper::body::Incoming;
use hyper::{Request as HyperRequest, Response as HyperResponse};
use std::convert::Infallible;
use tokio_tungstenite::tungstenite::Message as WsMessage;

pub(crate) async fn handle_websocket(
    req: HyperRequest<Incoming>,
    state: Arc<ServerState>,
) -> Result<HyperResponse<Full<Bytes>>, Infallible> {
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
        let ws_key = req
            .headers()
            .get("sec-websocket-key")
            .map(|v| v.to_str().unwrap_or("").to_string())
            .unwrap_or_default();

        // Use tungstenite's built-in accept key derivation (RFC 6455 compliant)
        let accept_value =
            tokio_tungstenite::tungstenite::handshake::derive_accept_key(ws_key.as_bytes());

        // Spawn the WebSocket upgrade task (runs AFTER we return the 101 response)
        tokio::task::spawn(async move {
            match hyper::upgrade::on(req).await {
                Ok(upgraded) => {
                    let io = hyper_util::rt::TokioIo::new(upgraded);
                    let ws_stream = tokio_tungstenite::WebSocketStream::from_raw_socket(
                        io,
                        tokio_tungstenite::tungstenite::protocol::Role::Server,
                        None,
                    )
                    .await;

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
                                            if ws_write.send(WsMessage::Text(text)).await.is_err() {
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
                            crate::server::ASYNCIO_LOOP.with(|cell| {
                                let mut loop_ref = cell.borrow_mut();
                                if loop_ref.is_none() {
                                    let new_loop_fn = state_clone.py_refs.new_event_loop.clone_ref(py);
                                    if !new_loop_fn.is_none(py) {
                                        if let Ok(new_loop) = new_loop_fn.bind(py).call0() {
                                            let set_loop_fn = state_clone.py_refs.set_event_loop.clone_ref(py);
                                            if !set_loop_fn.is_none(py) {
                                                let _ = set_loop_fn.bind(py).call1((&new_loop,));
                                            }
                                            if let Ok(run_method) = new_loop.getattr::<&str>("run_until_complete") {
                                                *loop_ref = Some((new_loop.unbind(), run_method.unbind()));
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
                                                crate::server::ASYNCIO_LOOP.with(|cell: &std::cell::RefCell<Option<(PyObject, PyObject)>>| {
                                                    if let Some(ref cached) = *cell.borrow() {
                                                        let _ = cached.1.bind(py).call1((&coro,));
                                                    } else if let Some(asyncio_mod) = &state_clone.asyncio_mod {
                                                        let _ = asyncio_mod.bind(py).call_method1::<&str, _>("run", (&coro,));
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
                Err(_e) => {}
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

    // Fallback: This is not actually reached when called properly, but needed for types.
    let response = HyperResponse::builder()
        .status(404)
        .body(Full::new(Bytes::new()))
        .unwrap();

    Ok(response)
}
