/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE 1
#include "transport.h"
#include "http.h"
#ifdef PF_ENABLE_UI
#include "ui_assets.h"
#endif
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

static int nonblock(int fd){
 int flags=fcntl(fd,F_GETFL);
 if(flags<0||fcntl(fd,F_SETFL,flags|O_NONBLOCK)<0)return -1;
 flags=fcntl(fd,F_GETFD);
 return flags<0||fcntl(fd,F_SETFD,flags|FD_CLOEXEC)<0?-1:0;
}
static int64_t millis(void){
 struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))return -1;
 return (int64_t)t.tv_sec*1000+t.tv_nsec/1000000;
}
static int wait_fd(int fd,short event,int64_t deadline){
 for(;;){
  int64_t now=millis();if(now<0)return -1;
  if(now>=deadline)return 0;
  struct pollfd p={.fd=fd,.events=event};
  int n=poll(&p,1,(int)(deadline-now));
  if(n<0&&errno==EINTR)continue;
  if(n<=0)return n;
  if(p.revents&event)return 1;
  return -1;
 }
}
static int local_addr(const struct sockaddr_in *a,socklen_t n){
 return n>=sizeof(*a)&&a->sin_family==AF_INET&&a->sin_addr.s_addr==htonl(UINT32_C(0x7f000001));
}
static int listener_port(int fd,unsigned *out){
 struct sockaddr_in actual={0};socklen_t len=sizeof actual;
 if(getsockname(fd,(struct sockaddr *)&actual,&len)||!local_addr(&actual,len))return -1;
 *out=ntohs(actual.sin_port);return *out?0:-1;
}
int pf_http_listen(unsigned port,unsigned *bound_port){
 if(!bound_port)return -1;
 *bound_port=0;if(port>65535)return -1;
 int fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)return -1;
 struct sockaddr_in address={0};address.sin_family=AF_INET;
 #ifdef __FreeBSD__
 address.sin_len=sizeof address;
#endif
 address.sin_port=htons((uint16_t)port);address.sin_addr.s_addr=htonl(UINT32_C(0x7f000001));
 if(nonblock(fd)||bind(fd,(struct sockaddr *)&address,sizeof address)||listen(fd,4)||listener_port(fd,bound_port)){
  close(fd);*bound_port=0;return -1;
 }
 return fd;
}
static int sent(int fd,const char *s,size_t n,int64_t deadline){
 while(n){
  if(wait_fd(fd,POLLOUT,deadline)!=1)return -1;
#ifdef MSG_NOSIGNAL
  ssize_t k=send(fd,s,n,MSG_NOSIGNAL);
#else
  ssize_t k=send(fd,s,n,0);
#endif
  if(k<0&&(errno==EINTR||errno==EAGAIN||errno==EWOULDBLOCK))continue;
  if(k<=0)return -1;
  s+=k;n-=(size_t)k;
 }
 return 0;
}
static const char *reason(int code){
 switch(code){
 case 200:return "OK";case 400:return "Bad Request";case 401:return "Unauthorized";
 case 403:return "Forbidden";case 404:return "Not Found";case 405:return "Method Not Allowed";
 case 409:return "Conflict";case 431:return "Request Header Fields Too Large";default:return "Internal Server Error";
 }
}
static int response(int fd,int code,const char *body,int64_t deadline){
 char head[768];
 int n=snprintf(head,sizeof head,"HTTP/1.1 %d %s\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: %zu\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\nContent-Security-Policy: default-src 'none'; frame-ancestors 'none'\r\n\r\n",code,reason(code),strlen(body));
 if(n<0||(size_t)n>=sizeof head||sent(fd,head,(size_t)n,deadline)||sent(fd,body,strlen(body),deadline))return -1;
 return 1;
}
#ifdef PF_ENABLE_UI
/* Fixed-purpose local read-only probe of the documented PLDMGR /version.
 * No arbitrary URL, forwarding of credentials, redirects or mutations.
 * An answer identifies an HTTP response, not a cryptographic peer identity. */
