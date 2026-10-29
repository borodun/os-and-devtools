#include "stats.h"

#include <stdio.h>
#include <string.h>

void stats_init(Stats *s)
{
    s->total = 0;
    s->ok = 0;
    s->min_ms = 0.0;
    s->max_ms = 0.0;
    s->sum_ms = 0.0;
}

void stats_header(FILE *output)
{
    fprintf(output, "request_id,backend,latency_ms,status\n");
}

int stats_record(Stats *s, FILE *output, int request_id,
                 const char *response, double latency_ms)
{
    int status = 0;
    char backend[128] = "none";
    sscanf(response, "HTTP/%*d.%*d %d", &status);

    const char *header = strstr(response, "\r\nX-Backend: ");
    if (header) {
        header += strlen("\r\nX-Backend: ");
        const char *end = strstr(header, "\r\n");
        if (end && end > header && (size_t)(end - header) < sizeof(backend)) {
            memcpy(backend, header, (size_t)(end - header));
            backend[end - header] = '\0';
        }
    }

    s->total += 1;
    s->sum_ms += latency_ms;
    if (s->total == 1 || latency_ms < s->min_ms)
        s->min_ms = latency_ms;
    if (latency_ms > s->max_ms)
        s->max_ms = latency_ms;

    fprintf(output, "%d,%s,%.3f,%d\n", request_id, backend, latency_ms, status);
    if (status == 200)
        s->ok += 1;
    return status == 200;
}

void stats_print(const Stats *s, const char *path)
{
    printf("Requests: %d, successful: %d, failed: %d\n",
           s->total, s->ok, s->total - s->ok);
    if (s->total > 0)
        printf("Latency ms: min=%.3f avg=%.3f max=%.3f\n",
               s->min_ms, s->sum_ms / (double)s->total, s->max_ms);
    printf("Saved to %s\n", path);
}
