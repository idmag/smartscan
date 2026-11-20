/* Extra no-op EGL symbols for container smoke tests. */
#include <stddef.h>
int eglQueryContext(void *d, void *c, int a, int *v) { (void)d;(void)c;(void)a;(void)v; return 0; }
int eglQueryDeviceAttribEXT(void *d, int a, int *v) { (void)d;(void)a;(void)v; return 0; }
int eglQueryDevicesEXT(int m, void **d, int *n) { (void)m;(void)d;(void)n; return 0; }
int eglQueryDisplayAttribEXT(void *d, int a, void *v) { (void)d;(void)a;(void)v; return 0; }
int eglQueryStringiEXT(void *d, int n, int i) { (void)d;(void)n;(void)i; return 0; }
const char *eglQueryString2(void *d, int n) { (void)d;(void)n; return ""; }