#if defined(PF_TEST_PLDMGR_PORT) && defined(PF_PS5_BUILD)
#error test-only port override is forbidden in PS5 builds
#endif
#ifndef PF_TEST_PLDMGR_PORT
#define PF_TEST_PLDMGR_PORT 8084
#endif
static int probe_ieq(const unsigned char *p,size_t n,const char *s){
 if(n!=strlen(s))return 0;
 for(size_t i=0;i<n;i++){unsigned char ch=p[i];if(ch>='A'&&ch<='Z')ch=(unsigned char)(ch+32);if(ch!=(unsigned char)s[i])return 0;}
 return 1;
}
static size_t probe_eol(const unsigned char *p,size_t n){
 for(size_t i=0;i+1<n;i++)if(p[i]=='\r'&&p[i+1]=='\n')return i;
 return n;
}
/* 0 incomplete, -1 refused, 1 syntactically valid three-part version. */
static int probe_parse(const unsigned char *raw,size_t n,char version[32]){
 size_t end=0;
 for(size_t i=0;i+3<n;i++)if(!memcmp(raw+i,"\r\n\r\n",4)){end=i+4;break;}
 if(!end)return n>=4096?-1:0;
 size_t line=probe_eol(raw,end);
 if(line!=15||(memcmp(raw,"HTTP/1.1 200 OK",15)&&memcmp(raw,"HTTP/1.0 200 OK",15)))return -1;
 size_t pos=line+2,body_n=0;unsigned seen=0;
 while(pos+2<end){
  line=probe_eol(raw+pos,end-pos);
  if(!line||line==end-pos||line>1024)return -1;
  const unsigned char *p=raw+pos;
  size_t colon=0;while(colon<line&&p[colon]!=':')colon++;
  if(!colon||colon==line)return -1;
  for(size_t i=0;i<line;i++)if(p[i]<32||p[i]>=127)return -1;
  for(size_t i=0;i<colon;i++)if(!((p[i]>='A'&&p[i]<='Z')||(p[i]>='a'&&p[i]<='z')||(p[i]>='0'&&p[i]<='9')||p[i]=='-'))return -1;
  size_t a=colon+1,b=line;while(a<b&&p[a]==' ')a++;while(b>a&&p[b-1]==' ')b--;
  unsigned bit=0;
  if(probe_ieq(p,colon,"content-length")){
   bit=1;if(a==b||b-a>2)return -1;
   for(size_t i=a;i<b;i++){if(p[i]<'0'||p[i]>'9')return -1;body_n=body_n*10+(size_t)(p[i]-'0');}
   if(!body_n||body_n>=32)return -1;
  }else if(probe_ieq(p,colon,"content-type")){
   bit=2;if(!probe_ieq(p+a,b-a,"text/plain")&&!probe_ieq(p+a,b-a,"text/plain; charset=utf-8"))return -1;
  }else if(probe_ieq(p,colon,"transfer-encoding")||probe_ieq(p,colon,"content-encoding"))return -1;
  if(bit&&(seen&bit))return -1;
  seen|=bit;pos+=line+2;
 }
 if(pos+2!=end||seen!=3)return -1;
 if(n-end<body_n)return 0;
 if(n-end!=body_n)return -1;
 unsigned dots=0,digits=0;
 for(size_t i=0;i<body_n;i++){
  unsigned ch=raw[end+i];
  if(ch=='.'){if(!digits||++dots>2)return -1;digits=0;}
  else if(ch<'0'||ch>'9'||++digits>5)return -1;
 }
 if(dots!=2||!digits)return -1;
 memcpy(version,raw+end,body_n);version[body_n]=0;return 1;
}
static int probe_version(char version[32],int64_t deadline){
 int64_t now=millis();if(now<0||now>=deadline)return 0;
 if(deadline-now>1200)deadline=now+1200;
 int fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)return 0;int ok=0;
 struct sockaddr_in remote={0};remote.sin_family=AF_INET;
#ifdef __FreeBSD__
 remote.sin_len=sizeof remote;
#endif
 remote.sin_addr.s_addr=htonl(UINT32_C(0x7f000001));remote.sin_port=htons(PF_TEST_PLDMGR_PORT);
 if(nonblock(fd))goto done;
#ifndef MSG_NOSIGNAL
#ifdef SO_NOSIGPIPE
 int one=1;if(setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof one))goto done;
#else
 goto done;
