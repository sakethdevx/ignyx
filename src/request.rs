use pyo3::prelude::*;
use std::collections::HashMap;

/// Python-facing Request object.
/// Contains HTTP method, path, headers, query params, and body.
#[pyclass]
#[derive(Clone)]
pub struct Request {
    #[pyo3(get)]
    pub method: String,
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub headers: String,
    #[pyo3(get)]
    pub query_params: String,
    #[pyo3(get)]
    pub path_params: String,
    #[pyo3(get)]
    pub body: Vec<u8>,
}

/// Parse a raw query string into a HashMap<String, String>
pub fn parse_query(query_string: &str) -> HashMap<String, String> {
    let mut map = HashMap::new();
    for pair in query_string.split('&') {
        if pair.is_empty() {
            continue;
        }
        let mut parts = pair.splitn(2, '=');
        if let Some(key) = parts.next() {
            let value = parts.next().unwrap_or("");
            // Basic urldecode replacement (handles '+' and '%20' manually)
            let decoded_value = value.replace('+', " ");
            map.insert(key.to_string(), decoded_value);
        }
    }
    map
}

#[pymethods]
impl Request {
    #[new]
    pub fn new(
        method: String,
        path: String,
        headers_map: HashMap<String, String>,
        query_map: HashMap<String, String>,
        path_map: HashMap<String, String>,
        body: Vec<u8>,
    ) -> Self {
        Self {
            method,
            path,
            headers: serde_json::to_string(&headers_map).unwrap_or_else(|_| "{}".to_string()),
            query_params: serde_json::to_string(&query_map).unwrap_or_else(|_| "{}".to_string()),
            path_params: serde_json::to_string(&path_map).unwrap_or_else(|_| "{}".to_string()),
            body,
        }
    }

    /// Get body as UTF-8 string
    pub fn text(&self) -> PyResult<String> {
        String::from_utf8(self.body.clone())
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }

    /// Parse body as JSON (returns Python dict)
    pub fn json(&self, py: Python<'_>) -> PyResult<PyObject> {
        let text = self.text()?;
        let value: serde_json::Value = serde_json::from_str(&text)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        json_value_to_py(py, &value)
    }
}

/// Convert a serde_json::Value to a Python object
pub fn json_value_to_py(py: Python<'_>, value: &serde_json::Value) -> PyResult<PyObject> {
    use pyo3::IntoPyObject;
    match value {
        serde_json::Value::Null => Ok(py.None()),
        serde_json::Value::Bool(b) => {
            Ok(b.into_pyobject(py).unwrap().to_owned().into_any().unbind())
        }
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.into_pyobject(py).unwrap().into_any().unbind())
            } else if let Some(f) = n.as_f64() {
                Ok(f.into_pyobject(py).unwrap().into_any().unbind())
            } else {
                Ok(py.None())
            }
        }
        serde_json::Value::String(s) => Ok(s.into_pyobject(py).unwrap().into_any().unbind()),
        serde_json::Value::Array(arr) => {
            let list = pyo3::types::PyList::empty(py);
            for item in arr {
                list.append(json_value_to_py(py, item)?)?;
            }
            Ok(list.into_any().unbind())
        }
        serde_json::Value::Object(map) => {
            let dict = pyo3::types::PyDict::new(py);
            for (k, v) in map {
                dict.set_item(k, json_value_to_py(py, v)?)?;
            }
            Ok(dict.into_any().unbind())
        }
    }
}
