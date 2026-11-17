/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_STORE_H
#define PF_STORE_H
#include <stddef.h>
/* Private, pre-opened directory fd. Never accepts destination paths from a manifest.
 * Initial install or explicit update (private, serialized caller). 0 success, -1 failure,
 * -2 wrong install/update state, -3 activation durability uncertain; inspect before retry.
 */
int pf_install_initial(int rootfd,const unsigned char *archive,size_t archive_n,const char *archive_sha,
 const unsigned char *manifest,size_t manifest_n,const char *manifest_sha);
/* Update retains previously preserved paths even when omitted; policy demotion is rejected. */
int pf_update(int rootfd,const unsigned char *archive,size_t archive_n,const char *archive_sha,
 const unsigned char *manifest,size_t manifest_n,const char *manifest_sha);
int pf_install_update(int rootfd,const unsigned char *archive,size_t archive_n,const char *archive_sha,
 const unsigned char *manifest,size_t manifest_n,const char *manifest_sha);
/* Verified backup of an active generation; out contains a 64-char snapshot ID. */
int pf_backup(int rootfd,const char *id,char out[65]);
int pf_backup_verify(int rootfd,const char *id,const char *snapshot);
#endif
