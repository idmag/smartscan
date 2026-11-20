/* Additional no-op symbols for the headless test shim. */
#include <stddef.h>
void *dbus_server_get_address(void) { return NULL; }
void *dbus_server_listen(const char *a, void *b) { (void)a; (void)b; return NULL; }
void dbus_server_disconnect(void *s) { (void)s; }
void dbus_server_unref(void *s) { (void)s; }
void *dbus_server_ref(void *s) { return s; }
int dbus_server_set_new_connection_function(void *s, void *f, void *d, void *e) { (void)s;(void)f;(void)d;(void)e; return 1; }
int dbus_server_set_watch_functions(void *s, void *a, void *b, void *c, void *d, void *e) { (void)s;(void)a;(void)b;(void)c;(void)d;(void)e; return 1; }
int dbus_server_set_timeout_functions(void *s, void *a, void *b, void *c, void *d, void *e) { (void)s;(void)a;(void)b;(void)c;(void)d;(void)e; return 1; }
int dbus_server_get_is_connected(void *s) { (void)s; return 0; }
void *dbus_connection_open(const char *a, void *b) { (void)a; (void)b; return NULL; }
void *dbus_connection_open_private(const char *a, void *b) { (void)a; (void)b; return NULL; }
int dbus_connection_try_register_object_path(void *c, const char *p, const void *v, void *d, void *e) { (void)c;(void)p;(void)v;(void)d;(void)e; return 0; }
int dbus_connection_try_register_fallback(void *c, const char *p, const void *v, void *d, void *e) { (void)c;(void)p;(void)v;(void)d;(void)e; return 0; }
int dbus_connection_register_fallback(void *c, const char *p, const void *v, void *d) { (void)c;(void)p;(void)v;(void)d; return 1; }
void dbus_connection_unregister_object_path(void *c, const char *p) { (void)c;(void)p; }
void dbus_connection_set_max_message_size(void *c, long s) { (void)c;(void)s; }
void dbus_connection_set_max_received_size(void *c, long s) { (void)c;(void)s; }
long dbus_connection_get_max_message_size(void *c) { (void)c; return 0; }
long dbus_connection_get_max_received_size(void *c) { (void)c; return 0; }
void dbus_connection_set_route_peer_messages(void *c, int b) { (void)c;(void)b; }
unsigned int dbus_message_get_reply_serial(void *m) { (void)m; return 0; }
int dbus_message_get_no_reply(void *m) { (void)m; return 0; }
int dbus_message_set_no_reply(void *m, int b) { (void)m;(void)b; return 1; }
int dbus_message_is_signal(void *m, const char *i, const char *n) { (void)m;(void)i;(void)n; return 0; }
int dbus_message_is_method_call(void *m, const char *i, const char *n) { (void)m;(void)i;(void)n; return 0; }
int dbus_message_is_method_return(void *m) { (void)m; return 0; }
int dbus_message_is_error(void *m, const char *n) { (void)m;(void)n; return 0; }
int dbus_message_iter_init(void *m, void *it) { (void)m;(void)it; return 0; }
int dbus_message_iter_get_arg_type(void *it) { (void)it; return 0; }
int dbus_message_iter_next(void *it) { (void)it; return 0; }
int dbus_message_iter_append_basic(void *it, int t, const void *v) { (void)it;(void)t;(void)v; return 1; }
int dbus_message_iter_get_basic(void *it, void *v) { (void)it;(void)v; return 0; }
void dbus_message_iter_init_append(void *m, void *it) { (void)m;(void)it; }
int dbus_message_iter_open_container(void *it, int t, const char *s, void *sub) { (void)it;(void)t;(void)s;(void)sub; return 1; }
int dbus_message_iter_close_container(void *it, void *sub) { (void)it;(void)sub; return 1; }
void dbus_message_iter_recurse(void *it, void *sub) { (void)it;(void)sub; }
void dbus_message_iter_abandon_container(void *it, void *sub) { (void)it;(void)sub; }
int dbus_message_set_destination(void *m, const char *s) { (void)m;(void)s; return 1; }
int dbus_message_set_interface(void *m, const char *s) { (void)m;(void)s; return 1; }
int dbus_message_set_member(void *m, const char *s) { (void)m;(void)s; return 1; }
int dbus_message_set_path(void *m, const char *s) { (void)m;(void)s; return 1; }
const char *dbus_message_get_error_name(void *m) { (void)m; return NULL; }
void *dbus_message_copy(void *m) { (void)m; return NULL; }
unsigned int dbus_message_get_serial(void *m) { (void)m; return 0; }
void *dbus_message_new(int t) { (void)t; return NULL; }
int dbus_message_get_auto_start(void *m) { (void)m; return 0; }
int dbus_message_set_auto_start(void *m, int b) { (void)m;(void)b; return 1; }
