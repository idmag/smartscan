/* Auto-generated no-op implementations for headless Qt smoke tests. */
#include <stddef.h>
void *dbus_bus_get_unique_name(void *a){(void)a;return NULL;}
int dbus_connection_set_allow_anonymous(void *a,int b){(void)a;(void)b;return 1;}
int dbus_connection_set_dispatch_status_function(void *a,void *b,void *c,void *d){(void)a;(void)b;(void)c;(void)d;return 1;}
int dbus_message_get_allow_interactive_authorization(void *a){(void)a;return 0;}
int dbus_message_set_allow_interactive_authorization(void *a,int b){(void)a;(void)b;return 1;}
int dbus_message_iter_append_fixed_array(void *a,int b,const void *c,int d){(void)a;(void)b;(void)c;(void)d;return 1;}
int dbus_message_iter_get_element_type(void *a){(void)a;return 0;}
int dbus_message_iter_get_fixed_array(void *a,void *b,int *c){(void)a;(void)b;(void)c;return 0;}
char *dbus_message_iter_get_signature(void *a){(void)a;return NULL;}
int dbus_message_set_error_name(void *a,const char *b){(void)a;(void)b;return 1;}
int dbus_message_set_reply_serial(void *a,unsigned int b){(void)a;(void)b;return 1;}
int dbus_message_set_sender(void *a,const char *b){(void)a;(void)b;return 1;}
void dbus_pending_call_block(void *a){(void)a;}
void dbus_pending_call_cancel(void *a){(void)a;}
int dbus_server_allocate_data_slot(int *a){(void)a;return 0;}
void dbus_server_free_data_slot(int *a){(void)a;}
int dbus_server_set_data(void *a,int b,void *c,void *d){(void)a;(void)b;(void)c;(void)d;return 1;}
int dbus_timeout_get_enabled(void *a){(void)a;return 0;}
int dbus_timeout_get_interval(void *a){(void)a;return 0;}
int dbus_timeout_handle(void *a){(void)a;return 0;}
int dbus_watch_get_enabled(void *a){(void)a;return 0;}
int dbus_watch_get_flags(void *a){(void)a;return 0;}
int dbus_watch_get_unix_fd(void *a){(void)a;return -1;}
int dbus_watch_handle(void *a,int b){(void)a;(void)b;return 0;}
