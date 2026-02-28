mod server;
mod handler;
mod websocket;
mod middleware;
mod multipart;
mod pyref;
mod router;
mod request;
mod response;

use pyo3::prelude::*;

/// The native Rust core module for Ignyx.
/// This is exposed to Python as `ignyx._core`.
#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<server::Server>()?;
    m.add_class::<request::Request>()?;
    m.add_class::<response::Response>()?;
    Ok(())
}
