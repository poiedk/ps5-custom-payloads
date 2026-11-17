/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "zip.h"
#include "core.h"
#include <string.h>

static uint16_t u16(const unsigned char *p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static int fits(size_t off,size_t len,size_t end){return off<=end && len<=end-off;}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int conflict(const pf_zip_entry *a,const pf_zip_entry *b){
 size_t n=a->name_len<b->name_len?a->name_len:b->name_len;
 for(size_t i=0;i<n;i++)if(fold(a->name[i])!=fold(b->name[i]))return 0;
 return a->name_len==b->name_len||(a->name_len>n?a->name[n]:b->name[n])=='/';
}
static uint32_t crc32_bytes(const unsigned char *p,size_t n){
 uint32_t crc=0xffffffffu;
 for(size_t i=0;i<n;i++){crc^=p[i];for(unsigned j=0;j<8;j++)crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);}
 return ~crc;
}
int pf_zip_scan(const unsigned char *b,size_t n,pf_zip_entry *out,size_t cap,size_t *count){
 if(!count)return -1;
 *count=0;
 if(!b||!out||n<22||n>PF_ZIP_MAX_ARCHIVE)return -1;
 /* Deliberately reject comments, ZIP64, split archives and trailing data. */
 size_t end=n-22;
 const unsigned char *e=b+end;
 if(u32(e)!=0x06054b50u||u16(e+4)||u16(e+6)||u16(e+20))return -1;
 size_t m=u16(e+10),cd=u32(e+16),cs=u32(e+12);
 if(!m||m!=u16(e+8)||m>cap||m>PF_ZIP_MAX_MEMBERS||!fits(cd,cs,end)||cd+cs!=end)return -1;
 size_t pos=cd,local=0,total=0;
 for(size_t i=0;i<m;i++){
  if(!fits(pos,46,end))return -1;
  const unsigned char *c=b+pos;
  if(u32(c)!=0x02014b50u||u16(c+6)>20||u16(c+8)&~0x0800u||u16(c+10)||u16(c+34))return -1;
  size_t size=u32(c+24),compressed=u32(c+20),namelen=u16(c+28);
  size_t extra=u16(c+30),comment=u16(c+32);
  uint32_t crc=u32(c+16);
  unsigned mode=(u32(c+38)>>16)&0170000u;
  if(mode!=0&&mode!=0100000u)return -1;
  if(u32(c+38)&0x10u)return -1;
  if(size!=compressed||size>PF_ZIP_MAX_MEMBER||size>PF_ZIP_MAX_TOTAL-total||!namelen||namelen>1024||extra||comment)return -1;
  if(!fits(pos+46,namelen,end)||u32(c+42)!=local||!fits(local,30,cd))return -1;
  const unsigned char *name=c+46,*l=b+local;
  if(!pf_path_valid((const char *)name,namelen))return -1;
  /* ASCII-only paths: avoid Unicode/case-fold ambiguity in this subset. */
  for(size_t j=0;j<namelen;j++)if(name[j]>=127)return -1;
  if(u32(l)!=0x04034b50u||u16(l+4)!=u16(c+6)||u16(l+6)!=u16(c+8)||u16(l+8)||u32(l+14)!=crc||u32(l+18)!=size||u32(l+22)!=size||u16(l+26)!=namelen||u16(l+28))return -1;
  size_t start=local+30;
  if(!fits(start,namelen,cd)||memcmp(b+start,name,namelen))return -1;
  start+=namelen;
  if(!fits(start,size,cd))return -1;
  pf_zip_entry entry={name,b+start,namelen,size};
  for(size_t j=0;j<i;j++)if(conflict(out+j,&entry))return -1;
  if(crc32_bytes(entry.data,size)!=crc)return -1;
  out[i]=entry;total+=size;local=start+size;pos+=46+namelen;
 }
 if(local!=cd||pos!=end)return -1;
 *count=m;return 0;
}
