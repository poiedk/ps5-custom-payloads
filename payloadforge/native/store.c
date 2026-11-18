/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE 1
#include "store.h"
#include "core.h"
#include "manifest.h"
#include "tar.h"
#include "sha256.h"
#include "version.h"
#include <errno.h>
#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int is_dir(int fd){struct stat s;return fd>=0&&!fstat(fd,&s)&&S_ISDIR(s.st_mode);}
static int is_regular(int fd){struct stat s;return fd>=0&&!fstat(fd,&s)&&S_ISREG(s.st_mode);}
static int dir_at(int fd,const char *name,int create){
 if(create&&mkdirat(fd,name,0700)&&errno!=EEXIST)return -1;
 int out=openat(fd,name,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
 if(out<0)return -1;
 struct stat s;
 if(!is_dir(out)||fstat(out,&s)||s.st_uid!=geteuid()||(s.st_mode&0077)){close(out);return -1;}
 return out;
}
static int write_all(int fd,const unsigned char *data,size_t len){
 while(len){ssize_t n=write(fd,data,len);if(n<0&&errno==EINTR)continue;if(n<=0)return -1;data+=(size_t)n;len-=(size_t)n;}
 return 0;
}
static int new_file(int dir,const char *name,const void *data,size_t n){
 int fd=openat(dir,name,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
 if(fd<0)return -1;
 int status=write_all(fd,data,n)||fsync(fd)?-1:0;
 if(close(fd))status=-1;
 return status;
}
static int file_parent(int root,const char *path,char name[1025],int create){
 char copy[1025];size_t n=strlen(path);
 if(!n||n>=sizeof copy)return -1;
 memcpy(copy,path,n+1);
 int fd=dup(root);if(fd<0)return -1;
 char *part=copy,*slash;
 while((slash=strchr(part,'/'))){
  *slash=0;
  int next=dir_at(fd,part,create);
  if(next<0||(create&&fsync(fd))){if(next>=0)close(next);close(fd);return -1;}
  close(fd);fd=next;part=slash+1;
 }
 memcpy(name,part,strlen(part)+1);return fd;
}
static int write_member(int root,const pf_zip_entry *e){
 char path[1025],name[1025];
 if(e->name_len>=sizeof path)return -1;
 memcpy(path,e->name,e->name_len);path[e->name_len]=0;
 int fd=file_parent(root,path,name,1);if(fd<0)return -1;
 int rc=new_file(fd,name,e->data,e->size);
 if(!rc&&fsync(fd))rc=-1;
 close(fd);return rc;
}
static int lock_exclusive(int fd){
 struct flock lock={0};lock.l_type=F_WRLCK;lock.l_whence=SEEK_SET;
 int rc;do{rc=fcntl(fd,F_SETLKW,&lock);}while(rc<0&&errno==EINTR);
 return rc;
}
static int exists_at(int fd,const char *name){
 struct stat s;if(!fstatat(fd,name,&s,AT_SYMLINK_NOFOLLOW))return 1;
 return errno==ENOENT?0:-1;
}
/* Read only regular, bounded files beneath already opened directories. */
static unsigned char *read_file(int dir,const char *name,size_t limit,size_t *size){
 int fd=openat(dir,name,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);
 if(fd<0)return NULL;
 struct stat st;
 if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_uid!=geteuid()||st.st_nlink!=1||st.st_size<0||(uint64_t)st.st_size>limit){close(fd);return NULL;}
 size_t n=(size_t)st.st_size,pos=0;unsigned char *raw=malloc(n+1);
 if(!raw){close(fd);return NULL;}
 while(pos<n){ssize_t got=read(fd,raw+pos,n-pos);if(got<0&&errno==EINTR)continue;if(got<=0){free(raw);close(fd);return NULL;}pos+=(size_t)got;}
 unsigned char extra;ssize_t got;do{got=read(fd,&extra,1);}while(got<0&&errno==EINTR);
 close(fd);if(got!=0){free(raw);return NULL;}
 raw[n]=0;*size=n;return raw;
}
static int read_hash(int dir,const char *name,char out[65]){
 size_t n;unsigned char *raw=read_file(dir,name,64,&n);
 if(!raw)return -1;
 int rc=-1;
 if(n==64&&pf_sha_valid((const char *)raw,n)){memcpy(out,raw,65);rc=0;}
 free(raw);return rc;
}
static unsigned char *read_member(int root,const char *path,size_t *n){
 char name[1025];int parent=file_parent(root,path,name,0);
 if(parent<0)return NULL;
 unsigned char *raw=read_file(parent,name,PF_ZIP_MAX_MEMBER,n);close(parent);return raw;
}
static int put_data(int root,const pf_file *file,const unsigned char *raw,size_t n){
 pf_zip_entry entry={(const unsigned char *)file->path,raw,strlen(file->path),n};
 return write_member(root,&entry);
}
static int find_file(const pf_file *files,size_t count,const char *path){
 for(size_t i=0;i<count;i++)if(!strcmp(files[i].path,path))return (int)i;
 return -1;
}
/* Registry is a canonical effective manifest, separate from the upstream one.
 * The parser forbids quotes, escapes and non-ASCII path/metadata characters. */
static unsigned char *registry(const pf_manifest *plan,const pf_file *files,size_t count,size_t *n){
 unsigned char *raw=malloc(PF_MANIFEST_LIMIT);if(!raw)return NULL;
 size_t used=0;int got=snprintf((char *)raw,PF_MANIFEST_LIMIT,
 "{\"schema_version\":1,\"id\":\"%s\",\"version\":\"%s\",\"files\":[",plan->id,plan->version);
 if(got<0||(size_t)got>=PF_MANIFEST_LIMIT)goto bad;
 used=(size_t)got;
 for(size_t i=0;i<count;i++){
  const pf_file *f=files+i;
  got=snprintf((char *)raw+used,PF_MANIFEST_LIMIT-used,
   "%s{\"path\":\"%s\",\"sha256\":\"%s\",\"size\":%zu,\"policy\":\"%s\"}",i?",":"",f->path,f->sha256,f->size,f->preserve?"preserve":"replace-with-backup");
  if(got<0||(size_t)got>=PF_MANIFEST_LIMIT-used)goto bad;
  used+=(size_t)got;
 }
 if(PF_MANIFEST_LIMIT-used<3)goto bad;
 memcpy(raw+used,"]}",3);*n=used+2;return raw;
 bad:free(raw);return NULL;
}
/* The original, checksum-bound manifest is the canonical dependency metadata.
 * Effective registry remains schema 1 (actual file hashes and preserved paths). */
static int parse_upstream(const unsigned char *raw,size_t n,pf_manifest *plan,pf_file *files){
 pf_manifest_metadata *meta=calloc(1,sizeof(*meta));
 if(!meta)return -1;
 int rc=pf_manifest_parse_metadata(raw,n,plan,files,PF_ZIP_MAX_MEMBERS,meta);
 free(meta);return rc;
}
static int load_generation(int gen,const char *generation,const char *id,pf_manifest *out,pf_file *files){
 char mh[65],ah[65],rh[65];size_t n;
 unsigned char *raw=NULL;int rc=-1;
 if(read_hash(gen,"manifest.sha256",mh)||read_hash(gen,"archive.sha256",ah))return -1;
 raw=read_file(gen,"manifest.json",PF_MANIFEST_LIMIT,&n);
 pf_manifest upstream;
 if(!raw||!pf_sha256_matches(raw,n,mh)||parse_upstream(raw,n,&upstream,files)||strcmp(upstream.id,id))goto done;
 if(!strcmp(generation,ah)){*out=upstream;rc=0;goto done;}
 free(raw);raw=NULL;
 if(read_hash(gen,"registry.sha256",rh))goto done;
 raw=read_file(gen,"registry.json",PF_MANIFEST_LIMIT,&n);
 if(!raw||!pf_sha256_matches(raw,n,rh)||pf_manifest_parse(raw,n,out,files,PF_ZIP_MAX_MEMBERS)||strcmp(out->id,id)||strcmp(out->version,upstream.version))goto done;
 rc=0;
 done:free(raw);return rc;
}


static int lower_hash(const char *hash){
 if(!hash||!pf_sha_valid(hash,strlen(hash)))return 0;
 for(size_t i=0;i<64;i++)if(hash[i]>='A'&&hash[i]<='F')return 0;
 return 1;
}
/* Return 0 absent, 1 active, 2 uninstalled/drop, 3 uninstalled/keep, -1 malformed.
 * Uninstalled marker contains the verified snapshot ID, not a generation path. */
static int read_marker(int app,char id[65]){
 int present=exists_at(app,"CURRENT");if(present<=0)return present;
 size_t n;unsigned char *p=read_file(app,"CURRENT",81,&n);if(!p)return -1;
 int rc=-1;
 if(n==64&&lower_hash((const char *)p)){memcpy(id,p,65);rc=1;}
 else if(n==81&&!memcmp(p,"uninstalled:",12)&&(!memcmp(p+76,":keep",5)||!memcmp(p+76,":drop",5))){
  memcpy(id,p+12,64);id[64]=0;if(lower_hash(id))rc=p[77]=='k'?3:2;
 }
 free(p);return rc;
}
/* Read active manifests while the root lock is held. Never trust a directory
 * name alone, never traverse links, never mutate state in this validator. */
static int generation_metadata(int gen,const char *id,pf_manifest *plan,pf_file *files,pf_manifest_metadata *meta){
 char h[65];size_t n=0;int rc=-1;
 if(read_hash(gen,"manifest.sha256",h)||!lower_hash(h))return -1;
 unsigned char *raw=read_file(gen,"manifest.json",PF_MANIFEST_LIMIT,&n);
 if(raw&&pf_sha256_matches(raw,n,h)&&!pf_manifest_parse_metadata(raw,n,plan,files,PF_ZIP_MAX_MEMBERS,meta)&&!strcmp(plan->id,id))rc=0;
 free(raw);return rc;
}
static void state_entry(pf_package_state *state,const pf_manifest *plan,const pf_manifest_metadata *meta){
 memset(state,0,sizeof(*state));
 memcpy(state->id,plan->id,sizeof state->id);memcpy(state->version,plan->version,sizeof state->version);
 state->dependencies=meta->dependencies;state->dependency_count=meta->dependency_count;
 state->conflicts=meta->conflicts;state->conflict_count=meta->conflict_count;
 state->resources=meta->resources;state->resource_count=meta->resource_count;
}
static int active_metadata(int apps,const char *id,pf_manifest *plan,pf_file *scratch,pf_manifest_metadata *meta){
 int app=-1,gens=-1,gen=-1,rc=-1;char current[65];pf_manifest registry_plan;
 app=dir_at(apps,id,0);if(app<0)goto done;
 int marker=read_marker(app,current);
 if(marker==0||marker==2||marker==3){rc=0;goto done;}
 if(marker!=1)goto done;
 gens=dir_at(app,"generations",0);if(gens<0)goto done;
 gen=dir_at(gens,current,0);if(gen<0||load_generation(gen,current,id,&registry_plan,scratch))goto done;
 if(generation_metadata(gen,id,plan,scratch,meta)||strcmp(plan->version,registry_plan.version))goto done;
 rc=1;
 done:if(gen>=0)close(gen);if(gens>=0)close(gens);if(app>=0)close(app);return rc;
}
static int state_gate(int apps,const char *replace,const pf_manifest *proposed,const pf_manifest_metadata *meta){
 int rc=-1;size_t count=0,visited=0;DIR *dir=NULL;
 pf_package_state *state=calloc(PF_STATE_MAX,sizeof(*state));
 pf_manifest_metadata **owned=calloc(PF_STATE_MAX,sizeof(*owned));
 pf_file *scratch=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*scratch));
 if(!state||!owned||!scratch)goto end;
 if(proposed){if(!meta||strcmp(proposed->id,replace))goto end;state_entry(state+count++,proposed,meta);}
 int scan=dir_at(apps,".",0);if(scan<0)goto end;
 dir=fdopendir(scan);if(!dir){close(scan);goto end;}
 for(;;){
  errno=0;struct dirent *ent=readdir(dir);
  if(!ent){if(errno)goto end;break;}
  const char *id=ent->d_name;
  if(!strcmp(id,".")||!strcmp(id,".."))continue;
  if(++visited>PF_STATE_MAX*4u||!pf_id_valid(id,strlen(id)))goto end;
  if(!strcmp(id,replace))continue;
  pf_manifest plan;pf_manifest_metadata *m=calloc(1,sizeof(*m));if(!m)goto end;
  int active=active_metadata(apps,id,&plan,scratch,m);
  if(active<0){free(m);goto end;}
  if(!active){free(m);continue;}
  if(count>=PF_STATE_MAX){free(m);goto end;}
  owned[count]=m;state_entry(state+count++,&plan,m);
 }
 rc=pf_state_validate(state,count)?-1:0;
 end:if(dir)closedir(dir);
 if(owned)for(size_t i=0;i<PF_STATE_MAX;i++)free(owned[i]);
 free(scratch);free(owned);free(state);return rc;
}
static void snapshot_id(const char *generation,const char *registry_hash,const char *ah,const char *mh,char out[65]){
 char key[256];memcpy(key,generation,64);memcpy(key+64,registry_hash,64);
 memcpy(key+128,ah,64);memcpy(key+192,mh,64);
 pf_sha256_hex(key,sizeof key,out);
}
static int registry_compatible(const pf_manifest *up,const pf_file *original,const pf_manifest *effective,const pf_file *files){
 if(strcmp(up->id,effective->id)||strcmp(up->version,effective->version))return 0;
 for(size_t i=0;i<up->count;i++){
  int j=find_file(files,effective->count,original[i].path);
  if(j<0||files[j].preserve!=original[i].preserve)return 0;
  if(!original[i].preserve&&(files[j].size!=original[i].size||strcmp(files[j].sha256,original[i].sha256)))return 0;
 }
 for(size_t i=0;i<effective->count;i++)if(find_file(original,up->count,files[i].path)<0&&!files[i].preserve)return 0;
 return 1;
}
/* Verify exact registered bytes (including preserved configuration) in a snapshot. */
static int verify_snapshot(int backups,const char *id,const char *snapshot,pf_manifest *plan,pf_file *files,char generation[65]){
 int rc=-1,dir=-1,data=-1;size_t n,mn;char rh[65],ah[65],mh[65],expected[65];unsigned char *raw=NULL,*upstream=NULL;
 pf_file *original=NULL;pf_manifest up;
 if(!lower_hash(snapshot))return -1;
 dir=dir_at(backups,snapshot,0);if(dir<0)goto done;
 if(read_hash(dir,"generation.sha256",generation)||!lower_hash(generation)||read_hash(dir,"registry.sha256",rh)||!lower_hash(rh))goto done;
 if(read_hash(dir,"archive.sha256",ah)||!lower_hash(ah)||read_hash(dir,"manifest.sha256",mh)||!lower_hash(mh))goto done;
 snapshot_id(generation,rh,ah,mh,expected);if(strcmp(expected,snapshot))goto done;
 raw=read_file(dir,"registry.json",PF_MANIFEST_LIMIT,&n);
 if(!raw||!pf_sha256_matches(raw,n,rh)||pf_manifest_parse(raw,n,plan,files,PF_ZIP_MAX_MEMBERS)||strcmp(plan->id,id))goto done;
 original=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*original));
 upstream=read_file(dir,"manifest.json",PF_MANIFEST_LIMIT,&mn);
 if(!original||!upstream||!pf_sha256_matches(upstream,mn,mh)||parse_upstream(upstream,mn,&up,original)||!registry_compatible(&up,original,plan,files))goto done;
 data=dir_at(dir,"data",0);if(data<0)goto done;
 for(size_t i=0;i<plan->count;i++){
  size_t len;unsigned char *p=read_member(data,files[i].path,&len);
  if(!p)goto done;
  int valid=len==files[i].size&&pf_sha256_matches(p,len,files[i].sha256);
  free(p);if(!valid)goto done;
 }
 rc=0;
 done:free(original);free(upstream);free(raw);if(data>=0)close(data);if(dir>=0)close(dir);return rc;
}
/* Must be called under store lock; caller must quiesce the managed application.
 * Snapshots are independent copies with actual content hashes, never hardlinks. */
