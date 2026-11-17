/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_ZIP_H
#define PF_ZIP_H
#include <stddef.h>
#include <stdint.h>
#define PF_ZIP_MAX_MEMBERS 2048u
#define PF_ZIP_MAX_ARCHIVE (128u*1024u*1024u)
#define PF_ZIP_MAX_MEMBER (64u*1024u*1024u)
#define PF_ZIP_MAX_TOTAL (256u*1024u*1024u)
typedef struct {
 const unsigned char *name,*data;
 size_t name_len,size;
} pf_zip_entry;
/* Strict ZIP_STORED subset. Read-only views of caller-owned bytes. */
int pf_zip_scan(const unsigned char *buf,size_t n,pf_zip_entry *out,size_t capacity,size_t *count);
#endif
