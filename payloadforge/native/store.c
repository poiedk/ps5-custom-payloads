/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE 1
#include "store.h"
#include "core.h"
#include "manifest.h"
#include "zip.h"
#include "sha256.h"
#include <errno.h>
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
static int load_generation(int gen,const char *generation,const char *id,pf_manifest *out,pf_file *files){
 char mh[65],ah[65],rh[65];size_t n;
 unsigned char *raw=NULL;int rc=-1;
 if(read_hash(gen,"manifest.sha256",mh)||read_hash(gen,"archive.sha256",ah))return -1;
 raw=read_file(gen,"manifest.json",PF_MANIFEST_LIMIT,&n);
 pf_manifest upstream;
 if(!raw||!pf_sha256_matches(raw,n,mh)||pf_manifest_parse(raw,n,&upstream,files,PF_ZIP_MAX_MEMBERS)||strcmp(upstream.id,id))goto done;
 if(!strcmp(generation,ah)){*out=upstream;rc=0;goto done;}
 free(raw);raw=NULL;
 if(read_hash(gen,"registry.sha256",rh))goto done;
 raw=read_file(gen,"registry.json",PF_MANIFEST_LIMIT,&n);
 if(!raw||!pf_sha256_matches(raw,n,rh)||pf_manifest_parse(raw,n,out,files,PF_ZIP_MAX_MEMBERS)||strcmp(out->id,id)||strcmp(out->version,upstream.version))goto done;
 rc=0;
 done:free(raw);return rc;
}


/* Failed staging directories are deliberately retained for explicit inspection.
 * A partial stage can never become active; no recursive deletion is performed.
 */
static int apply(int root,const unsigned char *archive,size_t an,const char *ah,
 const unsigned char *manifest,size_t mn,const char *mh,int update){
 int rc=-1,lock=-1,apps=-1,app=-1,gens=-1,stage=-1,data=-1;
 pf_file *files=NULL,*old=NULL,*check=NULL;pf_zip_entry *entries=NULL;
 int previous=-1,prior_data=-1;unsigned char *effective=NULL;size_t effective_n=0;
 pf_manifest prior={0};char current_id[65]={0};
 pf_manifest plan;size_t count=0;
 struct stat rootstat;
 if(fstat(root,&rootstat)||!S_ISDIR(rootstat.st_mode)||rootstat.st_uid!=geteuid()||(rootstat.st_mode&0077))return -1;
 files=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*files));
 if(!files)goto done;
 if(pf_bundle_verify(archive,an,ah,manifest,mn,mh,&plan,files,PF_ZIP_MAX_MEMBERS))goto done;
 entries=calloc(plan.count,sizeof(*entries));if(!entries)goto done;
 if(pf_zip_scan(archive,an,entries,plan.count,&count)||count!=plan.count)goto done;
 lock=openat(root,".lock",O_RDWR|O_CREAT|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK,0600);
 if(lock<0||!is_regular(lock)||lock_exclusive(lock))goto done;
 apps=dir_at(root,"apps",1);if(apps<0||fsync(root))goto done;
 app=dir_at(apps,plan.id,1);if(app<0||fsync(apps))goto done;
 int current=exists_at(app,"CURRENT");
 if(current<0||(!update&&current>0)||(update&&current==0)){rc=current>=0?-2:-1;goto done;}
 gens=dir_at(app,"generations",1);if(gens<0||fsync(app))goto done;
 if(update){
  old=calloc(PF_ZIP_MAX_MEMBERS,sizeof(*old));if(!old)goto done;
  if(read_hash(app,"CURRENT",current_id))goto done;
  previous=dir_at(gens,current_id,0);if(previous<0||load_generation(previous,current_id,plan.id,&prior,old))goto done;
  if(!strcmp(prior.version,plan.version))goto done;
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
 }
 /* Content-addressed initial generation; updates bind predecessor and manifest. */
 char generation[65],staging[80],pointer[80];
 if(update){
  char identity[192];memcpy(identity,ah,64);memcpy(identity+64,mh,64);memcpy(identity+128,current_id,64);
  pf_sha256_hex(identity,sizeof identity,generation);
 }else{memcpy(generation,ah,64);generation[64]=0;}
 if(snprintf(staging,sizeof staging,".stage-%s",generation)<0||
    snprintf(pointer,sizeof pointer,".pointer-%s",generation)<0)goto done;
 if(exists_at(gens,generation)!=0||mkdirat(gens,staging,0700))goto done;
 stage=dir_at(gens,staging,0);if(stage<0)goto done;
 data=dir_at(stage,"data",1);if(data<0)goto done;
 if(!update){
  for(size_t i=0;i<count;i++)if(write_member(data,entries+i))goto done;
 }else{
  size_t total=0;
  for(size_t i=0;i<plan.count;i++){
   pf_file *f=files+i;int index=find_file(old,prior.count,f->path);
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
 if(previous>=0)close(previous);
 if(data>=0)close(data);
 if(stage>=0)close(stage);
 if(gens>=0)close(gens);
 if(app>=0)close(app);
 if(apps>=0)close(apps);
 if(lock>=0)close(lock);
 free(effective);free(check);free(old);free(entries);free(files);return rc;
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
