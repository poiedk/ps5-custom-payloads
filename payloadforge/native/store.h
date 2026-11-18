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
/* Snapshot is a verified independent copy. Caller serializes threads and quiesces app. */
int pf_backup(int rootfd,const char *id,char snapshot[65]);
int pf_backup_verify(int rootfd,const char *id,const char *snapshot);
int pf_rollback(int rootfd,const char *id,const char *snapshot);
/* 0 deactivated/removed; 1 deactivated with incomplete cleanup; -2 not active.
 * -3 means pointer durability uncertain, and no cleanup is performed. */
int pf_uninstall(int rootfd,const char *id,int keep_config,size_t *removed);
int pf_install_upgrade(int rootfd,const unsigned char *archive,size_t archive_n,const char *archive_sha,
 const unsigned char *manifest,size_t manifest_n,const char *manifest_sha);
int pf_install_downgrade(int rootfd,const unsigned char *archive,size_t archive_n,const char *archive_sha,
 const unsigned char *manifest,size_t manifest_n,const char *manifest_sha);
/* Status: 1 active, 0 absent/uninstalled, -1 invalid state. */
int pf_status(int rootfd,const char *id,char version[65],char generation[65]);
/* Read-only recovery report. No generation is chosen or deleted. Marker:
 * 0 absent, 1 active, 2 uninstalled/drop, 3 uninstalled/keep, 4 invalid.
 * integrity: 0 not applicable, 1 verified managed bytes (mutable config
 * may differ), 2 damaged/missing. Counts do not authenticate inactive data.
 * Return -1 if inspection itself is unsafe or incomplete. */
typedef struct {
 unsigned marker,integrity;
 size_t changed_configs,staged_generations,staged_backups,pending_markers,
        inactive_generations,backups,unexpected_entries;
 char current[65];
} pf_recovery;
int pf_recovery_inspect(int rootfd,const char *id,pf_recovery *report);
/* Explicit, non-destructive retry preparation. The caller selects a single
 * remnant and supplies the last inspected CURRENT marker and ID. An absent
 * marker requires an empty expected_current. Never moves CURRENT or a live
 * generation, never promotes inactive data, and never deletes a remnant.
 * Quarantine is outside apps; no overwrite. 0 moved, -1 refused, -3 rename
 * succeeded but durability uncertain. Inspect again before retrying.
 */
enum { PF_REC_STAGE_GENERATION=1, PF_REC_STAGE_BACKUP=2,
 PF_REC_PENDING_ACTIVATION=3, PF_REC_PENDING_UNINSTALL=4,
 PF_REC_INACTIVE_GENERATION=5 };
int pf_recovery_quarantine(int rootfd,const char *id,unsigned expected_marker,
 const char *expected_current,unsigned kind,const char *object_hash);
#endif
