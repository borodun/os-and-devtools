#include "router.h"
#include "net.h"
#include "utils.h"

#include <errno.h>
#include <stdio.h>
#include <sys/socket.h>
#include <unistd.h>

int main(void)
{
    int port = cfg_int("PORT", 8080, 1, 65535);
    const char *config = cfg_string("BACKENDS", "backend-1:9000,backend-2:9000");
    Backend backends[2];
    if (router_parse(config, backends) != 0) {
        fprintf(stderr, "BACKENDS must be host:port,host:port\n");
        return 1;
    }

    for (int i = 0; i < 2; ++i) {
        if (net_wait_for(backends[i].host, backends[i].port, 50, 100) != 0) {
            fprintf(stderr, "Backend %s:%d is not ready\n", backends[i].host, backends[i].port);
            return 1;
        }
    }

    int server = net_listen(port);
    if (server < 0) {
        perror("balancer: listen");
        return 1;
    }
    printf("balancer listening on %d\n", port);
    fflush(stdout);

    size_t next = 0;
    for (;;) {
        int client = accept(server, NULL, NULL);
        if (client < 0) {
            if (errno == EINTR)
                continue;
            perror("balancer: accept");
            break;
        }
        router_handle(client, backends, &next);
        close(client);
    }
    close(server);
    return 1;
}
