/* Extra no-op EGL symbols for headless Qt smoke tests. */
#include <stddef.h>
const char *eglQueryString(void *d, int name) { (void)d; (void)name; return ""; }
void *eglGetDisplay(void *n) { (void)n; return NULL; }
int eglInitialize(void *d, void *a, void *b) { (void)d; (void)a; (void)b; return 0; }
int eglTerminate(void *d) { (void)d; return 0; }
int eglGetError(void) { return 0; }
void *eglGetCurrentContext(void) { return NULL; }
void *eglGetCurrentDisplay(void) { return NULL; }
void *eglGetCurrentSurface(int t) { (void)t; return NULL; }
int eglBindAPI(unsigned int a) { (void)a; return 1; }
void *eglCreateContext(void *a, void *b, void *c, const int *d) { (void)a;(void)b;(void)c;(void)d; return NULL; }
int eglDestroyContext(void *a, void *b) { (void)a;(void)b; return 1; }
int eglMakeCurrent(void *a, void *b, void *c, void *d) { (void)a;(void)b;(void)c;(void)d; return 0; }
void *eglCreateWindowSurface(void *a, void *b, void *c, const int *d) { (void)a;(void)b;(void)c;(void)d; return NULL; }
void *eglCreatePbufferSurface(void *a, void *b, const int *c) { (void)a;(void)b;(void)c; return NULL; }
int eglDestroySurface(void *a, void *b) { (void)a;(void)b; return 1; }
int eglQuerySurface(void *a, void *b, int c, int *d) { (void)a;(void)b;(void)c;(void)d; return 0; }
int eglSwapBuffers(void *a, void *b) { (void)a;(void)b; return 0; }
int eglReleaseThread(void) { return 1; }
int eglWaitClient(void) { return 1; }
int eglSwapInterval(void *a, int b) { (void)a;(void)b; return 1; }
void *eglGetProcAddress(const char *name) { (void)name; return NULL; }
void *eglGetPlatformDisplay(unsigned int p, void *d, const void *a) { (void)p;(void)d;(void)a; return NULL; }
int eglChooseConfig(void *d, const int *a, void **b, int c, int *n) { (void)d;(void)a;(void)b;(void)c;(void)n; return 0; }
int eglGetConfigs(void *d, void **a, int b, int *n) { (void)d;(void)a;(void)b;(void)n; return 0; }
int eglGetConfigAttrib(void *d, void *c, int a, int *v) { (void)d;(void)c;(void)a;(void)v; return 0; }
int eglBindTexImage(void *d, void *s, int b) { (void)d;(void)s;(void)b; return 0; }
int eglReleaseTexImage(void *d, void *s, int b) { (void)d;(void)s;(void)b; return 0; }
int eglSurfaceAttrib(void *d, void *s, int a, int v) { (void)d;(void)s;(void)a;(void)v; return 0; }
int eglCopyBuffers(void *d, void *s, void *t) { (void)d;(void)s;(void)t; return 0; }
