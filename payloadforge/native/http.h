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
/* Separate mutation protocol; deliberately NOT connected to read-only TCP
 * transport. POST, empty body, exact Origin, token and explicit confirmation.
 * Only managed operations; no shell, arbitrary paths or payload execution. */
enum { PF_CTL_BACKUP=1,PF_CTL_ROLLBACK=2,PF_CTL_UNINSTALL=3,PF_CTL_QUARANTINE=4 };
typedef struct {
 unsigned action,keep,marker,kind;
 char id[49],snapshot[65],current[65],object_hash[65];
} pf_http_control;
int pf_http_control_parse(const unsigned char *raw,size_t n,unsigned port,const char *token,pf_http_control *out);
/* Internal trusted caller only. Caller must serialize and quiesce the app.
 * The network runtime must NOT use this dispatcher until separately enabled.
 * Requires cap >= PF_HTTP_MAX_BODY before any mutation. */
int pf_http_control_dispatch(int rootfd,const pf_http_control *req,char *body,size_t cap);
#endif
