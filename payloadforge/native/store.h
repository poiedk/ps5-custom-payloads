/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_STORE_H
#define PF_STORE_H
#include <stddef.h>
/* Private, pre-opened directory fd. Never accepts destination paths from a manifest.
 * Initial-install-only native transaction. 0 success, -1 failure,
 * -2 package already active, -3 activation durability uncertain; inspect before retry.
 */
int pf_install_initial(int rootfd,const unsigned char *archive,size_t archive_n,const char *archive_sha,
 const unsigned char *manifest,size_t manifest_n,const char *manifest_sha);
#endif
