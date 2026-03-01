use pyo3::prelude::*;

pub struct PythonCachedRefs {
    pub new_event_loop: PyObject,
    pub set_event_loop: PyObject,
    pub request_class: PyObject,
}
