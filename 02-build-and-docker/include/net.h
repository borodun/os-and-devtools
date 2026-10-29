#ifndef LAB_NET_H
#define LAB_NET_H

#include <stddef.h>

int net_listen(int port);
int net_connect(const char *host, int port);
int net_wait_for(const char *host, int port, int attempts, int delay_ms);
int net_send_all(int fd, const void *buffer, size_t size);

#endif
