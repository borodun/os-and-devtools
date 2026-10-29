#ifndef LAB_ROUTER_H
#define LAB_ROUTER_H

#include <stddef.h>

typedef struct {
    char host[128];
    int port;
} Backend;

int router_parse(const char *config, Backend backends[2]);
void router_handle(int client, const Backend backends[2], size_t *next);

#endif
