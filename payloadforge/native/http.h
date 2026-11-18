/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_HTTP_H
#define PF_HTTP_H
#include <stddef.h>
#define PF_HTTP_MAX_HEAD 8192u
#define PF_HTTP_MAX_BODY 2048u
enum { PF_HTTP_HEALTH=1, PF_HTTP_STATUS=2, PF_HTTP_RECOVERY=3 };
typedef struct { unsigned route; char id[49]; } pf_http_request;
/* Parse one complete GET request (no body); authenticate all routes.
 * Return HTTP status. Expected token: exactly 64 lowercase hex digits. */
int pf_http_parse(const unsigned char *raw,size_t n,unsigned port,const char *token,pf_http_request *out);
/* Dispatch only authenticated, parsed requests; no network or mutation.
 * Caller supplies private rootfd and output buffer. Returns HTTP status. */
int pf_http_dispatch(int rootfd,const pf_http_request *request,char *body,size_t cap);
#endif
