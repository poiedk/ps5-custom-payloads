/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "manifest.h"
#include "core.h"
#include "sha256.h"
#include "zip.h"
#include <stdlib.h>
#include <string.h>

typedef struct {const unsigned char *p,*end;} parser;
static void ws(parser *s){while(s->p<s->end&&(*s->p==' '||*s->p=='\t'||*s->p=='\r'||*s->p=='\n'))s->p++;}
static int take(parser *s,unsigned char c){ws(s);if(s->p==s->end||*s->p!=c)return 0;s->p++;return 1;}
static int str(parser *s,char *out,size_t cap){
 if(!take(s,'"'))return 0;
 size_t n=0;
 while(s->p<s->end&&*s->p!='"'){
  unsigned char c=*s->p++;
  if(c<32||c>=127||c=='\\'||n+1>=cap)return 0;
  out[n++]=(char)c;
 }
 if(s->p==s->end)return 0;
 s->p++;out[n]=0;return 1;
}
static int number(parser *s,size_t *out,size_t limit){
 ws(s);if(s->p==s->end||*s->p<'0'||*s->p>'9')return 0;
 if(*s->p=='0'){s->p++;*out=0;return !(s->p<s->end&&*s->p>='0'&&*s->p<='9');}
 size_t n=0;while(s->p<s->end&&*s->p>='0'&&*s->p<='9'){
  size_t d=(size_t)(*s->p++-'0');if(d>limit||n>(limit-d)/10)return 0;n=10*n+d;}
 *out=n;return 1;
}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int same(const char *a,const char *b){while(*a&&*b&&fold((unsigned char)*a)==fold((unsigned char)*b)){a++;b++;}return !*a&&!*b;}
static int collision(const char *a,const char *b){
 while(*a&&*b&&fold((unsigned char)*a)==fold((unsigned char)*b)){a++;b++;}
 return (!*a&&(!*b||*b=='/'))||(!*b&&*a=='/');
}
static int alpha(unsigned c){return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9');}
static int version_valid(const char *v){
 if(!alpha((unsigned char)*v))return 0;
 for(;*v;v++)if(!alpha((unsigned char)*v)&&!strchr("._+-",*v))return 0;
 return 1;
}
static int file_parse(parser *s,pf_file *f){
 char key[32],policy[32];unsigned seen=0;
 if(!take(s,'{'))return 0;
 memset(f,0,sizeof(*f));
 for(;;){
  if(!str(s,key,sizeof key)||!take(s,':'))return 0;
  unsigned bit=0;
  if(!strcmp(key,"path")){bit=1;if(!str(s,f->path,sizeof f->path))return 0;}
  else if(!strcmp(key,"sha256")){bit=2;if(!str(s,f->sha256,sizeof f->sha256))return 0;}
  else if(!strcmp(key,"size")){bit=4;if(!number(s,&f->size,PF_ZIP_MAX_MEMBER))return 0;}
  else if(!strcmp(key,"policy")){bit=8;if(!str(s,policy,sizeof policy))return 0;
   if(!strcmp(policy,"preserve"))f->preserve=1;else if(strcmp(policy,"replace-with-backup"))return 0;}
  else return 0;
  if(seen&bit)return 0;
  seen|=bit;
  if(take(s,'}'))break;
  if(!take(s,','))return 0;
 }
 if(seen!=15||!pf_path_valid(f->path,strlen(f->path))||!pf_sha_valid(f->sha256,strlen(f->sha256)))return 0;
 for(size_t i=0;i<64;i++)if(f->sha256[i]>='A'&&f->sha256[i]<='F')return 0;
 if(f->path[0]=='.'||strstr(f->path,"/."))return 0;
 const char *suffix=strrchr(f->path,'.');
 if(!suffix||strchr(suffix,'/'))return 0;
 const char *configs[]={".json",".ini",".cfg",".conf"};
 for(size_t i=0;i<sizeof configs/sizeof *configs;i++)if(same(suffix,configs[i]))return f->preserve;
 const char *assets[]={".txt",".png",".jpg",".jpeg",".webp",".md",".dat"};
 for(size_t i=0;i<sizeof assets/sizeof *assets;i++)if(same(suffix,assets[i]))return 1;
 return 0;
}
static int dep_list(parser *s,pf_dep *items,size_t *count){
 if(!take(s,'['))return 0;
 if(take(s,']'))return 1;
 for(;;){
  if(*count>=PF_DEP_MAX||!take(s,'{'))return 0;
  pf_dep *d=items+*count;unsigned seen=0;char key[32];
  for(;;){
   if(!str(s,key,sizeof key)||!take(s,':'))return 0;
   unsigned bit=0;
   if(!strcmp(key,"id")){bit=1;if(!str(s,d->id,sizeof d->id))return 0;}
   else if(!strcmp(key,"constraint")){bit=2;if(!str(s,d->constraint,sizeof d->constraint))return 0;}
   else return 0;
   if(seen&bit)return 0;
   seen|=bit;
   if(take(s,'}'))break;
   if(!take(s,','))return 0;
  }
  if(seen!=3||!pf_id_valid(d->id,strlen(d->id))||pf_constraint_match("1",d->constraint)<0)return 0;
  for(size_t j=0;j<*count;j++)if(!strcmp(items[j].id,d->id))return 0;
  (*count)++;
  if(take(s,']'))return 1;
  if(!take(s,','))return 0;
 }
}
static int resource_list(parser *s,pf_resource *items,size_t *count){
 if(!take(s,'['))return 0;
 if(take(s,']'))return 1;
 for(;;){
  if(*count>=PF_RESOURCE_MAX||!take(s,'{'))return 0;
  pf_resource *r=items+*count;unsigned seen=0;char key[32],kind[8]={0};
  int value_is_path=0;size_t port=0;
  for(;;){
   if(!str(s,key,sizeof key)||!take(s,':'))return 0;
   unsigned bit=0;
   if(!strcmp(key,"type")){bit=1;if(!str(s,kind,sizeof kind))return 0;}
   else if(!strcmp(key,"value")){
    bit=2;ws(s);
    if(s->p<s->end&&*s->p=='"'){value_is_path=1;if(!str(s,r->path,sizeof r->path))return 0;}
    else if(!number(s,&port,65535)||!port)return 0;
   }else return 0;
   if(seen&bit)return 0;
   seen|=bit;
   if(take(s,'}'))break;
   if(!take(s,','))return 0;
  }
  if(seen!=3)return 0;
  if(!strcmp(kind,"path")){
   size_t len=strlen(r->path);
   if(!value_is_path||len<=6||strncmp(r->path,"/data/",6)||!pf_path_valid(r->path+1,len-1))return 0;
   r->kind=PF_PATH;
  }else{
   if(value_is_path||!port)return 0;
   if(!strcmp(kind,"tcp"))r->kind=PF_TCP;
   else if(!strcmp(kind,"udp"))r->kind=PF_UDP;
   else return 0;
   r->port=(unsigned)port;
  }
  for(size_t j=0;j<*count;j++)if(items[j].kind==r->kind&&
   (r->kind==PF_PATH?same(items[j].path,r->path):items[j].port==r->port))return 0;
  (*count)++;
  if(take(s,']'))return 1;
  if(!take(s,','))return 0;
 }
}
static int parse_impl(const unsigned char *raw,size_t n,pf_manifest *out,pf_file *files,size_t cap,pf_manifest_metadata *meta){
 if(!out)return -1;
 memset(out,0,sizeof(*out));
 if(!raw||!n||n>PF_MANIFEST_LIMIT||!files||!cap)return -1;
 parser s={raw,raw+n};pf_manifest m={0};char key[32];unsigned seen=0;
 if(!take(&s,'{'))return -1;
 for(;;){
  if(!str(&s,key,sizeof key)||!take(&s,':'))return -1;
  unsigned bit=0;
  if(!strcmp(key,"schema_version")){size_t v;bit=1;if(!number(&s,&v,3)||!v)return -1;m.schema=(unsigned)v;}
  else if(!strcmp(key,"id")){bit=2;if(!str(&s,m.id,sizeof m.id))return -1;}
  else if(!strcmp(key,"version")){bit=4;if(!str(&s,m.version,sizeof m.version))return -1;}
  else if(!strcmp(key,"files")){
   bit=8;if(!take(&s,'['))return -1;
   if(!take(&s,']'))for(;;){
    if(m.count>=cap||m.count>=PF_ZIP_MAX_MEMBERS||!file_parse(&s,files+m.count))return -1;
    pf_file *f=files+m.count;
    if(f->size>PF_ZIP_MAX_TOTAL-m.total)return -1;
    for(size_t j=0;j<m.count;j++)if(collision(f->path,files[j].path))return -1;
    m.total+=f->size;m.count++;
    if(take(&s,']'))break;
    if(!take(&s,','))return -1;
   }
  } else if(!strcmp(key,"dependencies")||!strcmp(key,"resources")||!strcmp(key,"conflicts")){
   bit=!strcmp(key,"dependencies")?16:!strcmp(key,"resources")?32:64;
   if(!meta){if(!take(&s,'[')||!take(&s,']'))return -1;}
   else if(seen&bit)return -1;
   else if(bit==16){if(!dep_list(&s,meta->dependencies,&meta->dependency_count))return -1;}
   else if(bit==32){if(!resource_list(&s,meta->resources,&meta->resource_count))return -1;}
   else if(!dep_list(&s,meta->conflicts,&meta->conflict_count))return -1;
  }else return -1;
  if(seen&bit)return -1;
  seen|=bit;
  if(take(&s,'}'))break;
  if(!take(&s,','))return -1;
 }
 ws(&s);
 if(s.p!=s.end||seen!=(m.schema==1?15u:m.schema==2?31u:127u)||!m.count||!pf_id_valid(m.id,strlen(m.id))||!version_valid(m.version))return -1;
 *out=m;return 0;
}
int pf_manifest_parse(const unsigned char *raw,size_t n,pf_manifest *out,pf_file *files,size_t cap){
 return parse_impl(raw,n,out,files,cap,NULL);
}
int pf_manifest_parse_metadata(const unsigned char *raw,size_t n,pf_manifest *out,pf_file *files,size_t cap,pf_manifest_metadata *meta){
 if(out)memset(out,0,sizeof(*out));
 if(!meta)return -1;
 memset(meta,0,sizeof(*meta));
 int rc=parse_impl(raw,n,out,files,cap,meta);
 if(rc)memset(meta,0,sizeof(*meta));
 return rc;
}
static int verify_impl(const unsigned char *a,size_t an,const char *ah,const unsigned char *m,size_t mn,const char *mh,pf_manifest *out,pf_file *files,size_t cap,pf_manifest_metadata *meta){
 if(!out)return -1;
 memset(out,0,sizeof(*out));
 if(!a||!m||!an||an>PF_ZIP_MAX_ARCHIVE||!mn||mn>PF_MANIFEST_LIMIT||!files||!cap||cap>PF_ZIP_MAX_MEMBERS)return -1;
 if(!pf_sha256_matches(a,an,ah)||!pf_sha256_matches(m,mn,mh))return -1;
 pf_manifest plan;
 if(parse_impl(m,mn,&plan,files,cap,meta))return -1;
 pf_zip_entry *entries=calloc(plan.count,sizeof(*entries));
 if(!entries)return -1;
 size_t count=0;int status=-1;
 if(pf_zip_scan(a,an,entries,plan.count,&count)||count!=plan.count)goto end;
 for(size_t i=0;i<count;i++){
  pf_zip_entry *e=entries+i;pf_file *match=NULL;
  for(size_t j=0;j<plan.count;j++)if(strlen(files[j].path)==e->name_len&&!memcmp(files[j].path,e->name,e->name_len)){match=files+j;break;}
  if(!match||e->size!=match->size||!pf_sha256_matches(e->data,e->size,match->sha256))goto end;
 }
 *out=plan;status=0;
 end:free(entries);return status;
}

int pf_bundle_verify(const unsigned char *a,size_t an,const char *ah,const unsigned char *m,size_t mn,const char *mh,pf_manifest *out,pf_file *files,size_t cap){
 return verify_impl(a,an,ah,m,mn,mh,out,files,cap,NULL);
}
int pf_bundle_verify_metadata(const unsigned char *a,size_t an,const char *ah,const unsigned char *m,size_t mn,const char *mh,pf_manifest *out,pf_file *files,size_t cap,pf_manifest_metadata *meta){
 if(out)memset(out,0,sizeof(*out));
 if(!meta)return -1;
 memset(meta,0,sizeof(*meta));
 int rc=verify_impl(a,an,ah,m,mn,mh,out,files,cap,meta);
 if(rc)memset(meta,0,sizeof(*meta));
 return rc;
}