#endif
#endif
 int rc=connect(fd,(struct sockaddr *)&remote,sizeof remote);
 if(rc<0){
  if(errno!=EINPROGRESS&&errno!=EWOULDBLOCK)goto done;
  if(wait_fd(fd,POLLOUT,deadline)!=1)goto done;
  int error=0;socklen_t len=sizeof error;
  if(getsockopt(fd,SOL_SOCKET,SO_ERROR,&error,&len)||error)goto done;
 }
 char request[160];
 int count=snprintf(request,sizeof request,"GET /version HTTP/1.1\r\nHost: 127.0.0.1:%u\r\nConnection: close\r\nAccept: text/plain\r\n\r\n",(unsigned)PF_TEST_PLDMGR_PORT);
 if(count<=0||(size_t)count>=sizeof request||sent(fd,request,(size_t)count,deadline))goto done;
 unsigned char bytes[4096];size_t used=0;
 while(used<sizeof bytes){
  if(wait_fd(fd,POLLIN,deadline)!=1)break;
  ssize_t got=recv(fd,bytes+used,sizeof bytes-used,0);
  if(got<0&&(errno==EINTR||errno==EAGAIN||errno==EWOULDBLOCK))continue;
  if(got<=0)break;
  used+=(size_t)got;int parsed=probe_parse(bytes,used,version);
  if(parsed){ok=parsed==1;break;}
 }
 done:close(fd);return ok;
}
static int probe_response(int fd,int64_t deadline){
 char version[32]={0},body[256];
 int reachable=probe_version(version,deadline);
 int n=snprintf(body,sizeof body,"{\"reachable\":%s,\"reported_version\":\"%s\",\"identity_verified\":false,\"read_only\":true}",reachable?"true":"false",reachable?version:"");
 int64_t now=millis();if(n<0||(size_t)n>=sizeof body||now<0)return -1;
 return response(fd,200,body,now+1000);
}
static int asset_response(int fd,unsigned asset,int64_t deadline){
 const char *mime=NULL;const unsigned char *bytes=NULL;size_t length=0;
 switch(asset){
 case 1:mime="text/html; charset=utf-8";bytes=pf_ui_html;length=sizeof pf_ui_html-1;break;
 case 2:mime="text/css; charset=utf-8";bytes=pf_ui_css;length=sizeof pf_ui_css-1;break;
 case 3:mime="application/javascript; charset=utf-8";bytes=pf_ui_js;length=sizeof pf_ui_js-1;break;
 case 4:mime="application/json; charset=utf-8";bytes=pf_ui_catalog;length=sizeof pf_ui_catalog-1;break;
 default:return -1;
 }
 char head[1024];
 int n=snprintf(head,sizeof head,"HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %zu\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nReferrer-Policy: same-origin\r\nX-Frame-Options: DENY\r\nContent-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'\r\n\r\n",mime,length);
 if(n<0||(size_t)n>=sizeof head||sent(fd,head,(size_t)n,deadline)||sent(fd,(const char *)bytes,length,deadline))return -1;
 return 1;
}
#endif
static size_t complete(const unsigned char *p,size_t n,size_t start){
 for(size_t i=start;i+3<n;i++)if(!memcmp(p+i,"\r\n\r\n",4))return i+4;
 return 0;
}
#ifdef PF_ENABLE_MANAGED
/* This path is not compiled into the read-only transport by default. */
static int managed_post(int fd,int root,const unsigned char *head,size_t used,size_t hn,unsigned port,const char *token,int64_t deadline){
 char body[PF_HTTP_MAX_BODY]={0};int code;
 if(hn>=17&&!memcmp(head,"POST /api/upload/",17)){
  unsigned action=0;size_t length=0;
  code=pf_http_upload_head(head,hn,port,token,&action,&length);
  if(code!=200)goto send_error;
  if(used-hn>length){code=400;goto send_error;}
  size_t total=hn+length;
  unsigned char *raw=malloc(total);
  if(!raw){code=500;goto send_error;}
  memcpy(raw,head,used);
  while(used<total){
   if(wait_fd(fd,POLLIN,deadline)!=1){free(raw);return -1;}
   ssize_t got=recv(fd,raw+used,total-used,0);
   if(got<0&&(errno==EINTR||errno==EAGAIN||errno==EWOULDBLOCK))continue;
   if(got<=0){free(raw);return -1;}
   used+=(size_t)got;
  }
  pf_http_upload request;
  code=pf_http_upload_parse(raw,total,port,token,&request);
  if(code==200)code=pf_http_upload_dispatch(root,&request,body,sizeof body);
  free(raw);
 }else{
  pf_http_control request;
  code=pf_http_control_parse(head,used,port,token,&request);
  if(code==200)code=pf_http_control_dispatch(root,&request,body,sizeof body);
 }
 /* Store transaction is not interrupted by socket timeout. Send a bounded
  * response when possible, even if the original request window elapsed. */
 if(code==200||code==409){
  int64_t now=millis();
  return now<0?-1:response(fd,code,body,now+2000);
 }
 send_error:return response(fd,code,"{\"error\":\"request rejected\"}",deadline);
}
#endif
static int serve(int listener,int root,const char *token,unsigned timeout_ms,int managed){
#ifndef PF_ENABLE_MANAGED
 (void)managed;
#endif
 unsigned port;
 if(!timeout_ms||timeout_ms>10000||listener_port(listener,&port)||nonblock(listener))return -1;
 int64_t now=millis();if(now<0)return -1;int64_t deadline=now+timeout_ms;
 int fd=-1;
 for(;;){
  int ready=wait_fd(listener,POLLIN,deadline);if(ready!=1)return ready;
  struct sockaddr_in peer={0};socklen_t len=sizeof peer;
  fd=accept(listener,(struct sockaddr *)&peer,&len);
  if(fd<0&&(errno==EINTR||errno==EAGAIN||errno==EWOULDBLOCK))continue;
  if(fd<0)return -1;
  if(!local_addr(&peer,len)||nonblock(fd)){close(fd);return -1;}
  break;
 }
#ifndef MSG_NOSIGNAL
#ifdef SO_NOSIGPIPE
 int one=1;if(setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&one,sizeof one)){close(fd);return -1;}
