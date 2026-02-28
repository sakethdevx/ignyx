mod handler;
mod middleware;
mod multipart;
mod pyref;
mod request;
mod response;
mod router;
mod server;
mod websocket;

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
