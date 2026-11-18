/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "tar.h"
#include "core.h"
#include "inflate.h"
#include <stdlib.h>
#include <string.h>
static int zeros(const unsigned char *p,size_t n){
 for(size_t i=0;i<n;i++)if(p[i])return 0;
 return 1;
}
static int octal(const unsigned char *p,size_t n,size_t limit,size_t *value){
 size_t v=0,i=0,digits=0;
 while(i<n&&p[i]==' ')i++;
 while(i<n&&p[i]>='0'&&p[i]<='7'){
  size_t d=p[i++]-'0';
  if(d>limit||v>(limit-d)/8)return 0;
  v=v*8+d;digits++;
 }
 if(!digits||i==n)return 0;
 for(;i<n;i++)if(p[i]&&p[i]!=' ')return 0;
 *value=v;return 1;
}
static size_t field(const unsigned char *p,size_t n){
 size_t i=0;while(i<n&&p[i])i++;
 if(i<n&&!zeros(p+i,n-i))return n+1;
 return i;
}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int overlap(const pf_zip_entry *a,const pf_zip_entry *b){
 size_t n=a->name_len<b->name_len?a->name_len:b->name_len;
 for(size_t i=0;i<n;i++)if(fold(a->name[i])!=fold(b->name[i]))return 0;
 return a->name_len==b->name_len||(a->name_len>n?a->name[n]:b->name[n])=='/';
}
static int scan_tar(const unsigned char *b,size_t n,pf_zip_entry *out,unsigned char **owned,size_t cap,size_t *count){
 size_t pos=0,m=0,total=0;
 if(n<1024||n%512)return -1;
 while(pos<=n-512){
  const unsigned char *h=b+pos;
  if(zeros(h,512)){
   if(n-pos<1024||!zeros(h,n-pos)||!m)return -1;
   *count=m;return 0;
  }
  if(m>=cap||memcmp(h+257,"ustar\0",6)||memcmp(h+263,"00",2)||
     (h[156]!='0'&&h[156]!=0)||!zeros(h+157,100))return -1;
  size_t sum=0,check=0,size=0;
  for(size_t i=0;i<512;i++)sum+=(i>=148&&i<156)?32u:h[i];
  if(!octal(h+148,8,512u*255u,&check)||sum!=check||
     !octal(h+124,12,PF_ZIP_MAX_MEMBER,&size)||size>PF_ZIP_MAX_TOTAL-total)return -1;
  size_t a=field(h,100),p=field(h+345,155);
  if(!a||a>100||p>155)return -1;
  size_t len=a+(p?p+1:0);
  unsigned char *name=malloc(len+1);
  if(!name)return -1;
  owned[m]=name;
  if(p){memcpy(name,h+345,p);name[p]='/';}
  memcpy(name+(p?p+1:0),h,a);name[len]=0;
  if(!pf_path_valid((const char *)name,len))return -1;
  for(size_t i=0;i<len;i++)if(name[i]>=127)return -1;
  size_t start=pos+512,padded=(size+511u)&~(size_t)511u;
  if(padded>n-start||!zeros(b+start+size,padded-size))return -1;
  pf_zip_entry e={name,b+start,len,size};
  for(size_t i=0;i<m;i++)if(overlap(out+i,&e))return -1;
  out[m++]=e;total+=size;pos=start+padded;
 }
 return -1;
}
void pf_archive_release(unsigned char **owned,unsigned char **expanded,size_t cap){
 pf_zip_release(owned,cap);
 if(expanded){pf_inflate_free(*expanded);*expanded=NULL;}
}
int pf_archive_scan(const unsigned char *raw,size_t n,pf_zip_entry *out,unsigned char **owned,unsigned char **expanded,size_t cap,size_t *count){
 if(!count)return -1;
 *count=0;
 if(!raw||!n||n>PF_ZIP_MAX_ARCHIVE||!out||!owned||!expanded||*expanded||!cap||cap>PF_ZIP_MAX_MEMBERS)return -1;
 for(size_t i=0;i<cap;i++)if(owned[i])return -1;
 if(pf_format_detect(raw,n)==PF_ZIP)return pf_zip_scan_owned(raw,n,out,owned,cap,count);
 if(pf_format_detect(raw,n)!=PF_GZIP)return -1;
 size_t size=0;
 if(pf_gzip_expand(raw,n,expanded,&size))return -1;
 if(scan_tar(*expanded,size,out,owned,cap,count)){
  pf_archive_release(owned,expanded,cap);*count=0;return -1;
 }
 return 0;
}