static int snapshot_locked(int app,const char *generation,const pf_manifest *plan,const pf_file *prior,int source_gen,int source,char out[65]){
 int rc=-1,backups=-1,stage=-1,data=-1;pf_file *files=NULL,*check=NULL;
 unsigned char *raw=NULL,*upstream=NULL;size_t n=0,mn=0,total=0;char rh[65],ah[65],mh[65],name[65],staging[80],saved[65];pf_manifest verified;
 files=calloc(plan->count,sizeof(*files));check=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*check));
 if(!files||!check||!lower_hash(generation))goto done;
 if(read_hash(source_gen,"archive.sha256",ah)||!lower_hash(ah)||read_hash(source_gen,"manifest.sha256",mh)||!lower_hash(mh))goto done;
 upstream=read_file(source_gen,"manifest.json",PF_MANIFEST_LIMIT,&mn);
 if(!upstream||!pf_sha256_matches(upstream,mn,mh))goto done;
 memcpy(files,prior,plan->count*sizeof(*files));
 for(size_t i=0;i<plan->count;i++){
  size_t len;unsigned char *p=read_member(source,files[i].path,&len);
  if(!p)goto done;
  int valid=(files[i].preserve||(len==files[i].size&&pf_sha256_matches(p,len,files[i].sha256)))&&len<=PF_ZIP_MAX_TOTAL-total;
  if(valid){files[i].size=len;total+=len;pf_sha256_hex(p,len,files[i].sha256);}
  free(p);if(!valid)goto done;
 }
 raw=registry(plan,files,plan->count,&n);
 if(!raw||pf_manifest_parse(raw,n,&verified,check,PF_ZIP_MAX_MEMBERS))goto done;
 pf_sha256_hex(raw,n,rh);snapshot_id(generation,rh,ah,mh,name);
 backups=dir_at(app,"backups",1);if(backups<0||fsync(app))goto done;
 int exists=exists_at(backups,name);
 if(exists<0)goto done;
 if(!exists){
  if(snprintf(staging,sizeof staging,".stage-%s",name)<0||mkdirat(backups,staging,0700))goto done;
  stage=dir_at(backups,staging,0);if(stage<0)goto done;
  data=dir_at(stage,"data",1);if(data<0)goto done;
  for(size_t i=0;i<plan->count;i++){
   size_t len;unsigned char *p=read_member(source,files[i].path,&len);
   if(!p)goto done;
   int valid=len==files[i].size&&pf_sha256_matches(p,len,files[i].sha256)&&!put_data(data,files+i,p,len);
   free(p);if(!valid)goto done;
  }
  if(fsync(data)||new_file(stage,"registry.json",raw,n)||new_file(stage,"registry.sha256",rh,64)||new_file(stage,"generation.sha256",generation,64)||new_file(stage,"manifest.json",upstream,mn)||new_file(stage,"manifest.sha256",mh,64)||new_file(stage,"archive.sha256",ah,64)||fsync(stage))goto done;
  if(renameat(backups,staging,backups,name)||fsync(backups))goto done;
 }
 if(verify_snapshot(backups,plan->id,name,&verified,check,saved))goto done;
 memcpy(out,name,65);rc=0;
 done:if(data>=0)close(data);if(stage>=0)close(stage);if(backups>=0)close(backups);
 free(upstream);free(raw);free(check);free(files);return rc;
}
static int open_root_lock(int root){
 struct stat st;
 if(fstat(root,&st)||!S_ISDIR(st.st_mode)||st.st_uid!=geteuid()||(st.st_mode&0077))return -1;
 int lock=openat(root,".lock",O_RDWR|O_CREAT|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK,0600);
 if(lock<0)return -1;
 if(!is_regular(lock)||fstat(lock,&st)||st.st_uid!=geteuid()||st.st_nlink!=1||lock_exclusive(lock)){close(lock);return -1;}
 return lock;
}
int pf_backup(int root,const char *id,char out[65]){
 if(!out)return -1;
 out[0]=0;
 if(!id||!pf_id_valid(id,strlen(id)))return -1;
 int rc=-1,lock=-1,apps=-1,app=-1,gens=-1,gen=-1,data=-1;
 pf_file *files=NULL;pf_manifest plan;char current[65];
 lock=open_root_lock(root);if(lock<0)goto done;
 apps=dir_at(root,"apps",0);if(apps<0)goto done;
 app=dir_at(apps,id,0);if(app<0||read_hash(app,"CURRENT",current)||!lower_hash(current))goto done;
 gens=dir_at(app,"generations",0);if(gens<0)goto done;
 gen=dir_at(gens,current,0);if(gen<0)goto done;
 files=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*files));if(!files||load_generation(gen,current,id,&plan,files))goto done;
 data=dir_at(gen,"data",0);if(data<0)goto done;
 rc=snapshot_locked(app,current,&plan,files,gen,data,out);
 done:if(data>=0)close(data);if(gen>=0)close(gen);if(gens>=0)close(gens);if(app>=0)close(app);if(apps>=0)close(apps);if(lock>=0)close(lock);
 free(files);return rc;
}
int pf_backup_verify(int root,const char *id,const char *snapshot){
 if(!id||!pf_id_valid(id,strlen(id))||!lower_hash(snapshot))return -1;
 int rc=-1,lock=-1,apps=-1,app=-1,backups=-1;pf_file *files=NULL;pf_manifest plan;char generation[65];
 lock=open_root_lock(root);if(lock<0)goto done;
 apps=dir_at(root,"apps",0);if(apps<0)goto done;
 app=dir_at(apps,id,0);if(app<0)goto done;
 backups=dir_at(app,"backups",0);if(backups<0)goto done;
 files=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*files));if(!files)goto done;
 rc=verify_snapshot(backups,id,snapshot,&plan,files,generation);
 done:if(backups>=0)close(backups);if(app>=0)close(app);if(apps>=0)close(apps);if(lock>=0)close(lock);free(files);return rc;
}

