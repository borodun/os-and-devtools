#ifndef LAB_UTILS_H
#define LAB_UTILS_H

const char *cfg_string(const char *name, const char *fallback);
int cfg_int(const char *name, int fallback, int min_value, int max_value);

#endif
