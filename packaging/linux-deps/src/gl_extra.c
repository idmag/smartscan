/* No-op GL/GLX entry points so Qt can load in containers without a GPU. */
#include <stddef.h>
const unsigned char *glGetString(unsigned int name) { (void)name; return (const unsigned char*)""; }
int glGetError(void) { return 0; }
void glGetIntegerv(unsigned int p, int *v) { (void)p; if (v) v[0] = 0; }
void *glXChooseFBConfig(void *d, int s, const int *a, int *n) { (void)d;(void)s;(void)a;(void)n; return 0; }
void *glXChooseVisual(void *d, int s, const int *a) { (void)d;(void)s;(void)a; return 0; }
int glXGetConfig(void *d, void *v, int a, int *r) { (void)d;(void)v;(void)a;(void)r; return 0; }
int glXGetFBConfigAttrib(void *d, void *c, int a, int *v) { (void)d;(void)c;(void)a;(void)v; return 0; }
void *glXGetVisualFromFBConfig(void *d, void *c) { (void)d;(void)c; return 0; }
void *glXGetProcAddress(const unsigned char *n) { (void)n; return 0; }
void *glXCreateContext(void *d, void *v, void *s, int b) { (void)d;(void)v;(void)s;(void)b; return 0; }
void *glXCreateNewContext(void *d, void *c, int t, void *s, int b) { (void)d;(void)c;(void)t;(void)s;(void)b; return 0; }
void glXDestroyContext(void *d, void *c) { (void)d;(void)c; }
int glXMakeCurrent(void *d, unsigned long w, void *c) { (void)d;(void)w;(void)c; return 0; }
void *glXGetProcAddressARB(const unsigned char *n) { (void)n; return 0; }
void glViewport(int x, int y, int w, int h) { (void)x;(void)y;(void)w;(void)h; }
