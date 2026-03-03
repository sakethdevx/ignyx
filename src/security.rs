/// Rust-native JWT encode/decode for Ignyx.
///
/// Exposed to Python as `ignyx._core.JwtDecoder`.
/// The higher-level `JWTBearer` dependency lives in `python/ignyx/security.py`
/// and delegates to this struct for the actual crypto work.
use jsonwebtoken::{decode, encode, Algorithm, DecodingKey, EncodingKey, Header, Validation};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde_json::Value;
use std::collections::HashMap;

// ── serde_json ↔ Python conversion helpers ──────────────────────────────────

/// Convert a `serde_json::Value` into a Python object.
fn json_to_py(py: Python<'_>, val: &Value) -> PyResult<PyObject> {
    match val {
        Value::Null => Ok(py.None()),
        Value::Bool(b) => {
            use pyo3::types::PyBool;
            let borrowed = (*b).into_pyobject(py)?;
            Ok(<pyo3::Bound<'_, PyBool> as Clone>::clone(&borrowed)
                .into_any()
                .unbind())
        }
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.into_pyobject(py)?.into_any().unbind())
            } else if let Some(f) = n.as_f64() {
                Ok(f.into_pyobject(py)?.into_any().unbind())
            } else {
                Ok(n.to_string().into_pyobject(py)?.into_any().unbind())
            }
        }
        Value::String(s) => Ok(s.clone().into_pyobject(py)?.into_any().unbind()),
        Value::Array(arr) => {
            let items: PyResult<Vec<PyObject>> = arr.iter().map(|v| json_to_py(py, v)).collect();
            Ok(PyList::new(py, items?)?.into_any().unbind())
        }
        Value::Object(obj) => {
            let dict = PyDict::new(py);
            for (k, v) in obj {
                dict.set_item(k, json_to_py(py, v)?)?;
            }
            Ok(dict.into_any().unbind())
        }
    }
}

/// Convert a Python object into a `serde_json::Value` for JWT encoding.
fn py_to_json(obj: &Bound<'_, PyAny>) -> PyResult<Value> {
    if obj.is_none() {
        return Ok(Value::Null);
    }
    // Check bool BEFORE int — Python bool is a subclass of int.
    if obj.is_instance_of::<pyo3::types::PyBool>() {
        let b: bool = obj.extract()?;
        return Ok(Value::Bool(b));
    }
    if let Ok(i) = obj.extract::<i64>() {
        return Ok(Value::Number(i.into()));
    }
    if let Ok(f) = obj.extract::<f64>() {
        if let Some(n) = serde_json::Number::from_f64(f) {
            return Ok(Value::Number(n));
        }
    }
    if let Ok(s) = obj.extract::<String>() {
        return Ok(Value::String(s));
    }
    if let Ok(list) = obj.downcast::<PyList>() {
        let arr: PyResult<Vec<Value>> = list.iter().map(|v| py_to_json(&v)).collect();
        return Ok(Value::Array(arr?));
    }
    if let Ok(dict) = obj.downcast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (k, v) in dict {
            let key: String = k.extract()?;
            map.insert(key, py_to_json(&v)?);
        }
        return Ok(Value::Object(map));
    }
    Ok(Value::String(obj.str()?.to_string()))
}

fn str_to_algorithm(algorithm: &str) -> PyResult<Algorithm> {
    match algorithm {
        "HS256" => Ok(Algorithm::HS256),
        "HS384" => Ok(Algorithm::HS384),
        "HS512" => Ok(Algorithm::HS512),
        "RS256" => Ok(Algorithm::RS256),
        "RS384" => Ok(Algorithm::RS384),
        "RS512" => Ok(Algorithm::RS512),
        "ES256" => Ok(Algorithm::ES256),
        "ES384" => Ok(Algorithm::ES384),
        _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Unsupported algorithm '{algorithm}'. \
             Supported: HS256, HS384, HS512, RS256, RS384, RS512, ES256, ES384"
        ))),
    }
}

// ── PyClass ─────────────────────────────────────────────────────────────────

/// Rust-native JWT codec.
///
/// For HMAC algorithms (HS256 / HS384 / HS512) pass the raw secret string.
/// For asymmetric algorithms (RS* / ES*) pass the PEM-encoded public key for
/// ``decode`` and the PEM-encoded private key for ``encode``.
///
/// Example::
///
///     from ignyx._core import JwtDecoder
///     codec = JwtDecoder(secret="my-secret", algorithm="HS256")
///     token = codec.encode({"sub": "user1", "exp": 9999999999})
///     payload = codec.decode(token)   # -> {"sub": "user1", "exp": 9999999999}
#[pyclass]
pub struct JwtDecoder {
    secret: String,
    algorithm: Algorithm,
    validate_exp: bool,
}

#[pymethods]
impl JwtDecoder {
    /// Create a new JwtDecoder.
    ///
    /// :param secret: HMAC secret or PEM key string.
    /// :param algorithm: JWT algorithm (default ``"HS256"``).
    /// :param validate_exp: Whether to enforce the ``exp`` claim (default ``True``).
    #[new]
    #[pyo3(signature = (secret, algorithm = "HS256", validate_exp = true))]
    pub fn new(secret: String, algorithm: &str, validate_exp: bool) -> PyResult<Self> {
        Ok(Self {
            algorithm: str_to_algorithm(algorithm)?,
            secret,
            validate_exp,
        })
    }

    /// Decode and validate a JWT token.
    ///
    /// Returns the payload as a Python ``dict``.
    /// Raises ``ValueError`` if the token is invalid, expired, or tampered with.
    pub fn decode(&self, py: Python<'_>, token: &str) -> PyResult<PyObject> {
        let key = DecodingKey::from_secret(self.secret.as_bytes());
        // Disable built-in exp validation and manage it manually below.
        // jsonwebtoken 9.3 changed the exp validation defaults; doing it
        // ourselves keeps behavior consistent across crate versions.
        let mut validation = Validation::new(self.algorithm);
        validation.validate_exp = false;
        validation.required_spec_claims.clear();

        let data = decode::<HashMap<String, Value>>(token, &key, &validation)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

        // Manual expiry check.
        if self.validate_exp {
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0);
            match data.claims.get("exp").and_then(|v| v.as_f64()) {
                Some(exp) if now >= exp => {
                    return Err(pyo3::exceptions::PyValueError::new_err("Token has expired"));
                }
                None => {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        "Token missing required 'exp' claim",
                    ));
                }
                _ => {}
            }
        }

        let dict = PyDict::new(py);
        for (k, v) in data.claims {
            dict.set_item(&k, json_to_py(py, &v)?)?;
        }
        Ok(dict.into_any().unbind())
    }

    /// Encode a Python dict payload into a JWT string.
    ///
    /// Raises ``ValueError`` if the payload cannot be serialized or signing fails.
    pub fn encode(&self, _py: Python<'_>, payload: &Bound<'_, PyDict>) -> PyResult<String> {
        let claims = py_to_json(payload.as_any())?;
        let key = EncodingKey::from_secret(self.secret.as_bytes());
        let header = Header::new(self.algorithm);
        encode(&header, &claims, &key)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
}
