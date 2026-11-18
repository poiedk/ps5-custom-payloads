/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_MANIFEST_H
#define PF_MANIFEST_H
#include <stddef.h>
#include "constraints.h"
#define PF_PATH_LIMIT 1024u
#define PF_MANIFEST_LIMIT (2u*1024u*1024u)
typedef struct { char path[PF_PATH_LIMIT+1]; char sha256[65]; size_t size; int preserve; } pf_file;
typedef struct { char id[49],version[65]; size_t count,total; unsigned schema; } pf_manifest;
typedef struct {
 size_t dependency_count,conflict_count,resource_count;
 pf_dep dependencies[PF_DEP_MAX],conflicts[PF_DEP_MAX];
 pf_resource resources[PF_RESOURCE_MAX];
} pf_manifest_metadata;
/* Read-only extended parser. Successful parsing does not authorize installation. */
int pf_manifest_parse_metadata(const unsigned char *raw,size_t n,pf_manifest *out,pf_file *files,size_t capacity,pf_manifest_metadata *meta);
/* Native subset: ASCII strings, data-only files, empty dependency/conflict/resource arrays. */
int pf_manifest_parse(const unsigned char *raw,size_t n,pf_manifest *out,pf_file *files,size_t capacity);
int pf_bundle_verify(const unsigned char *archive,size_t archive_n,const char *archive_hash,
 const unsigned char *manifest,size_t manifest_n,const char *manifest_hash,pf_manifest *out,pf_file *files,size_t capacity);
#endif
