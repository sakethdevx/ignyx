use pyo3::prelude::*;
use std::collections::HashMap;
use std::time::{Duration, Instant};

use dashmap::DashMap;

// ── Python middleware bridge (unchanged) ────────────────────────────────

pub fn execute_before_middlewares(
    py: Python<'_>,
    middlewares: &[PyObject],
    mut py_request_wrapped: PyObject,
) -> PyResult<PyObject> {
    for mw in middlewares {
        if let Ok(method) = mw.getattr(py, "before_request") {
            let modified_req = method.call1(py, (&py_request_wrapped,))?;
            if !modified_req.is_none(py) {
                py_request_wrapped = modified_req;
            }
        }
    }
    Ok(py_request_wrapped)
}

pub fn execute_after_middlewares(
    py: Python<'_>,
    middlewares: &[PyObject],
    req_obj: &PyObject,
    mut result: PyObject,
) -> PyResult<PyObject> {
    for mw in middlewares.iter().rev() {
        if let Ok(method) = mw.getattr(py, "after_request") {
            let modified_res = method.call1(py, (req_obj, &result))?;
            if !modified_res.is_none(py) {
                result = modified_res;
            }
        }
    }
    Ok(result)
}

// ── Rust-native middleware configs ──────────────────────────────────────

/// CORS configuration extracted from Python CORSMiddleware at startup.
pub struct RustCORSConfig {
    pub allow_origins: Vec<String>,
    pub allow_methods: Vec<String>,
    pub allow_headers: Vec<String>,
    pub allow_credentials: bool,
    pub max_age: u32,
}

/// Rate-limit configuration extracted from Python RateLimitMiddleware at startup.
pub struct RustRateLimitConfig {
    pub max_requests: u32,
    pub window_secs: u64,
}

/// GZip configuration extracted from Python GZipMiddleware at startup.
pub struct RustGZipConfig {
    pub minimum_size: usize,
}

/// Collection of all Rust-native middlewares that execute without the Python GIL.
pub struct RustMiddlewares {
    pub cors: Option<RustCORSConfig>,
    pub rate_limit: Option<RustRateLimitConfig>,
    pub gzip: Option<RustGZipConfig>,
    /// Concurrent map: key → Vec<Instant> of request timestamps
    pub rate_limit_store: DashMap<String, Vec<Instant>>,
}

impl RustMiddlewares {
    pub fn new(
        cors: Option<RustCORSConfig>,
        rate_limit: Option<RustRateLimitConfig>,
        gzip: Option<RustGZipConfig>,
    ) -> Self {
        Self {
            cors,
            rate_limit,
            gzip,
            rate_limit_store: DashMap::new(),
        }
    }

    /// Check rate limit for the given key (IP or token).
    /// Returns `Ok(())` if allowed, or `Err((status, body, headers))` if exceeded.
    pub fn check_rate_limit(
        &self,
        key: &str,
    ) -> Result<(), (u16, String, HashMap<String, String>)> {
        if let Some(ref config) = self.rate_limit {
            let now = Instant::now();
            let window = Duration::from_secs(config.window_secs);

            let mut entry = self.rate_limit_store.entry(key.to_string()).or_default();
            // Evict expired timestamps
            entry.retain(|t| now.duration_since(*t) < window);

            if entry.len() >= config.max_requests as usize {
                let mut headers = HashMap::new();
                headers.insert("retry-after".to_string(), config.window_secs.to_string());
                headers.insert("content-type".to_string(), "application/json".to_string());
                return Err((
                    429,
                    r#"{"detail":"Rate limit exceeded"}"#.to_string(),
                    headers,
                ));
            }

            entry.push(now);
        }
        Ok(())
    }

    /// Apply CORS headers to a hyper HeaderMap (mutates in-place).
    pub fn apply_cors_headers(&self, response_headers: &mut hyper::header::HeaderMap) {
        if let Some(ref config) = self.cors {
            let insert = |map: &mut hyper::header::HeaderMap, name: &str, value: &str| {
                if let Ok(v) = hyper::header::HeaderValue::from_str(value) {
                    map.insert(
                        hyper::header::HeaderName::from_bytes(name.as_bytes()).unwrap(),
                        v,
                    );
                }
            };
            insert(
                response_headers,
                "access-control-allow-origin",
                &config.allow_origins.join(", "),
            );
            insert(
                response_headers,
                "access-control-allow-methods",
                &config.allow_methods.join(", "),
            );
            insert(
                response_headers,
                "access-control-allow-headers",
                &config.allow_headers.join(", "),
            );
            if config.allow_credentials {
                insert(response_headers, "access-control-allow-credentials", "true");
            }
            insert(
                response_headers,
                "access-control-max-age",
                &config.max_age.to_string(),
            );
        }
    }

    /// Attempt GZip compression. Returns `Some(compressed_bytes)` if applicable, else `None`.
    pub fn maybe_gzip(&self, body: &[u8], accept_encoding: &str) -> Option<Vec<u8>> {
        if let Some(ref config) = self.gzip {
            if body.len() >= config.minimum_size && accept_encoding.contains("gzip") {
                use flate2::write::GzEncoder;
                use flate2::Compression;
                use std::io::Write;

                let mut encoder = GzEncoder::new(Vec::new(), Compression::fast());
                if encoder.write_all(body).is_ok() {
                    if let Ok(compressed) = encoder.finish() {
                        if compressed.len() < body.len() {
                            return Some(compressed);
                        }
                    }
                }
            }
        }
        None
    }
}

/// Extract a Rust middleware config from a Python middleware object.
/// Returns (cors, rate_limit, gzip, should_keep_in_python_list).
pub fn extract_rust_middleware(
    py: Python<'_>,
    mw: &PyObject,
) -> (
    Option<RustCORSConfig>,
    Option<RustRateLimitConfig>,
    Option<RustGZipConfig>,
    bool,
) {
    let class_name = mw
        .getattr(py, "__class__")
        .and_then(|c| c.getattr(py, "__name__"))
        .and_then(|n| n.extract::<String>(py))
        .unwrap_or_default();

    match class_name.as_str() {
        "CORSMiddleware" => {
            let cors = RustCORSConfig {
                allow_origins: mw
                    .getattr(py, "allow_origins")
                    .and_then(|v| v.extract::<Vec<String>>(py))
                    .unwrap_or_else(|_| vec!["*".to_string()]),
                allow_methods: mw
                    .getattr(py, "allow_methods")
                    .and_then(|v| v.extract::<Vec<String>>(py))
                    .unwrap_or_else(|_| vec!["GET".to_string(), "POST".to_string()]),
                allow_headers: mw
                    .getattr(py, "allow_headers")
                    .and_then(|v| v.extract::<Vec<String>>(py))
                    .unwrap_or_else(|_| vec!["*".to_string()]),
                allow_credentials: mw
                    .getattr(py, "allow_credentials")
                    .and_then(|v| v.extract::<bool>(py))
                    .unwrap_or(false),
                max_age: mw
                    .getattr(py, "max_age")
                    .and_then(|v| v.extract::<u32>(py))
                    .unwrap_or(86400),
            };
            (Some(cors), None, None, false)
        }
        "GZipMiddleware" => {
            let gz = RustGZipConfig {
                minimum_size: mw
                    .getattr(py, "minimum_size")
                    .and_then(|v| v.extract::<usize>(py))
                    .unwrap_or(500),
            };
            (None, None, Some(gz), false)
        }
        _ => (None, None, None, true),
    }
}
