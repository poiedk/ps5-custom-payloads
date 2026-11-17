#include "core.h"
#include <string.h>
static int lower(unsigned char c){return c>='a' && c<='z';}
static int digit(unsigned char c){return c>='0' && c<='9';}
int pf_id_valid(const char *s,size_t n){
  if(!s || n<1 || n>48 || (!lower((unsigned char)s[0]) && !digit((unsigned char)s[0])))return 0;
  for(size_t i=0;i<n;i++)if(!lower((unsigned char)s[i]) && !digit((unsigned char)s[i]) && s[i]!='-')return 0;
  return 1;
}
int pf_path_valid(const char *s,size_t n){
  if(!s || n<1 || n>4096 || s[0]=='/')return 0;
  size_t start=0;
  for(size_t i=0;i<=n;i++){
    if(i<n && ((unsigned char)s[i]<32 || s[i]=='\\' || s[i]==':'))return 0;
    if(i==n || s[i]=='/'){
      size_t len=i-start;
      if(!len || (len==1 && s[start]=='.') || (len==2 && s[start]=='.' && s[start+1]=='.'))return 0;
      start=i+1;
    }
  }
  return 1;
}
int pf_sha_valid(const char *s,size_t n){
  if(!s || n!=64)return 0;
  for(size_t i=0;i<n;i++){unsigned char c=(unsigned char)s[i];if(!digit(c)&&!(c>='a'&&c<='f')&&!(c>='A'&&c<='F'))return 0;}
  return 1;
}
enum pf_format pf_format_detect(const unsigned char *data,size_t n){
  if(!data)return PF_UNKNOWN;
  if(n>=4 && !memcmp(data,"\x7f""ELF",4))return PF_ELF;
  if(n>=4 && (!memcmp(data,"PK\x03\x04",4)||!memcmp(data,"PK\x05\x06",4)))return PF_ZIP;
  if(n>=2 && data[0]==0x1f && data[1]==0x8b)return PF_GZIP;
  return PF_UNKNOWN;
}
