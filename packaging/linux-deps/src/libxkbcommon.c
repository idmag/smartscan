/* Minimal no-op stand-in for libxkbcommon, used ONLY so that Qt's offscreen
 * platform can start inside a bare CI container for GUI smoke tests. */
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

typedef struct xkb_context { int dummy; } xkb_context;
typedef struct xkb_keymap { int dummy; } xkb_keymap;
typedef struct xkb_state { int dummy; } xkb_state;
typedef struct xkb_rule_names { const char *rules, *model, *layout, *variant, *options; } xkb_rule_names;

static xkb_context ctx_singleton;
static xkb_keymap km_singleton;
static xkb_state st_singleton;

xkb_context *xkb_context_new(int flags) { (void)flags; return &ctx_singleton; }
xkb_context *xkb_context_ref(xkb_context *c) { return c; }
void xkb_context_unref(xkb_context *c) { (void)c; }
void xkb_context_set_log_level(xkb_context *c, int level) { (void)c; (void)level; }
void xkb_context_set_log_fn(xkb_context *c, void *fn, void *data) { (void)c; (void)fn; (void)data; }

xkb_keymap *xkb_keymap_new_from_names(xkb_context *c, const xkb_rule_names *r, int flags) {
  (void)c; (void)r; (void)flags; return &km_singleton;
}
xkb_keymap *xkb_keymap_new_from_string(xkb_context *c, const char *s, int f, int g) {
  (void)c; (void)s; (void)f; (void)g; return &km_singleton;
}
xkb_keymap *xkb_keymap_ref(xkb_keymap *k) { return k; }
void xkb_keymap_unref(xkb_keymap *k) { (void)k; }
char *xkb_keymap_get_as_string(xkb_keymap *k, int f) {
  (void)k; (void)f;
  const char *s = "xkb_keymap { xkb_keycodes { include \"evdev+aliases(qwerty)\" };"
                  " xkb_types { include \"complete\" };"
                  " xkb_compat { include \"complete\" };"
                  " xkb_symbols { include \"pc+us\" }; };";
  char *out = malloc(strlen(s) + 1);
  if (out) strcpy(out, s);
  return out;
}
int xkb_keymap_min_keycode(xkb_keymap *k) { (void)k; return 8; }
int xkb_keymap_max_keycode(xkb_keymap *k) { (void)k; return 255; }
void xkb_keymap_key_for_each(xkb_keymap *k, void *fn, void *d) { (void)k; (void)fn; (void)d; }
const char *xkb_keymap_key_get_name(xkb_keymap *k, int key) { (void)k; (void)key; return NULL; }
int xkb_keymap_key_by_name(xkb_keymap *k, const char *n) { (void)k; (void)n; return 0; }
int xkb_keymap_num_layouts(xkb_keymap *k) { (void)k; return 1; }
int xkb_keymap_num_layouts_for_key(xkb_keymap *k, int key) { (void)k; (void)key; return 1; }
int xkb_keymap_num_levels_for_key(xkb_keymap *k, int key, int lay) { (void)k; (void)key; (void)lay; return 2; }
int xkb_keymap_num_mods(xkb_keymap *k) { (void)k; return 8; }
int xkb_keymap_num_leds(xkb_keymap *k) { (void)k; return 0; }
const char *xkb_keymap_layout_get_name(xkb_keymap *k, int i) { (void)k; (void)i; return "English (US)"; }
const char *xkb_keymap_key_get_syms_by_level(xkb_keymap *k, int key, int lay, int lev, const int **syms) {
  (void)k; (void)lay; (void)lev;
  static const int syms_table[1] = { 0 };
  if (syms) *syms = syms_table;
  (void)key;
  return NULL;
}
unsigned int xkb_keysym_from_name(const char *n, int f) { (void)n; (void)f; return 0; }
int xkb_keysym_to_utf8(unsigned int sym, char *buf, unsigned int size) { (void)sym; if (buf && size) buf[0] = 0; return 0; }
unsigned int xkb_keysym_to_utf32(unsigned int sym) { (void)sym; return 0; }
unsigned int xkb_utf32_to_keysym(unsigned int u) { (void)u; return 0; }

xkb_state *xkb_state_new(xkb_keymap *k) { (void)k; return &st_singleton; }
xkb_state *xkb_state_ref(xkb_state *s) { return s; }
void xkb_state_unref(xkb_state *s) { (void)s; } 
int xkb_state_update_key(xkb_state *s, int key, int dir) { (void)s; (void)key; (void)dir; return 0; }
int xkb_state_update_mask(xkb_state *s, int a, int b, int c, int d, int e, int f) {
  (void)s; (void)a; (void)b; (void)c; (void)d; (void)e; (void)f; return 0;
}
int xkb_state_key_get_layout(xkb_state *s, int key) { (void)s; (void)key; return 0; }
int xkb_state_key_get_level(xkb_state *s, int key, int lay) { (void)s; (void)key; (void)lay; return 0; }
int xkb_state_key_get_syms(xkb_state *s, int key, const int **syms) {
  (void)s; (void)key;
  static const int syms_table[1] = { 0 };
  if (syms) *syms = syms_table;
  return 1;
}
unsigned int xkb_state_key_get_one_sym(xkb_state *s, int key) { (void)s; (void)key; return 0; }
int xkb_state_key_get_utf8(xkb_state *s, int key, char *buf, unsigned int size) {
  (void)s; (void)key; if (buf && size) buf[0] = 0; return 0;
}
unsigned int xkb_state_key_get_utf32(xkb_state *s, int key) { (void)s; (void)key; return 0; }
int xkb_state_serialize_layout(xkb_state *s) { (void)s; return 0; }
int xkb_state_serialize_mods(xkb_state *s, int comp) { (void)s; (void)comp; return 0; }
int xkb_state_mod_name_is_active(xkb_state *s, const char *n, int t) { (void)s; (void)n; (void)t; return 0; }
int xkb_state_mod_index_is_active(xkb_state *s, int idx, int t) { (void)s; (void)idx; (void)t; return 0; }
int xkb_state_layout_index_is_active(xkb_state *s, int idx, int t) { (void)s; (void)idx; (void)t; return 0; }
const char *xkb_state_key_get_keyname(xkb_state *s, int key) { (void)s; (void)key; return NULL; }
int xkb_keymap_mod_get_index(xkb_keymap *k, const char *n) { (void)k; (void)n; return 0; }
xkb_keymap *xkb_state_get_keymap(xkb_state *s) { (void)s; return &km_singleton; }
