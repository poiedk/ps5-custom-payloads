/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_CONSTRAINTS_H
#define PF_CONSTRAINTS_H
#include <stddef.h>
#define PF_STATE_MAX 256u
#define PF_DEP_MAX 64u
#define PF_RESOURCE_MAX 128u
typedef struct { char id[49], constraint[129]; } pf_dep;
typedef struct { unsigned kind,port; char path[513]; } pf_resource;
enum { PF_TCP=1,PF_UDP=2,PF_PATH=3 };
typedef struct {
 char id[49],version[65];
 const pf_dep *dependencies,*conflicts;
 size_t dependency_count,conflict_count;
 const pf_resource *resources;
 size_t resource_count;
} pf_package_state;
/* 1 match, 0 no match, -1 malformed constraint/version. */
int pf_constraint_match(const char *version,const char *constraint);
/* Validate a complete proposed state, including reverse dependencies.
 * 0 valid, -1 malformed, -2 dependency missing/incompatible,
 * -3 cycle, -4 conflict. No filesystem access or execution. */
int pf_state_validate(const pf_package_state *state,size_t count);
#endif