/* Failed staging directories are deliberately retained for explicit inspection.
 * A partial stage can never become active; no recursive deletion is performed.
 */
static int apply(int root,const unsigned char *archive,size_t an,const char *ah,
 const unsigned char *manifest,size_t mn,const char *mh,int action){
 int update=action!=0;
 int rc=-1,lock=-1,apps=-1,app=-1,gens=-1,stage=-1,data=-1;
 pf_file *files=NULL,*old=NULL,*check=NULL;pf_zip_entry *entries=NULL;unsigned char **owned=NULL,*expanded=NULL;size_t owned_count=0;
 int previous=-1,prior_data=-1,backups=-1,source_snapshot=-1;unsigned char *effective=NULL;size_t effective_n=0;
 int merge=update,reinstall=0;
 pf_manifest prior={0};char current_id[65]={0};
 pf_manifest plan;size_t count=0;pf_manifest_metadata *meta=NULL;
 struct stat rootstat;
 if(fstat(root,&rootstat)||!S_ISDIR(rootstat.st_mode)||rootstat.st_uid!=geteuid()||(rootstat.st_mode&0077))return -1;
 files=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*files));
 if(!files)goto done;
 meta=calloc(1,sizeof(*meta));if(!meta||pf_bundle_verify_metadata(archive,an,ah,manifest,mn,mh,&plan,files,PF_ZIP_MAX_MEMBERS,meta))goto done;
 owned_count=plan.count;entries=calloc(owned_count,sizeof(*entries));owned=calloc(owned_count,sizeof(*owned));if(!entries||!owned)goto done;
 if(pf_archive_scan(archive,an,entries,owned,&expanded,owned_count,&count)||count!=plan.count)goto done;
 lock=open_root_lock(root);if(lock<0)goto done;
 apps=dir_at(root,"apps",1);if(apps<0||fsync(root))goto done;
 app=dir_at(apps,plan.id,1);if(app<0||fsync(apps))goto done;
 int current=read_marker(app,current_id);
 if(current<0||(!update&&current==1)||(update&&current!=1)){rc=current>=0?-2:-1;goto done;}
 if(state_gate(apps,plan.id,&plan,meta))goto done;
 reinstall=current>=2;merge=update||current==3;
 gens=dir_at(app,"generations",1);if(gens<0||fsync(app))goto done;
 if(update){
  old=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*old));if(!old)goto done;
  previous=dir_at(gens,current_id,0);if(previous<0||load_generation(previous,current_id,plan.id,&prior,old))goto done;
  if(!strcmp(prior.version,plan.version))goto done;
  if(action==2||action==3){int order;if(pf_version_compare(plan.version,prior.version,&order)||(action==2?order<=0:order>=0))goto done;}
  prior_data=dir_at(previous,"data",0);if(prior_data<0)goto done;
  /* Verify every registered immutable file before staging; mutable configs may differ. */
  for(size_t i=0;i<prior.count;i++){
   size_t n;unsigned char *raw=read_member(prior_data,old[i].path,&n);
   if(!raw)goto done;
   int valid=old[i].preserve||(n==old[i].size&&pf_sha256_matches(raw,n,old[i].sha256));
   free(raw);if(!valid)goto done;
   if(old[i].preserve){
    int index=find_file(files,plan.count,old[i].path);
    if(index>=0&&!files[index].preserve)goto done;
    if(index<0){if(plan.count>=PF_ZIP_MAX_MEMBERS)goto done;files[plan.count++]=old[i];}
   }
  }
  char backup[65];if(snapshot_locked(app,current_id,&prior,old,previous,prior_data,backup))goto done;
 }
 if(current==3){
  old=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*old));if(!old)goto done;
  backups=dir_at(app,"backups",0);if(backups<0)goto done;
  char source_gen[65];if(verify_snapshot(backups,plan.id,current_id,&prior,old,source_gen))goto done;
  source_snapshot=dir_at(backups,current_id,0);if(source_snapshot<0)goto done;
  prior_data=dir_at(source_snapshot,"data",0);if(prior_data<0)goto done;
  for(size_t i=0;i<prior.count;i++)if(old[i].preserve){
   int index=find_file(files,plan.count,old[i].path);
   if(index>=0&&!files[index].preserve)goto done;
   if(index<0){if(plan.count>=PF_ZIP_MAX_MEMBERS)goto done;files[plan.count++]=old[i];}
  }
 }
 /* Content-addressed initial generation; updates bind predecessor and manifest. */
 char generation[65],staging[80],pointer[80];
 if(update||reinstall){
  char identity[192];memcpy(identity,ah,64);memcpy(identity+64,mh,64);memcpy(identity+128,current_id,64);
  pf_sha256_hex(identity,sizeof identity,generation);
 }else{memcpy(generation,ah,64);generation[64]=0;}
 if(snprintf(staging,sizeof staging,".stage-%s",generation)<0||
    snprintf(pointer,sizeof pointer,".pointer-%s",generation)<0)goto done;
 if(exists_at(gens,generation)!=0||mkdirat(gens,staging,0700))goto done;
 stage=dir_at(gens,staging,0);if(stage<0)goto done;
 data=dir_at(stage,"data",1);if(data<0)goto done;
 if(!merge&&!reinstall){
  for(size_t i=0;i<count;i++)if(write_member(data,entries+i))goto done;
 }else{
  size_t total=0;
  for(size_t i=0;i<plan.count;i++){
   pf_file *f=files+i;int index=merge?find_file(old,prior.count,f->path):-1;
   if(index>=0&&old[index].preserve){
    size_t n;unsigned char *raw=read_member(prior_data,f->path,&n);if(!raw)goto done;
    if(n>PF_ZIP_MAX_TOTAL-total){free(raw);goto done;}
    f->size=n;pf_sha256_hex(raw,n,f->sha256);int status=put_data(data,f,raw,n);free(raw);if(status)goto done;
   }else{
    const pf_zip_entry *entry=NULL;
    for(size_t j=0;j<count;j++)if(strlen(f->path)==entries[j].name_len&&!memcmp(f->path,entries[j].name,entries[j].name_len)){entry=entries+j;break;}
    if(!entry||f->size>PF_ZIP_MAX_TOTAL-total||write_member(data,entry))goto done;
   }
   total+=f->size;
  }
  effective=registry(&plan,files,plan.count,&effective_n);if(!effective)goto done;
  check=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*check));pf_manifest validated;
  if(!check||pf_manifest_parse(effective,effective_n,&validated,check,PF_ZIP_MAX_MEMBERS))goto done;
  char rh[65];pf_sha256_hex(effective,effective_n,rh);
  if(new_file(stage,"registry.json",effective,effective_n)||new_file(stage,"registry.sha256",rh,64))goto done;
 }
 if(fsync(data)||new_file(stage,"manifest.json",manifest,mn)||new_file(stage,"archive.sha256",ah,64)||new_file(stage,"manifest.sha256",mh,64)||fsync(stage))goto done;
 if(renameat(gens,staging,gens,generation)||fsync(gens))goto done;
 if(new_file(app,pointer,generation,64))goto done;
 if(renameat(app,pointer,app,"CURRENT"))goto done;
 rc=fsync(app)?-3:0;
 done:
 if(prior_data>=0)close(prior_data);
 if(source_snapshot>=0)close(source_snapshot);
 if(backups>=0)close(backups);
 if(previous>=0)close(previous);
 if(data>=0)close(data);
 if(stage>=0)close(stage);
 if(gens>=0)close(gens);
 if(app>=0)close(app);
 if(apps>=0)close(apps);
 if(lock>=0)close(lock);
 pf_archive_release(owned,&expanded,owned_count);free(owned);free(meta);free(effective);free(check);free(old);free(entries);free(files);return rc;
}

