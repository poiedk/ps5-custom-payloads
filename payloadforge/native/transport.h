/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef PF_TRANSPORT_H
#define PF_TRANSPORT_H
/* Explicit loopback-only listener; no automatic start. port=0 selects an OS
 * assigned port. Returns descriptor or -1. Caller closes the descriptor. */
int pf_http_listen(unsigned port,unsigned *bound_port);
/* Serve at most one connection with a finite total deadline. 1 response sent,
 * 0 idle timeout, -1 transport or deadline failure. No concurrent requests. */
int pf_http_serve_one(int listener,int rootfd,const char *token,unsigned timeout_ms);
#endif
