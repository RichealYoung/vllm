// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: Copyright contributors to the vLLM project

#include <Python.h>

namespace {
PyObject* token_lcp(PyObject*, PyObject* args) {
  PyObject *a, *b;
  Py_ssize_t n;
  if (!PyArg_ParseTuple(args, "OOn", &a, &b, &n)) return nullptr;
  if (!PyList_CheckExact(a) || !PyList_CheckExact(b) || n < 0 ||
      n > PyList_Size(a) || n > PyList_Size(b)) {
    PyErr_SetString(PyExc_ValueError,
                    "expected exact lists and bounded length");
    return nullptr;
  }
  Py_ssize_t i = 0;
  for (; i < n; ++i) {
    PyObject *x = PyList_GetItem(a, i), *y = PyList_GetItem(b, i);
    if (!PyLong_CheckExact(x) || !PyLong_CheckExact(y)) {
      PyErr_SetString(PyExc_ValueError, "expected integer token IDs");
      return nullptr;
    }
    unsigned long u = PyLong_AsUnsignedLong(x);
    if (PyErr_Occurred()) return nullptr;
    unsigned long v = PyLong_AsUnsignedLong(y);
    if (PyErr_Occurred()) return nullptr;
    if (u != v) break;
  }
  return PyLong_FromSsize_t(i);
}
PyMethodDef methods[] = {{"token_lcp", token_lcp, METH_VARARGS,
                          "Exact token prefix length under the GIL."},
                         {nullptr, nullptr, 0, nullptr}};
PyModuleDef module = {PyModuleDef_HEAD_INIT, "_session_prefix", nullptr, -1,
                      methods};
}  // namespace
PyMODINIT_FUNC PyInit__session_prefix() { return PyModule_Create(&module); }