int pf_install_initial(int root,const unsigned char *a,size_t an,const char *ah,const unsigned char *m,size_t mn,const char *mh){
 return apply(root,a,an,ah,m,mn,mh,0);
}
int pf_install_update(int root,const unsigned char *a,size_t an,const char *ah,const unsigned char *m,size_t mn,const char *mh){
 return apply(root,a,an,ah,m,mn,mh,1);
}
int pf_update(int root,const unsigned char *a,size_t an,const char *ah,const unsigned char *m,size_t mn,const char *mh){
 return pf_install_update(root,a,an,ah,m,mn,mh);
}

/* Restore a verified snapshot into a fresh generation, retaining current
 * user settings. A snapshot contains upstream provenance independently of
 * its source generation. All native manifests currently reject dependencies.
 */
int pf_rollback(int root,const char *id,const char *snapshot){
 if(!id||!pf_id_valid(id,strlen(id))||!lower_hash(snapshot))return -1;
 int rc=-1,lock=-1,apps=-1,app=-1,gens=-1,previous=-1,prior_data=-1,backups=-1,target=-1,target_data=-1,stage=-1,data=-1;
 pf_file *files=NULL,*old=NULL,*check=NULL;pf_manifest plan,prior,validated;
 pf_manifest_metadata *meta=NULL;
 char current[65],source[65],ah[65],mh[65],rh[65],generation[65],previous_backup[65],staging[80],pointer[80];
 size_t mn=0,rn=0,total=0;unsigned char *manifest=NULL,*effective=NULL;
 lock=open_root_lock(root);if(lock<0)goto done;
 apps=dir_at(root,"apps",0);if(apps<0)goto done;
 app=dir_at(apps,id,0);if(app<0||read_hash(app,"CURRENT",current)||!lower_hash(current))goto done;
 gens=dir_at(app,"generations",0);if(gens<0)goto done;
 backups=dir_at(app,"backups",0);if(backups<0)goto done;
 files=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*files));old=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*old));check=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*check));
 if(!files||!old||!check||verify_snapshot(backups,id,snapshot,&plan,files,source))goto done;
 target=dir_at(backups,snapshot,0);if(target<0||read_hash(target,"archive.sha256",ah)||read_hash(target,"manifest.sha256",mh))goto done;
 manifest=read_file(target,"manifest.json",PF_MANIFEST_LIMIT,&mn);
 if(!manifest||!pf_sha256_matches(manifest,mn,mh))goto done;
 meta=calloc(1,sizeof(*meta));pf_manifest upstream;
 if(!meta||pf_manifest_parse_metadata(manifest,mn,&upstream,check,PF_ZIP_MAX_MEMBERS,meta)||strcmp(upstream.id,plan.id)||strcmp(upstream.version,plan.version)||state_gate(apps,id,&plan,meta))goto done;
 target_data=dir_at(target,"data",0);if(target_data<0)goto done;
 previous=dir_at(gens,current,0);if(previous<0||load_generation(previous,current,id,&prior,old))goto done;
 prior_data=dir_at(previous,"data",0);if(prior_data<0)goto done;
 for(size_t i=0;i<prior.count;i++)if(old[i].preserve){
  int j=find_file(files,plan.count,old[i].path);
  if(j>=0&&!files[j].preserve)goto done;
  if(j<0){if(plan.count>=PF_ZIP_MAX_MEMBERS)goto done;files[plan.count++]=old[i];}
 }
 if(snapshot_locked(app,current,&prior,old,previous,prior_data,previous_backup))goto done;
 char key[136];memcpy(key,"rollback",8);memcpy(key+8,current,64);memcpy(key+72,snapshot,64);
 pf_sha256_hex(key,sizeof key,generation);
 if(snprintf(staging,sizeof staging,".stage-%s",generation)<0||snprintf(pointer,sizeof pointer,".pointer-%s",generation)<0||exists_at(gens,generation)!=0||mkdirat(gens,staging,0700))goto done;
 stage=dir_at(gens,staging,0);if(stage<0)goto done;
 data=dir_at(stage,"data",1);if(data<0)goto done;
 for(size_t i=0;i<plan.count;i++){
  pf_file *file=files+i;int j=find_file(old,prior.count,file->path);
  int preserve=j>=0&&old[j].preserve;size_t n;
  unsigned char *raw=read_member(preserve?prior_data:target_data,file->path,&n);if(!raw)goto done;
  int valid=n<=PF_ZIP_MAX_TOTAL-total&&(preserve||(n==file->size&&pf_sha256_matches(raw,n,file->sha256)));
  if(valid){file->size=n;pf_sha256_hex(raw,n,file->sha256);total+=n;valid=!put_data(data,file,raw,n);}
  free(raw);if(!valid)goto done;
 }
 effective=registry(&plan,files,plan.count,&rn);
 if(!effective||pf_manifest_parse(effective,rn,&validated,check,PF_ZIP_MAX_MEMBERS))goto done;
 pf_sha256_hex(effective,rn,rh);
 if(fsync(data)||new_file(stage,"registry.json",effective,rn)||new_file(stage,"registry.sha256",rh,64)||new_file(stage,"manifest.json",manifest,mn)||new_file(stage,"manifest.sha256",mh,64)||new_file(stage,"archive.sha256",ah,64)||fsync(stage))goto done;
 if(renameat(gens,staging,gens,generation)||fsync(gens)||new_file(app,pointer,generation,64)||renameat(app,pointer,app,"CURRENT"))goto done;
 rc=fsync(app)?-3:0;
 done:
 if(data>=0)close(data);
 if(stage>=0)close(stage);
 if(target_data>=0)close(target_data);
 if(target>=0)close(target);
 if(backups>=0)close(backups);
 if(prior_data>=0)close(prior_data);
 if(previous>=0)close(previous);
 if(gens>=0)close(gens);
 if(app>=0)close(app);
 if(apps>=0)close(apps);
 if(lock>=0)close(lock);
 free(meta);free(effective);free(manifest);free(check);free(old);free(files);return rc;
}

