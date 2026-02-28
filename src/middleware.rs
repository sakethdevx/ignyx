use pyo3::prelude::*;

pub fn execute_before_middlewares(
    py: Python<'_>,
    middlewares: &[PyObject],
    mut py_request_wrapped: PyObject,
) -> PyObject {
    for mw in middlewares {
        if let Ok(method) = mw.getattr(py, "before_request") {
            if let Ok(modified_req) = method.call1(py, (&py_request_wrapped,)) {
                py_request_wrapped = modified_req;
            }
        }
    }
    py_request_wrapped
}

pub fn execute_after_middlewares(
    py: Python<'_>,
    middlewares: &[PyObject],
    req_obj: &PyObject,
    mut result: PyObject,
) -> PyObject {
    for mw in middlewares.iter().rev() {
        if let Ok(method) = mw.getattr(py, "after_request") {
            if let Ok(modified_res) = method.call1(py, (req_obj, &result)) {
                result = modified_res;
            }
        }
    }
    result
}
