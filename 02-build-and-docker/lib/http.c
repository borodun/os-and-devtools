#include "http.h"
#include "net.h"

#include <stdio.h>
#include <string.h>
#include <sys/socket.h>

int http_read_request(int fd)
{
    char buffer[2048];
    size_t used = 0;

    while (used + 1 < sizeof(buffer)) {
        ssize_t n = recv(fd, buffer + used, sizeof(buffer) - used - 1, 0);
        if (n <= 0)
            return n == 0 ? 0 : -1;
        used += (size_t)n;
        buffer[used] = '\0';
        if (strstr(buffer, "\r\n\r\n") != NULL)
            return strncmp(buffer, "GET / HTTP/1.", 13) == 0 ? 1 : -1;
    }
    return -1;
}

int http_send_get(int fd)
{
    static const char request[] =
        "GET / HTTP/1.0\r\nHost: lab\r\nConnection: close\r\n\r\n";
    return net_send_all(fd, request, sizeof(request) - 1);
}

int http_send_response(int fd, int status, const char *backend, const char *body)
{
    const char *reason = status == 200 ? "OK" :
                         status == 400 ? "Bad Request" : "Bad Gateway";
    char header[512];
    int n = snprintf(header, sizeof(header),
                     "HTTP/1.0 %d %s\r\n"
                     "Content-Type: text/plain\r\n"
                     "Content-Length: %zu\r\n"
                     "X-Backend: %s\r\n"
                     "Connection: close\r\n\r\n",
                     status, reason, strlen(body), backend);
    if (n < 0 || (size_t)n >= sizeof(header))
        return -1;
    return net_send_all(fd, header, (size_t)n) == 0 &&
           net_send_all(fd, body, strlen(body)) == 0 ? 0 : -1;
}

int http_read_response(int fd, char *buffer, size_t capacity)
{
    size_t used = 0;
    if (capacity < 2)
        return -1;

    while (used + 1 < capacity) {
        ssize_t n = recv(fd, buffer + used, capacity - used - 1, 0);
        if (n < 0)
            return -1;
        if (n == 0) {
            buffer[used] = '\0';
            return (int)used;
        }
        used += (size_t)n;
    }
    return -1;
}
