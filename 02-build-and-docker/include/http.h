#ifndef LAB_HTTP_H
#define LAB_HTTP_H

#include <stddef.h>

/* 1: GET / received; 0: peer disconnected; -1: invalid request. */
int http_read_request(int fd);
int http_send_get(int fd);
int http_send_response(int fd, int status, const char *backend, const char *body);
/* Returns response size, or -1 on error/overflow. Adds a terminating zero. */
int http_read_response(int fd, char *buffer, size_t capacity);

#endif