/* Logical deactivation precedes registry-only cleanup. No recursive removal;
 * unregistered data, old generations and snapshots remain. */
int pf_uninstall(int root,const char *id,int keep,size_t *removed){
 if(!removed)return -1;
 *removed=0;
 if(!id||!pf_id_valid(id,strlen(id))||(keep!=0&&keep!=1))return -1;
 int rc=-1,lock=-1,apps=-1,app=-1,gens=-1,gen=-1,data=-1;
 pf_file *files=NULL;pf_manifest plan;char current[65],snapshot[65],marker[82],pointer[80];
 lock=open_root_lock(root);if(lock<0)goto done;
 apps=dir_at(root,"apps",0);if(apps<0)goto done;
 app=dir_at(apps,id,0);if(app<0)goto done;
 if(read_marker(app,current)!=1){rc=-2;goto done;}
 if(state_gate(apps,id,NULL,NULL))goto done;
 gens=dir_at(app,"generations",0);if(gens<0)goto done;
 gen=dir_at(gens,current,0);if(gen<0)goto done;
 files=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*files));if(!files||load_generation(gen,current,id,&plan,files))goto done;
 data=dir_at(gen,"data",0);if(data<0||snapshot_locked(app,current,&plan,files,gen,data,snapshot))goto done;
 if(snprintf(marker,sizeof marker,"uninstalled:%s:%s",snapshot,keep?"keep":"drop")!=81||
    snprintf(pointer,sizeof pointer,".uninstall-%s",snapshot)<0)goto done;
 if(new_file(app,pointer,marker,81)||renameat(app,pointer,app,"CURRENT"))goto done;
 if(fsync(app)){rc=-3;goto done;}
 rc=0;
 for(size_t i=0;i<plan.count;i++){
  char name[1025];int parent=file_parent(data,files[i].path,name,0);
  if(parent<0){rc=1;continue;}
  struct stat st;
  if(fstatat(parent,name,&st,AT_SYMLINK_NOFOLLOW)||!S_ISREG(st.st_mode)||st.st_uid!=geteuid()||st.st_nlink!=1||unlinkat(parent,name,0))rc=1;
  else{(*removed)++;if(fsync(parent))rc=1;}
  close(parent);
 }
 done:if(data>=0)close(data);if(gen>=0)close(gen);if(gens>=0)close(gens);if(app>=0)close(app);if(apps>=0)close(apps);if(lock>=0)close(lock);
 free(files);return rc;
}

