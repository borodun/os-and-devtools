#include "router.h"
#include "http.h"
#include "net.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int router_parse(const char *config, Backend backends[2])
{
    const char *cursor = config;
    for (int i = 0; i < 2; ++i) {
        const char *colon = strchr(cursor, ':');
        if (!colon)
            return -1;
        size_t len = (size_t)(colon - cursor);
        if (!len || len >= sizeof(backends[i].host))
            return -1;
        memcpy(backends[i].host, cursor, len);
        backends[i].host[len] = '\0';

        char *end;
        long port = strtol(colon + 1, &end, 10);
        if (end == colon + 1 || port < 1 || port > 65535)
            return -1;
        backends[i].port = (int)port;
        if (i == 0 && *end != ',')
            return -1;
        if (i == 1 && *end != '\0')
            return -1;
        cursor = end + 1;
    }
    return 0;
}

void router_handle(int client, const Backend backends[2], size_t *next)
{
    int request = http_read_request(client);
    if (request == 0)
        return;
    if (request < 0) {
        http_send_response(client, 400, "none", "Bad request\n");
        return;
    }

    const Backend *target = &backends[*next];
    *next = (*next + 1) % 2;

    printf("routing to %s:%d\n", target->host, target->port);
    fflush(stdout);

    int upstream = net_connect(target->host, target->port);
    if (upstream < 0) {
        http_send_response(client, 502, "none", "Backend unavailable\n");
        return;
    }

    char response[4096];
    int n = -1;
    if (http_send_get(upstream) == 0)
        n = http_read_response(upstream, response, sizeof(response));
    close(upstream);

    if (n <= 0) {
        http_send_response(client, 502, "none", "Backend unavailable\n");
        return;
    }
    net_send_all(client, response, (size_t)n);
}
