#define _POSIX_C_SOURCE 200809L
#include "net.h"

#include <arpa/inet.h>
#include <errno.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

int net_listen(int port)
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0)
        return -1;

    int reuse = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons((unsigned short)port);

    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0 || listen(fd, 32) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

int net_connect(const char *host, int port)
{
    char service[16];
    snprintf(service, sizeof(service), "%d", port);

    struct addrinfo hints = {0};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    struct addrinfo *results;
    if (getaddrinfo(host, service, &hints, &results) != 0)
        return -1;

    int fd = -1;
    for (struct addrinfo *p = results; p != NULL; p = p->ai_next) {
        fd = socket(p->ai_family, p->ai_socktype, p->ai_protocol);
        if (fd < 0)
            continue;
        if (connect(fd, p->ai_addr, p->ai_addrlen) == 0)
            break;
        close(fd);
        fd = -1;
    }

    freeaddrinfo(results);
    return fd;
}

int net_wait_for(const char *host, int port, int attempts, int delay_ms)
{
    struct timespec pause = {delay_ms / 1000, (delay_ms % 1000) * 1000000L};
    for (int i = 0; i < attempts; ++i) {
        int fd = net_connect(host, port);
        if (fd >= 0) {
            close(fd);
            return 0;
        }
        if (i + 1 < attempts)
            nanosleep(&pause, NULL);
    }
    return -1;
}

int net_send_all(int fd, const void *buffer, size_t size)
{
    const char *p = buffer;
    while (size > 0) {
        ssize_t sent = send(fd, p, size, MSG_NOSIGNAL);
        if (sent < 0 && errno == EINTR)
            continue;
        if (sent <= 0)
            return -1;
        p += sent;
        size -= (size_t)sent;
    }
    return 0;
}
