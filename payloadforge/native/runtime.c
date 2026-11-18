/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Explicit read-only session. No arguments => no listener, no filesystem writes. */
#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE 1
#include "transport.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t stop;
static void stop_handler(int signo){(void)signo;stop=1;}
static void erase(void *p,size_t n){volatile unsigned char *q=p;while(n--)*q++=0;}
static int entropy(char token[65]){
 unsigned char raw[32]={0};size_t pos=0;int rc=-1;
 int fd=open("/dev/urandom",O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
 if(fd<0)return -1;
 while(pos<sizeof raw){
  ssize_t n=read(fd,raw+pos,sizeof raw-pos);
  if(n<0&&errno==EINTR)continue;
  if(n<=0)goto done;
  pos+=(size_t)n;
 }
 static const char hex[]="0123456789abcdef";
 for(size_t i=0;i<sizeof raw;i++){token[2*i]=hex[raw[i]>>4];token[2*i+1]=hex[raw[i]&15];}
 token[64]=0;rc=0;
 done:erase(raw,sizeof raw);close(fd);return rc;
}
static int parse_uint(const char *s,unsigned limit,unsigned *out){
 if(!s||!*s)return -1;
 unsigned n=0;
 for(;*s;s++){if(*s<'0'||*s>'9')return -1;unsigned d=(unsigned)(*s-'0');if(d>limit||n>(limit-d)/10)return -1;n=10*n+d;}
 *out=n;return 0;
}
static int open_private(const char *path){
 if(!path||path[0]!='/'||strlen(path)>1024||path[1]==0)return -1;
 /* Traverse exact caller-supplied path without following symlinks.
  * Ancestors need not be private; the final directory must be. */
 char copy[1025];memcpy(copy,path,strlen(path)+1);
 int fd=open("/",O_RDONLY|O_DIRECTORY|O_CLOEXEC);if(fd<0)return -1;
 char *p=copy+1;
 for(;;){
  char *slash=strchr(p,'/');if(slash)*slash=0;
  if(!*p||!strcmp(p,".")||!strcmp(p,"..")){close(fd);return -1;}
  int next=openat(fd,p,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
  close(fd);if(next<0)return -1;fd=next;
  if(!slash)break;
  p=slash+1;
 }
 struct stat st;
 if(fstat(fd,&st)||!S_ISDIR(st.st_mode)||st.st_uid!=geteuid()||(st.st_mode&0077)){close(fd);return -1;}
 return fd;
}
static int64_t milliseconds(void){
 struct timespec ts;
 if(clock_gettime(CLOCK_MONOTONIC,&ts))return -1;
 return (int64_t)ts.tv_sec*1000+ts.tv_nsec/1000000;
}
int main(int argc,char **argv){
 /* Separate runtime artifact, explicitly opt in. Never choose a default root. */
 unsigned port=0,seconds=0;
 if(argc!=8||strcmp(argv[1],"--serve-read-only")||strcmp(argv[2],"--root")||
    strcmp(argv[4],"--port")||strcmp(argv[6],"--seconds")||
    parse_uint(argv[5],65535,&port)||parse_uint(argv[7],300,&seconds)||!seconds){
  fputs("Usage: payloadforge-runtime --serve-read-only --root /private/path --port 0 --seconds 60\n",stderr);
  return 2;
 }
 int root=open_private(argv[3]);if(root<0){fputs("Private existing root required\n",stderr);return 1;}
 char token[65]={0};int listener=-1,rc=1;unsigned actual=0;
 if(entropy(token)){fputs("Secure entropy unavailable\n",stderr);goto done;}
 struct sigaction sa={0};sa.sa_handler=stop_handler;
 if(sigemptyset(&sa.sa_mask)||sigaction(SIGTERM,&sa,NULL)||sigaction(SIGINT,&sa,NULL))goto done;
 listener=pf_http_listen(port,&actual);
 if(listener<0){fputs("Loopback listener unavailable\n",stderr);goto done;}
 int64_t now=milliseconds();if(now<0)goto done;
 int64_t deadline=now+(int64_t)seconds*1000;
 /* Only local launcher stdout, never stored or served by HTTP. */
 if(printf("PayloadForge read-only runtime\nhttp://127.0.0.1:%u\nSession token: %s\n",actual,token)<0||fflush(stdout))goto done;
 rc=0;
 while(!stop){
  now=milliseconds();if(now<0){rc=1;break;}
  if(now>=deadline)break;
  unsigned left=(unsigned)(deadline-now);
  (void)pf_http_serve_one(listener,root,token,left>1000?1000:left);
 }
 done:if(listener>=0)close(listener);
 close(root);erase(token,sizeof token);return rc;
}
