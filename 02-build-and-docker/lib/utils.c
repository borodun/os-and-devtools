#include "utils.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

const char *cfg_string(const char *name, const char *fallback)
{
    const char *value = getenv(name);
    return value && *value ? value : fallback;
}

int cfg_int(const char *name, int fallback, int min_value, int max_value)
{
    const char *value = getenv(name);
    if (!value || !*value)
        return fallback;

    errno = 0;
    char *end;
    long n = strtol(value, &end, 10);
    if (errno || *end || end == value || n < min_value || n > max_value) {
        fprintf(stderr, "Invalid %s: %s (expected %d..%d)\n",
                name, value, min_value, max_value);
        exit(EXIT_FAILURE);
    }
    return (int)n;
}
