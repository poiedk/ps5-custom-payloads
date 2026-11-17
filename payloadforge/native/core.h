#ifndef PAYLOADFORGE_CORE_H
#define PAYLOADFORGE_CORE_H
#include <stddef.h>
enum pf_format { PF_UNKNOWN, PF_ELF, PF_ZIP, PF_GZIP };
int pf_id_valid(const char *value, size_t n);
int pf_path_valid(const char *value, size_t n);
int pf_sha_valid(const char *value, size_t n);
enum pf_format pf_format_detect(const unsigned char *data, size_t n);
#endif
