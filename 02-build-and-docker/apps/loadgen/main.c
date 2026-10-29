#define _POSIX_C_SOURCE 200809L
#include "stats.h"
#include "http.h"
#include "net.h"
#include "utils.h"

#include <stdio.h>
#include <time.h>
#include <unistd.h>

static double elapsed_ms(const struct timespec *start, const struct timespec *end)
{
    return (end->tv_sec - start->tv_sec) * 1000.0 +
           (end->tv_nsec - start->tv_nsec) / 1000000.0;
}

int main(void)
{
    const char *host = cfg_string("TARGET_HOST", "balancer");
    int port = cfg_int("TARGET_PORT", 8080, 1, 65535);
    int count = cfg_int("REQUEST_COUNT", 1000, 1, 1000000);
    const char *path = cfg_string("OUTPUT_FILE", "result.csv");

    if (net_wait_for(host, port, 50, 100) != 0) {
        fprintf(stderr, "Target %s:%d is not ready\n", host, port);
        return 1;
    }

    FILE *output = fopen(path, "w");
    if (!output) {
        perror(path);
        return 1;
    }
    stats_header(output);

    Stats stats;
    stats_init(&stats);

    for (int i = 1; i <= count; ++i) {
        struct timespec start, end;
        char response[4096] = "";
        clock_gettime(CLOCK_MONOTONIC, &start);

        int fd = net_connect(host, port);
        if (fd >= 0) {
            if (http_send_get(fd) == 0 &&
                http_read_response(fd, response, sizeof(response)) < 0)
                response[0] = '\0';
            close(fd);
        }
        clock_gettime(CLOCK_MONOTONIC, &end);
        stats_record(&stats, output, i, response, elapsed_ms(&start, &end));
    }

    if (fclose(output) != 0) {
        perror("write results");
        return 1;
    }

    stats_print(&stats, path);
    return stats.ok == stats.total ? 0 : 1;
}
