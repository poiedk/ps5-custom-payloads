/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "constraints.h"
#include "core.h"
#include "version.h"
#include <string.h>
#include <stdlib.h>
static size_t bounded(const char *s,size_t cap){
 size_t n=0;if(!s)return cap;while(n<cap&&s[n])n++;return n;
}
static int space(char c){return c==' '||c=='\t'||c=='\r'||c=='\n';}
static int constraint(const char *version,const char *s,int syntax_only){
 size_t n=bounded(s,129);
 if(!n||n>=129)return -1;
 if(n==1&&*s=='*')return 1;
 int result=1;
 const char *p=s;
 for(;;){
  while(space(*p))p++;
  char op=*p;if(op!='<'&&op!='>'&&op!='='&&op!='!')return -1;
  p++;
  int equal=*p=='=';if(equal)p++;
  if((op=='='||op=='!')&&!equal)return -1;
  while(space(*p))p++;
  const char *start=p;
  while(*p&&*p!=','&&!space(*p))p++;
  size_t len=(size_t)(p-start);
  if(!len||len>64)return -1;
  char target[65];memcpy(target,start,len);target[len]=0;
  int cmp;
  if(pf_version_compare(syntax_only?target:version,target,&cmp))return -1;
  int match=op=='='?cmp==0:op=='!'?cmp!=0:op=='<'?(cmp<0||(equal&&cmp==0)):(cmp>0||(equal&&cmp==0));
  if(!match)result=0;
  while(space(*p))p++;
  if(!*p)return result;
  if(*p++!=',')return -1;
 }
}
int pf_constraint_match(const char *version,const char *s){
 if(!version||bounded(version,65)>=65)return -1;
 return constraint(version,s,0);
}
static int index_of(const pf_package_state *s,size_t n,const char *id){
 for(size_t i=0;i<n;i++)if(!strcmp(s[i].id,id))return (int)i;
 return -1;
}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int path_overlap(const char *a,const char *b,int prefix){
 while(*a&&*b&&fold((unsigned char)*a)==fold((unsigned char)*b)){a++;b++;}
 return (!*a&&!*b)||(prefix&&((!*a&&*b=='/')||(!*b&&*a=='/')));
}
static int resource_match(const pf_resource *a,const pf_resource *b,int prefix){
 if(a->kind!=b->kind)return 0;
 return a->kind==PF_PATH?path_overlap(a->path,b->path,prefix):a->port==b->port;
}
static int check_deps(const pf_dep *d,size_t n){
 if(n>PF_DEP_MAX||(n&&!d))return -1;
 for(size_t i=0;i<n;i++){
  size_t len=bounded(d[i].id,sizeof d[i].id);
  if(len>=sizeof d[i].id||!pf_id_valid(d[i].id,len)||constraint(NULL,d[i].constraint,1)<0)return -1;
  for(size_t j=0;j<i;j++)if(!strcmp(d[i].id,d[j].id))return -1;
 }
 return 0;
}
int pf_state_validate(const pf_package_state *s,size_t n){
 if(n>PF_STATE_MAX||(n&&!s))return -1;
 size_t resource_total=0,dep_total=0;
 for(size_t i=0;i<n;i++){
  const pf_package_state *p=s+i;
  size_t idn=bounded(p->id,sizeof p->id),vn=bounded(p->version,sizeof p->version);
  if(!vn||vn>=sizeof p->version||idn>=sizeof p->id||!pf_id_valid(p->id,idn))return -1;
  for(size_t j=0;j<i;j++)if(!strcmp(p->id,s[j].id))return -1;
  if(check_deps(p->dependencies,p->dependency_count)||check_deps(p->conflicts,p->conflict_count))return -1;
  if(p->resource_count>PF_RESOURCE_MAX||(p->resource_count&&!p->resources))return -1;
  resource_total+=p->resource_count;dep_total+=p->dependency_count+p->conflict_count;
  if(resource_total>1024||dep_total>4096)return -1;
  for(size_t j=0;j<p->resource_count;j++){
   const pf_resource *r=p->resources+j;
   if(r->kind==PF_TCP||r->kind==PF_UDP){if(!r->port||r->port>65535)return -1;}
   else if(r->kind==PF_PATH){
    size_t len=bounded(r->path,sizeof r->path);
    if(len<=6||len>=sizeof r->path||strncmp(r->path,"/data/",6)||!pf_path_valid(r->path+1,len-1))return -1;
    for(size_t k=0;k<len;k++)if((unsigned char)r->path[k]>=127)return -1;
   }else return -1;
   for(size_t k=0;k<j;k++)if(resource_match(r,p->resources+k,0))return -1;
  }
 }
 unsigned char done[PF_STATE_MAX]={0};
 for(size_t i=0;i<n;i++){
  const pf_package_state *p=s+i;
  for(size_t j=0;j<p->dependency_count;j++){
   const pf_dep *d=p->dependencies+j;int k=index_of(s,n,d->id);
   if(k<0)return -2;
   int match=pf_constraint_match(s[k].version,d->constraint);
   if(match!=1)return match<0?-1:-2;
  }
  for(size_t j=0;j<p->conflict_count;j++){
   const pf_dep *d=p->conflicts+j;int k=index_of(s,n,d->id);
   if(k==(int)i)return -4;
   if(k>=0){int match=pf_constraint_match(s[k].version,d->constraint);if(match<0)return -1;if(match)return -4;}
  }
  for(size_t j=0;j<i;j++)for(size_t a=0;a<p->resource_count;a++)for(size_t b=0;b<s[j].resource_count;b++)
   if(resource_match(p->resources+a,s[j].resources+b,1))return -4;
 }
 size_t completed=0;
 while(completed<n){
  size_t before=completed;
  for(size_t i=0;i<n;i++)if(!done[i]){
   int ready=1;
   for(size_t j=0;j<s[i].dependency_count;j++){
    int k=index_of(s,n,s[i].dependencies[j].id);
    if(k<0||!done[k]){ready=0;break;}
   }
   if(ready){done[i]=1;completed++;}
  }
  if(before==completed)return -3;
 }
 return 0;
}
