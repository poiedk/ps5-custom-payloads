/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_VERSION_H
#define PF_VERSION_H
/* Numeric 1–3 component versions with optional v prefix and SemVer prerelease/build.
 * Returns 0 for recognized versions, -1 otherwise. Result -1, 0 or 1. */
int pf_version_compare(const char *left,const char *right,int *result);
#endif
