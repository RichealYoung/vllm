#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>
#if defined(__x86_64__) && defined(__GNUC__)
#include <immintrin.h>
#define X86_AVX2 1
#endif

/* No pointer-equality shortcut: inputs may contain separately decoded ints.
 * Keep the GIL while reading Python objects; don't use private PyLong layout. */
static PyObject *list_lcp(PyObject *self, PyObject *args) {
    PyObject *a, *b; Py_ssize_t n; int unbox;
    if (!PyArg_ParseTuple(args, "OOnp", &a, &b, &n, &unbox)) return NULL;
    if (!PyList_CheckExact(a) || !PyList_CheckExact(b) || n < 0 ||
        n > PyList_GET_SIZE(a) || n > PyList_GET_SIZE(b)) {
        PyErr_SetString(PyExc_ValueError, "expected exact lists and bounded n"); return NULL;
    }
    Py_ssize_t i = 0;
    for (; i < n; i++) {
        PyObject *x = PyList_GET_ITEM(a, i), *y = PyList_GET_ITEM(b, i);
        if (unbox) {
            unsigned long u = PyLong_AsUnsignedLong(x);
            if (PyErr_Occurred()) return NULL;
            unsigned long v = PyLong_AsUnsignedLong(y);
            if (PyErr_Occurred()) return NULL;
            if (u != v) break;
        } else {
            int eq = PyObject_RichCompareBool(x, y, Py_EQ);
            if (eq < 0) return NULL;
            if (!eq) break;
        }
    }
    return PyLong_FromSsize_t(i);
}

static size_t word_lcp(const unsigned char *a, const unsigned char *b, size_t n) {
    size_t bytes = n * 4, i = 0;
    while (bytes - i >= 8) {
        uint64_t x, y; memcpy(&x, a+i, 8); memcpy(&y, b+i, 8);
        uint64_t d = x ^ y;
        if (d) {
#if defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
            return (i + __builtin_ctzll(d)/8) / 4;
#else
            for (size_t k=0;k<8;k++) if(a[i+k]!=b[i+k]) return (i+k)/4;
#endif
        }
        i += 8;
    }
    for (; i < bytes; i++) if(a[i]!=b[i]) return i/4;
    return n;
}

#ifdef X86_AVX2
__attribute__((target("avx2")))
static size_t avx2_lcp(const unsigned char *a, const unsigned char *b, size_t n) {
    size_t i = 0;
    for (; n-i >= 8; i+=8) {
        __m256i x = _mm256_loadu_si256((const __m256i *)(a+4*i));
        __m256i y = _mm256_loadu_si256((const __m256i *)(b+4*i));
        unsigned mask = (unsigned)_mm256_movemask_ps(_mm256_castsi256_ps(_mm256_cmpeq_epi32(x,y)));
        if(mask != 255) return i + __builtin_ctz((~mask)&255);
    }
    return i + word_lcp(a+4*i,b+4*i,n-i);
}
#endif

static PyObject *buffer_lcp(PyObject *self, PyObject *args) {
    PyObject *a,*b; Py_ssize_t n; int avx;
    if(!PyArg_ParseTuple(args,"OOnp",&a,&b,&n,&avx)) return NULL;
    Py_buffer x,y;
    if(PyObject_GetBuffer(a,&x,PyBUF_CONTIG_RO)<0) return NULL;
    if(PyObject_GetBuffer(b,&y,PyBUF_CONTIG_RO)<0) {PyBuffer_Release(&x);return NULL;}
    if(n<0 || n>x.len/4 || n>y.len/4 || x.itemsize!=4 || y.itemsize!=4) {
        PyErr_SetString(PyExc_ValueError,"expected bounded contiguous 4-byte buffers");
        PyBuffer_Release(&x);PyBuffer_Release(&y);return NULL;
    }
    size_t result;
#ifdef X86_AVX2
    if(avx && __builtin_cpu_supports("avx2")) result=avx2_lcp(x.buf,y.buf,(size_t)n);
    else
#endif
    result=word_lcp(x.buf,y.buf,(size_t)n);
    PyBuffer_Release(&x);PyBuffer_Release(&y);
    return PyLong_FromSize_t(result);
}
static PyObject *features(PyObject *s, PyObject *unused) {
#ifdef X86_AVX2
    return Py_BuildValue("{s:O}","avx2",__builtin_cpu_supports("avx2")?Py_True:Py_False);
#else
    return Py_BuildValue("{s:O}","avx2",Py_False);
#endif
}
static PyMethodDef methods[]={
    {"list_lcp",list_lcp,METH_VARARGS,"Bounded list LCP under the GIL."},
    {"buffer_lcp",buffer_lcp,METH_VARARGS,"Bounded uint32 buffer LCP."},
    {"features",features,METH_NOARGS,"Runtime features."},{NULL,NULL,0,NULL}};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"matcher",NULL,-1,methods};
PyMODINIT_FUNC PyInit_matcher(void){return PyModule_Create(&module);}
