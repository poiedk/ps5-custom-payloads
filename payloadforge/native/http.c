/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "http.h"
#include "core.h"
#include "store.h"
#include <stdio.h>
#include <string.h>
#define LIT(s) (s), (sizeof(s)-1u)
static int eq(const unsigned char *v,size_t n,const char *s,size_t len){return n==len&&!memcmp(v,s,n);}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int ieq(const unsigned char *v,size_t n,const char *s,size_t len){
 if(n!=len)return 0;
 for(size_t i=0;i<n;i++)if(fold(v[i])!=(unsigned char)s[i])return 0;
 return 1;
}
static int hex_token(const char *token){
 if(!token||strlen(token)!=64)return 0;
 for(size_t i=0;i<64;i++)if(!((token[i]>='0'&&token[i]<='9')||(token[i]>='a'&&token[i]<='f')))return 0;
 return 1;
}
static int auth(const unsigned char *p,size_t n,const char *token){
 if(n!=71||memcmp(p,"Bearer ",7))return 0;
 unsigned diff=0;
 for(size_t i=0;i<64;i++)diff|=p[i+7]^(unsigned char)token[i];
 return diff==0;
}
static size_t eol(const unsigned char *p,size_t n){
 for(size_t i=0;i+1<n;i++)if(p[i]=='\r'&&p[i+1]=='\n')return i;
 return n;
}
static int name_char(unsigned c){
 return (c>='0'&&c<='9')||(fold(c)>='a'&&fold(c)<='z')||c=='-';
}
static int check_headers(const unsigned char *raw,size_t n,size_t first_end,unsigned port,const char *token,int mutation){
 char host[32],origin[40];int h=snprintf(host,sizeof host,"127.0.0.1:%u",port);
 int o=snprintf(origin,sizeof origin,"http://%s",host);
 if(h<=0||o<=0||(size_t)h>=sizeof host||(size_t)o>=sizeof origin)return 500;
 unsigned seen=0;int hostok=0,originok=1,authok=0,complete=0,confirmed=0;
 size_t pos=first_end+2,headers=0,line;
 while(pos<n){
  line=eol(raw+pos,n-pos);if(line==n-pos||line>1024)return 400;
  if(!line){pos+=2;complete=1;break;}
  if(++headers>48)return 431;
  const unsigned char *p=raw+pos;
  size_t colon=0;while(colon<line&&p[colon]!=':'){if(!name_char(p[colon]))return 400;colon++;}
  if(!colon||colon==line)return 400;
  size_t start=colon+1,stop=line;
  while(start<stop&&p[start]==' ')start++;
  while(stop>start&&p[stop-1]==' ')stop--;
  const unsigned char *v=p+start;size_t vn=stop-start;
  for(size_t i=0;i<line;i++)if(p[i]<32||p[i]>=127)return 400;
  unsigned bit=0;
  if(ieq(p,colon,LIT("host"))){bit=1;hostok=eq(v,vn,host,(size_t)h);}
  else if(ieq(p,colon,LIT("authorization"))){bit=2;authok=auth(v,vn,token);}
  else if(ieq(p,colon,LIT("origin"))){bit=4;originok=eq(v,vn,origin,(size_t)o);}
  else if(ieq(p,colon,LIT("x-payloadforge-confirm"))){bit=16;confirmed=eq(v,vn,LIT("yes"));}
  else if(ieq(p,colon,LIT("content-length"))){bit=8;if(!eq(v,vn,LIT("0")))return 400;}
  else if(ieq(p,colon,LIT("transfer-encoding"))||ieq(p,colon,LIT("upgrade"))||ieq(p,colon,LIT("expect"))||ieq(p,colon,LIT("proxy-authorization")))return 400;
  if(bit&&(seen&bit))return 400;
  seen|=bit;pos+=line+2;
 }
 if(!complete||pos!=n)return 400;
 if(!hostok||!originok)return 403;
 if(!authok)return 401;
 if(mutation&&(!(seen&4)||!(seen&8)||!confirmed))return 403;
 return 200;

}
int pf_http_parse(const unsigned char *raw,size_t n,unsigned port,const char *token,pf_http_request *out){
 if(!out)return 500;
 memset(out,0,sizeof(*out));
 if(!port||port>65535||!hex_token(token))return 500;
 if(!raw||!n)return 400;
 if(n>PF_HTTP_MAX_HEAD)return 431;
 for(size_t i=0;i<n;i++)if((raw[i]<32&&raw[i]!='\r'&&raw[i]!='\n')||raw[i]>=127)return 400;
 size_t line=eol(raw,n);if(line==n||line>512)return 400;
 if(line<4||memcmp(raw,"GET ",4))return 405;
 size_t end=4;while(end<line&&raw[end]!=' ')end++;
 if(end==line||(!eq(raw+end,line-end,LIT(" HTTP/1.1"))&&!eq(raw+end,line-end,LIT(" HTTP/1.0"))))return 400;
 pf_http_request request={0};const unsigned char *path=raw+4;size_t len=end-4,plen=0;
 if(eq(path,len,LIT("/api/health")))request.route=PF_HTTP_HEALTH;
 else if(len>15&&!memcmp(path,"/api/status?id=",15)){request.route=PF_HTTP_STATUS;plen=15;}
 else if(len>17&&!memcmp(path,"/api/recovery?id=",17)){request.route=PF_HTTP_RECOVERY;plen=17;}
 if(plen){
  if(!pf_id_valid((const char *)path+plen,len-plen))return 400;
  memcpy(request.id,path+plen,len-plen);
 }
 int status=check_headers(raw,n,line,port,token,0);if(status!=200)return status;
 if(!request.route)return 404;
 *out=request;return 200;
}
static int json_safe(const char *s){
 for(;*s;s++)if((unsigned char)*s<32||(unsigned char)*s>=127||*s=='"'||*s=='\\')return 0;
 return 1;
}
int pf_http_dispatch(int root,const pf_http_request *req,char *body,size_t cap){
 if(!body||!cap)return 500;
 body[0]=0;if(!req)return 500;
 int n=-1,status=200;
 if(req->route==PF_HTTP_HEALTH)n=snprintf(body,cap,"{\"mode\":\"native-read-only\",\"mutation\":false}");
 else if(req->route==PF_HTTP_STATUS||req->route==PF_HTTP_RECOVERY){
  if(!memchr(req->id,0,sizeof req->id)||!pf_id_valid(req->id,strlen(req->id)))return 400;
  pf_recovery p;
  if(pf_recovery_inspect(root,req->id,&p)){
   n=snprintf(body,cap,"{\"error\":\"inspection unavailable\"}");status=409;
  }else if(req->route==PF_HTTP_STATUS){
   /* Avoid pf_status: its current implementation creates a lock file. */
   n=snprintf(body,cap,"{\"id\":\"%s\",\"active\":%s,\"marker\":%u,\"integrity\":%u}",req->id,p.marker==1?"true":"false",p.marker,p.integrity);
  }else{
   if(!json_safe(p.current))return 500;
   n=snprintf(body,cap,"{\"id\":\"%s\",\"marker\":%u,\"integrity\":%u,\"current\":\"%s\",\"changed_configs\":%zu,\"staged_generations\":%zu,\"staged_backups\":%zu,\"pending_markers\":%zu,\"inactive_generations\":%zu,\"backups\":%zu,\"unexpected_entries\":%zu}",req->id,p.marker,p.integrity,p.current,p.changed_configs,p.staged_generations,p.staged_backups,p.pending_markers,p.inactive_generations,p.backups,p.unexpected_entries);
  }
 }else return 404;
 if(n<0||(size_t)n>=cap){body[0]=0;return 500;}
 return status;
}

