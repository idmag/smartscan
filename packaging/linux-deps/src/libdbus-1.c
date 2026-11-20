/* Minimal no-op stand-in for libdbus-1, ONLY for headless Qt smoke tests. */
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

typedef struct DBusConnection { int dummy; } DBusConnection;
typedef struct DBusMessage { int dummy; } DBusMessage;
typedef struct DBusError { const char *name; const char *message; unsigned int dummy; } DBusError;
typedef struct DBusBus { int dummy; } DBusBus;
typedef struct DBusPendingCall { int dummy; } DBusPendingCall;

static DBusError err_singleton;
static DBusConnection conn_singleton;

void dbus_error_init(DBusError *e) { if (e) { e->name = NULL; e->message = NULL; } }
void dbus_error_free(DBusError *e) { if (e) { e->name = NULL; e->message = NULL; } }
int dbus_error_is_set(const DBusError *e) { (void)e; return 0; }
void dbus_shutdown(void) {}

DBusConnection *dbus_bus_get(int type, DBusError *e) { (void)type; (void)e; return &conn_singleton; }
DBusConnection *dbus_bus_get_private(int type, DBusError *e) { (void)type; (void)e; return &conn_singleton; }
int dbus_bus_register(DBusConnection *c, DBusError *e) { (void)c; (void)e; return 1; }
void dbus_connection_set_exit_on_disconnect(DBusConnection *c, int b) { (void)c; (void)b; }
int dbus_connection_get_is_connected(DBusConnection *c) { (void)c; return 0; }
void dbus_connection_close(DBusConnection *c) { (void)c; }
void dbus_connection_unref(DBusConnection *c) { (void)c; }
DBusConnection *dbus_connection_ref(DBusConnection *c) { return c; }
int dbus_connection_get_unix_fd(DBusConnection *c, int *fd) { (void)c; if (fd) *fd = -1; return 0; }
int dbus_connection_get_unix_user(DBusConnection *c, unsigned long *u) { (void)c; if (u) *u = 0; return 0; }
unsigned long dbus_connection_get_serial(DBusConnection *c) { (void)c; return 1; }

DBusMessage *dbus_message_new_method_call(const char *bus, const char *path, const char *iface, const char *member) {
  (void)bus; (void)path; (void)iface; (void)member; return NULL;
}
void dbus_message_unref(DBusMessage *m) { (void)m; }
DBusMessage *dbus_message_ref(DBusMessage *m) { return m; }
int dbus_message_append_args(DBusMessage *m, int first_arg_type, ...) { (void)m; (void)first_arg_type; return 1; }
int dbus_message_get_args(DBusMessage *m, DBusError *e, int first_arg_type, ...) { (void)m; (void)e; (void)first_arg_type; return 0; }
int dbus_message_get_type(DBusMessage *m) { (void)m; return 0; }
const char *dbus_message_get_member(DBusMessage *m) { (void)m; return NULL; }
const char *dbus_message_get_sender(DBusMessage *m) { (void)m; return NULL; }
const char *dbus_message_get_interface(DBusMessage *m) { (void)m; return NULL; }
const char *dbus_message_get_path(DBusMessage *m) { (void)m; return NULL; }
const char *dbus_message_get_destination(DBusMessage *m) { (void)m; return NULL; }
const char *dbus_message_get_signature(DBusMessage *m) { (void)m; return NULL; }
DBusMessage *dbus_message_new_signal(const char *p, const char *i, const char *n) { (void)p; (void)i; (void)n; return NULL; }
DBusMessage *dbus_message_new_method_return(DBusMessage *m) { (void)m; return NULL; }
DBusMessage *dbus_message_new_error(DBusMessage *m, const char *n, const char *msg) { (void)m; (void)n; (void)msg; return NULL; }

int dbus_connection_send(DBusConnection *c, DBusMessage *m, unsigned int *serial) {
  (void)c; (void)m; if (serial) *serial = 1; return 1;
}
int dbus_connection_send_with_reply(DBusConnection *c, DBusMessage *m, DBusPendingCall **p, int timeout) {
  (void)c; (void)m; (void)timeout; if (p) *p = NULL; return 1;
}
int dbus_connection_send_with_reply_and_block(DBusConnection *c, DBusMessage *m, int timeout, DBusError *e) {
  (void)c; (void)m; (void)timeout; (void)e; return 0;
}
int dbus_connection_read_write_dispatch(DBusConnection *c, int timeout) { (void)c; (void)timeout; return 0; }
int dbus_connection_read_write(DBusConnection *c, int timeout) { (void)c; (void)timeout; return 0; }
DBusMessage *dbus_connection_pop_message(DBusConnection *c) { (void)c; return NULL; }
int dbus_connection_add_filter(DBusConnection *c, void *fn, void *d, void *free_data) {
  (void)c; (void)fn; (void)d; (void)free_data; return 1;
}
void dbus_connection_remove_filter(DBusConnection *c, void *fn, void *d) { (void)c; (void)fn; (void)d; }
int dbus_connection_register_object_path(DBusConnection *c, const char *p, const void *v, void *d) {
  (void)c; (void)p; (void)v; (void)d; return 1;
}
int dbus_connection_set_timeout_functions(DBusConnection *c, void *a, void *b, void *d, void *e, void *f) {
  (void)c; (void)a; (void)b; (void)d; (void)e; (void)f; return 1;
}
int dbus_connection_set_watch_functions(DBusConnection *c, void *a, void *b, void *d, void *e, void *f) {
  (void)c; (void)a; (void)b; (void)d; (void)e; (void)f; return 1;
}
void dbus_connection_flush(DBusConnection *c) { (void)c; }
int dbus_connection_get_dispatch_status(DBusConnection *c) { (void)c; return 0; }
int dbus_connection_dispatch(DBusConnection *c) { (void)c; return 0; }
int dbus_bus_add_match(DBusConnection *c, const char *r, DBusError *e) { (void)c; (void)r; (void)e; return 1; }
int dbus_bus_remove_match(DBusConnection *c, const char *r, DBusError *e) { (void)c; (void)r; (void)e; return 1; }
int dbus_bus_request_name(DBusConnection *c, const char *n, unsigned int f, DBusError *e) {
  (void)c; (void)n; (void)f; (void)e; return 1;
}
int dbus_bus_release_name(DBusConnection *c, const char *n, DBusError *e) {
  (void)c; (void)n; (void)e; return 1;
}
unsigned long dbus_bus_get_unix_user(DBusConnection *c, const char *n, DBusError *e) {
  (void)c; (void)n; (void)e; return 0;
}
void dbus_pending_call_unref(DBusPendingCall *p) { (void)p; }
int dbus_pending_call_get_completed(DBusPendingCall *p) { (void)p; return 1; }
DBusMessage *dbus_pending_call_steal_reply(DBusPendingCall *p) { (void)p; return NULL; }
int dbus_pending_call_set_notify(DBusPendingCall *p, void *fn, void *d, void *f) {
  (void)p; (void)fn; (void)d; (void)f; return 1;
}
const char *dbus_get_local_machine_id(void) { return "00000000000000000000000000000000"; }
int dbus_threads_init_default(void) { return 1; }
int dbus_connection_get_is_authenticated(DBusConnection *c) { (void)c; return 0; }
int dbus_connection_can_send_type(DBusConnection *c, int t) { (void)c; (void)t; return 0; }
void dbus_free(void *p) { free(p); }
char *dbus_malloc(int n) { return malloc((size_t)n); }
