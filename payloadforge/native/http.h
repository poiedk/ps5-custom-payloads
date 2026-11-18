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
/* Bounded binary upload (PFU1): magic, big-endian manifest+archive lengths,
 * 64 ASCII hex manifest SHA256, 64 ASCII hex archive SHA256, manifest, archive.
 * These are caller-supplied integrity checks, NOT signatures or provenance.
 * No upload is exposed by the existing network runtime. */
#define PF_UPLOAD_MAX (12u*1024u*1024u)
#define PF_UPLOAD_PREFIX 140u
enum { PF_UPLOAD_VERIFY=1,PF_UPLOAD_INSTALL=2,PF_UPLOAD_UPGRADE=3,PF_UPLOAD_DOWNGRADE=4 };
typedef struct {
 unsigned action;
 const unsigned char *manifest,*archive;
 size_t manifest_n,archive_n;
 char manifest_sha[65],archive_sha[65];
} pf_http_upload;
/* Authenticate a complete header BEFORE reading or allocating the body. */
int pf_http_upload_head(const unsigned char *raw,size_t n,unsigned port,const char *token,unsigned *action,size_t *body_n);
/* Complete request; body pointers borrow the immutable caller buffer. */
int pf_http_upload_parse(const unsigned char *raw,size_t n,unsigned port,const char *token,pf_http_upload *out);
/* Internal trusted caller, serialized/quiesced store. Verify is read-only
 * and NOT a dependency/state plan; apply revalidates in the store engine. */
int pf_http_upload_dispatch(int rootfd,const pf_http_upload *req,char *body,size_t cap);
/* Fixed public UI assets only. No token/state or filesystem access. */
int pf_http_ui_route(const unsigned char *raw,size_t n,unsigned port,const char *token,unsigned *asset);
#endif
