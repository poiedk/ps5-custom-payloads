/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_INFLATE_H
#define PF_INFLATE_H
#include <stddef.h>
/* Read-only exact raw DEFLATE expansion. Success owns *out; free it after use.
 * Failure leaves *out NULL. Never opens files. No concatenated streams. */
int pf_inflate_exact(const unsigned char *compressed,size_t compressed_n,size_t expected,unsigned char **out);
void pf_inflate_free(void *out);
#endif
