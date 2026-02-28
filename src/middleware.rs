use pyo3::prelude::*;

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
