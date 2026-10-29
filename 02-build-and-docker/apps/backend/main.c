#include "handler.h"
#include "net.h"
#include "utils.h"

#include <errno.h>
#include <stdio.h>
#include <sys/socket.h>
#include <unistd.h>

int main(void)
{
    int port = cfg_int("PORT", 9000, 1, 65535);
    const char *name = cfg_string("SERVER_NAME", "backend");
    int server = net_listen(port);
    if (server < 0) {
        perror("backend: listen");
        return 1;
    }

    printf("%s listening on %d\n", name, port);
    fflush(stdout);
    for (;;) {
        int client = accept(server, NULL, NULL);
        if (client < 0) {
            if (errno == EINTR)
                continue;
            perror("backend: accept");
            break;
        }
        backend_handle(client, name);
        close(client);
    }
    close(server);
    return 1;
}
