/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_SHA256_H
#define PF_SHA256_H
#include <stddef.h>
#include <stdint.h>
typedef struct { uint32_t h[8]; uint64_t bytes; unsigned char block[64]; size_t used; } pf_sha256;
void pf_sha256_init(pf_sha256 *s);
void pf_sha256_update(pf_sha256 *s,const void *data,size_t n);
void pf_sha256_final(pf_sha256 *s,unsigned char out[32]);
void pf_sha256_hex(const void *data,size_t n,char out[65]);
int pf_sha256_matches(const void *data,size_t n,const char *hex);
#endif