static int arg(const unsigned char **p,size_t *n,const char *key,char *dst,size_t cap){
 size_t k=strlen(key);if(*n<k||memcmp(*p,key,k))return 0;
 *p+=k;*n-=k;
 size_t v=0;while(v<*n&&(*p)[v]!='&')v++;
 if(v>=cap)return 0;
 memcpy(dst,*p,v);dst[v]=0;*p+=v;*n-=v;return 1;
}
static int one_digit(const char *p,unsigned min,unsigned max,unsigned *out){
 if(p[0]<'0'||p[0]>'9'||p[1])return 0;
 unsigned x=(unsigned)(p[0]-'0');if(x<min||x>max)return 0;*out=x;return 1;
}
int pf_http_control_parse(const unsigned char *raw,size_t n,unsigned port,const char *token,pf_http_control *out){
 if(!out)return 500;
 memset(out,0,sizeof(*out));
 if(!port||port>65535||!hex_token(token))return 500;
 if(!raw||!n)return 400;
 if(n>PF_HTTP_MAX_HEAD)return 431;
 for(size_t i=0;i<n;i++)if((raw[i]<32&&raw[i]!='\r'&&raw[i]!='\n')||raw[i]>=127)return 400;
 size_t line=eol(raw,n);if(line==n||line>512)return 400;
 if(line<5||memcmp(raw,"POST ",5))return 405;
 size_t end=5;while(end<line&&raw[end]!=' ')end++;
 if(end==line||!eq(raw+end,line-end,LIT(" HTTP/1.1")))return 400;
 int status=check_headers(raw,n,line,port,token,1);if(status!=200)return status;
 const unsigned char *p=raw+5;size_t len=end-5,skip=0;
 pf_http_control q={0};
 const char *routes[]={"/api/control/backup?","/api/control/rollback?","/api/control/uninstall?","/api/control/quarantine?"};
 for(unsigned i=0;i<4;i++){
  size_t k=strlen(routes[i]);
  if(len>=k&&!memcmp(p,routes[i],k)){q.action=i+1;skip=k;break;}
 }
 if(!skip)return 404;
 p+=skip;len-=skip;
 if(!arg(&p,&len,"id=",q.id,sizeof q.id)||!pf_id_valid(q.id,strlen(q.id)))return 400;
 if(q.action==PF_CTL_ROLLBACK){
  if(!arg(&p,&len,"&snapshot=",q.snapshot,sizeof q.snapshot)||!hex_token(q.snapshot))return 400;
 }else if(q.action==PF_CTL_UNINSTALL){
  char mode[8];
  if(!arg(&p,&len,"&config=",mode,sizeof mode))return 400;
  if(!strcmp(mode,"keep"))q.keep=1;else if(strcmp(mode,"drop"))return 400;
 }else if(q.action==PF_CTL_QUARANTINE){
  char marker[2],kind[2];
  if(!arg(&p,&len,"&marker=",marker,sizeof marker)||!one_digit(marker,0,3,&q.marker)||
     !arg(&p,&len,"&current=",q.current,sizeof q.current)||
     (q.marker?!hex_token(q.current):q.current[0]!=0)||
     !arg(&p,&len,"&kind=",kind,sizeof kind)||!one_digit(kind,1,5,&q.kind)||
     !arg(&p,&len,"&object=",q.object_hash,sizeof q.object_hash)||!hex_token(q.object_hash))return 400;
 }
 if(len)return 400;
 *out=q;return 200;
}
int pf_http_control_dispatch(int root,const pf_http_control *q,char *body,size_t cap){
 if(!body||!cap)return 500;
 body[0]=0;
 if(cap<PF_HTTP_MAX_BODY||!q)return 500;
 if(!memchr(q->id,0,sizeof q->id)||!pf_id_valid(q->id,strlen(q->id)))return 400;
 char snapshot[65]={0};size_t removed=0;int rc;
 switch(q->action){
 case PF_CTL_BACKUP:rc=pf_backup(root,q->id,snapshot);break;
 case PF_CTL_ROLLBACK:
  if(!memchr(q->snapshot,0,sizeof q->snapshot)||!hex_token(q->snapshot))return 400;
  rc=pf_rollback(root,q->id,q->snapshot);break;
 case PF_CTL_UNINSTALL:
  if(q->keep>1)return 400;
  rc=pf_uninstall(root,q->id,(int)q->keep,&removed);break;
 case PF_CTL_QUARANTINE:
  if(q->marker>3||q->kind<1||q->kind>5||!memchr(q->current,0,sizeof q->current)||
     !memchr(q->object_hash,0,sizeof q->object_hash)||!hex_token(q->object_hash)||
     (q->marker?!hex_token(q->current):q->current[0]!=0))return 400;
  rc=pf_recovery_quarantine(root,q->id,q->marker,q->current,q->kind,q->object_hash);break;
 default:return 404;
 }
 int status=409,n;
 if(rc==0){
  status=200;
  n=snprintf(body,cap,"{\"ok\":true,\"result\":0,\"snapshot\":\"%s\",\"removed\":%zu}",snapshot,removed);
 }else if(q->action==PF_CTL_UNINSTALL&&rc==1){
  status=200;
  n=snprintf(body,cap,"{\"ok\":false,\"deactivated\":true,\"cleanup_incomplete\":true,\"removed\":%zu}",removed);
 }else if(rc==-3)n=snprintf(body,cap,"{\"ok\":false,\"inspect_before_retry\":true,\"result\":-3}");
 else n=snprintf(body,cap,"{\"ok\":false,\"inspect_before_retry\":true,\"result\":%d}",rc);
 if(n<0||(size_t)n>=cap){body[0]=0;return 500;}
 return status;
}
