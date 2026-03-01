use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};
use std::collections::HashMap;

/// Python-facing Request object.
/// Raw HTTP data (headers, query params, path params) is stored natively in Rust
/// memory. Python strings are only allocated when the user explicitly accesses
/// a specific header or parameter, eliminating unnecessary FFI overhead.
#[pyclass]
#[derive(Clone)]
pub struct Request {
    #[pyo3(get)]
    pub method: String,
    #[pyo3(get)]
    pub path: String,
    /// Raw headers kept in Rust memory — no Python allocation until accessed
    headers_map: HashMap<String, String>,
    /// Raw query params kept in Rust memory
    query_params_map: HashMap<String, String>,
    /// Raw path params kept in Rust memory
    path_params_map: HashMap<String, String>,
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
            headers_map,
            query_params_map: query_map,
            path_params_map: path_map,
            body,
        }
    }

    // --- Lazy individual accessors (no full dict conversion) ---

    /// Get a single header by name without materializing the full Python dict.
    pub fn get_header(&self, key: &str) -> Option<String> {
        self.headers_map.get(&key.to_lowercase()).cloned()
    }

    /// Get a single query parameter by key.
    pub fn get_query_param(&self, key: &str) -> Option<String> {
        self.query_params_map.get(key).cloned()
    }

    /// Get a single path parameter by key.
    pub fn get_path_param(&self, key: &str) -> Option<String> {
        self.path_params_map.get(key).cloned()
    }

    // --- Bulk accessors (converted to Python dict only when needed) ---

    /// Materialize all headers as a Python dict.
    pub fn get_all_headers(&self) -> HashMap<String, String> {
        self.headers_map.clone()
    }

    /// Materialize all query params as a Python dict.
    pub fn get_all_query_params(&self) -> HashMap<String, String> {
        self.query_params_map.clone()
    }

    /// Materialize all path params as a Python dict.
    pub fn get_all_path_params(&self) -> HashMap<String, String> {
        self.path_params_map.clone()
    }

    // --- Backward-compatible JSON string getters ---

    /// Headers as JSON string (backward compatibility for external code).
    #[getter]
    pub fn headers(&self) -> String {
        serde_json::to_string(&self.headers_map).unwrap_or_else(|_| "{}".to_string())
    }

    /// Query params as JSON string (backward compatibility).
    #[getter]
    pub fn query_params(&self) -> String {
        serde_json::to_string(&self.query_params_map).unwrap_or_else(|_| "{}".to_string())
    }

    /// Path params as JSON string (backward compatibility).
    #[getter]
    pub fn path_params(&self) -> String {
        serde_json::to_string(&self.path_params_map).unwrap_or_else(|_| "{}".to_string())
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

/// Convert a Python object to a serde_json::Value for native serialization.
/// Handles dicts, lists, strings, ints, floats, bools, None, and Pydantic models.
/// This bypasses Python's `json` module entirely — serialization stays in Rust.
pub fn py_to_json_value(
    py: Python<'_>,
    obj: &Bound<'_, pyo3::types::PyAny>,
) -> PyResult<serde_json::Value> {
    if obj.is_none() {
        Ok(serde_json::Value::Null)
    } else if obj.is_instance_of::<PyBool>() {
        // Must check bool BEFORE int (bool is a subclass of int in Python)
        Ok(serde_json::Value::Bool(obj.extract::<bool>()?))
    } else if obj.is_instance_of::<PyInt>() {
        Ok(serde_json::Value::Number(obj.extract::<i64>()?.into()))
    } else if obj.is_instance_of::<PyFloat>() {
        if let Some(n) = serde_json::Number::from_f64(obj.extract::<f64>()?) {
            Ok(serde_json::Value::Number(n))
        } else {
            Ok(serde_json::Value::Null)
        }
    } else if obj.is_instance_of::<PyString>() {
        Ok(serde_json::Value::String(obj.extract::<String>()?))
    } else if obj.is_instance_of::<PyList>() {
        let list = obj.downcast::<PyList>()?;
        let mut arr = Vec::with_capacity(list.len());
        for item in list {
            arr.push(py_to_json_value(py, &item)?);
        }
        Ok(serde_json::Value::Array(arr))
    } else if obj.is_instance_of::<PyDict>() {
        let dict = obj.downcast::<PyDict>()?;
        let mut map = serde_json::Map::new();
        for (k, v) in dict {
            let key = k.extract::<String>()?;
            map.insert(key, py_to_json_value(py, &v)?);
        }
        Ok(serde_json::Value::Object(map))
    } else if obj.hasattr("model_dump")? {
        // Pydantic BaseModel — call model_dump() to get a dict, then serialize natively
        let dict = obj.call_method0("model_dump")?;
        py_to_json_value(py, &dict)
    } else {
        // Fallback: convert to string representation
        Ok(serde_json::Value::String(obj.str()?.extract::<String>()?))
    }
}

/// Serialize a Python object directly to a JSON byte string, bypassing Python's json module.
pub fn py_to_json_string(py: Python<'_>, obj: &Bound<'_, pyo3::types::PyAny>) -> PyResult<String> {
    let value = py_to_json_value(py, obj)?;
    serde_json::to_string(&value)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}