#else
 close(fd);return -1; /* Never risk killing the process on broken pipe. */
#endif
#endif
 unsigned char head[PF_HTTP_MAX_HEAD];size_t used=0;
 char body[PF_HTTP_MAX_BODY];int rc=-1,code=431;
 while(used<sizeof head){
  if(wait_fd(fd,POLLIN,deadline)!=1)goto end;
  ssize_t got=recv(fd,head+used,sizeof head-used,0);
  if(got<0&&(errno==EINTR||errno==EAGAIN||errno==EWOULDBLOCK))continue;
  if(got<=0)goto end;
  size_t scan=used>3?used-3:0;used+=(size_t)got;
  size_t hn=complete(head,used,scan);
  if(hn){
#ifdef PF_ENABLE_MANAGED
   if(managed&&used>=5&&!memcmp(head,"POST ",5)){rc=managed_post(fd,root,head,used,hn,port,token,deadline);goto end;}
#endif
#ifdef PF_ENABLE_UI
   if(managed){
    unsigned asset=0;
    code=pf_http_ui_route(head,used,port,token,&asset);
    if(code==200){rc=asset==5?probe_response(fd,deadline):asset_response(fd,asset,deadline);goto end;}
    if(code!=404){rc=response(fd,code,"{\"error\":\"request rejected\"}",deadline);goto end;}
   }
#endif
   pf_http_request request;
   code=pf_http_parse(head,used,port,token,&request);
   if(code==200){
    code=pf_http_dispatch(root,&request,body,sizeof body);
#ifdef PF_ENABLE_MANAGED
    if(managed&&code==200&&request.route==PF_HTTP_HEALTH)
     snprintf(body,sizeof body,"{\"mode\":\"native-managed-development\",\"mutation\":true,\"upload_max\":%u}",PF_UPLOAD_MAX);
#endif
    if(code==200||code==409){rc=response(fd,code,body,deadline);goto end;}
   }
   break;
  }
 }
 rc=response(fd,code,"{\"error\":\"request rejected\"}",deadline);
 end:close(fd);return rc;
}

int pf_http_serve_one(int listener,int root,const char *token,unsigned timeout_ms){return serve(listener,root,token,timeout_ms,0);}
#ifdef PF_ENABLE_MANAGED
int pf_http_serve_managed_one(int listener,int root,const char *token,unsigned timeout_ms){return serve(listener,root,token,timeout_ms,1);}
#endif
