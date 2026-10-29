#ifndef LAB_STATS_H
#define LAB_STATS_H

#include <stdio.h>

typedef struct {
    int total;
    int ok;
    double min_ms;
    double max_ms;
    double sum_ms;
} Stats;

void stats_init(Stats *s);
void stats_header(FILE *output);
int stats_record(Stats *s, FILE *output, int request_id,
                 const char *response, double latency_ms);
void stats_print(const Stats *s, const char *path);

#endif
