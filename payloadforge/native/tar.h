/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_TAR_H
#define PF_TAR_H
#include "zip.h"
#define PF_TAR_LIMIT (PF_ZIP_MAX_TOTAL+8u*1024u*1024u)
/* Unified read-only ZIP/USTAR.GZ reader. Zero-initialize owned and expanded.
 * For TAR, expanded owns the data buffer and owned owns individual names.
 * For ZIP, expanded stays NULL and owned owns expanded ZIP entries.
 * Release both on success; failure releases all allocated memory. */
int pf_archive_scan(const unsigned char *raw,size_t n,pf_zip_entry *out,
 unsigned char **owned,unsigned char **expanded,size_t capacity,size_t *count);
void pf_archive_release(unsigned char **owned,unsigned char **expanded,size_t capacity);
#endif
