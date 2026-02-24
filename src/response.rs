use pyo3::prelude::*;
use std::collections::HashMap;

/// Python-facing Response object.
#[pyclass]
#[derive(Clone)]
pub struct Response {
    #[pyo3(get, set)]
    pub status_code: u16,
    #[pyo3(get, set)]
    pub headers: HashMap<String, String>,
    #[pyo3(get, set)]
    pub body: String,
}

#[pymethods]
impl Response {
    #[new]
    #[pyo3(signature = (body = String::new(), status_code = 200, headers = None))]
    pub fn new(body: String, status_code: u16, headers: Option<HashMap<String, String>>) -> Self {
        let mut h = headers.unwrap_or_default();
        h.entry("content-type".to_string())
            .or_insert_with(|| "application/json".to_string());
        Self {
            status_code,
            headers: h,
            body,
        }
    }

    /// Create a JSON response from a Python dict
    #[staticmethod]
    #[pyo3(signature = (data, status_code=None))]
    pub fn json(py: Python<'_>, data: &Bound<'_, pyo3::types::PyAny>, status_code: Option<u16>) -> PyResult<Self> {
        // Use Python's json.dumps for reliable serialization
        let json_mod = py.import("json")?;
        let json_str: String = json_mod
            .call_method1("dumps", (data,))?
            .extract()?;
        let mut headers = HashMap::new();
        headers.insert("content-type".to_string(), "application/json".to_string());
        Ok(Self {
            status_code: status_code.unwrap_or(200),
            headers,
            body: json_str,
        })
    }

    /// Create a plain text response
    #[staticmethod]
    #[pyo3(signature = (text, status_code = None))]
    pub fn text(text: String, status_code: Option<u16>) -> Self {
        let mut headers = HashMap::new();
        headers.insert("content-type".to_string(), "text/plain".to_string());
        Self {
            status_code: status_code.unwrap_or(200),
            headers,
            body: text,
        }
    }
}