int pf_install_upgrade(int root,const unsigned char *a,size_t an,const char *ah,const unsigned char *m,size_t mn,const char *mh){
 return apply(root,a,an,ah,m,mn,mh,2);
}
int pf_install_downgrade(int root,const unsigned char *a,size_t an,const char *ah,const unsigned char *m,size_t mn,const char *mh){
 return apply(root,a,an,ah,m,mn,mh,3);
}
/* Inventory reads registry metadata; it is not a full content verification. */
int pf_status(int root,const char *id,char version[65],char generation[65]){
 if(!version||!generation)return -1;
 version[0]=generation[0]=0;
 if(!id||!pf_id_valid(id,strlen(id)))return -1;
 int rc=-1,lock=-1,apps=-1,app=-1,gens=-1,gen=-1;char current[65];
 pf_manifest plan;pf_file *files=NULL;
 lock=open_root_lock(root);if(lock<0)goto done;
 int present=exists_at(root,"apps");if(!present){rc=0;goto done;}if(present<0)goto done;
 apps=dir_at(root,"apps",0);if(apps<0)goto done;
 present=exists_at(apps,id);if(!present){rc=0;goto done;}if(present<0)goto done;
 app=dir_at(apps,id,0);if(app<0)goto done;
 present=read_marker(app,current);if(present==0||present>=2){rc=0;goto done;}if(present<0)goto done;
 gens=dir_at(app,"generations",0);if(gens<0)goto done;
 gen=dir_at(gens,current,0);if(gen<0)goto done;
 files=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*files));if(!files||load_generation(gen,current,id,&plan,files))goto done;
 memcpy(version,plan.version,strlen(plan.version)+1);memcpy(generation,current,65);rc=1;
 done:if(gen>=0)close(gen);if(gens>=0)close(gens);if(app>=0)close(app);if(apps>=0)close(apps);if(lock>=0)close(lock);
 free(files);return rc;
}
