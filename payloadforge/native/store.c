/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE 1
#include "store.h"
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
 if(!is_dir(out)){close(out);return -1;}
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
static int file_parent(int root,const char *path,char name[1025]){
 char copy[1025];size_t n=strlen(path);
 if(!n||n>=sizeof copy)return -1;
 memcpy(copy,path,n+1);
 int fd=dup(root);if(fd<0)return -1;
 char *part=copy,*slash;
 while((slash=strchr(part,'/'))){
  *slash=0;
  int next=dir_at(fd,part,1);
  if(next<0||fsync(fd)){if(next>=0)close(next);close(fd);return -1;}
  close(fd);fd=next;part=slash+1;
 }
 memcpy(name,part,strlen(part)+1);return fd;
}
static int write_member(int root,const pf_zip_entry *e){
 char path[1025],name[1025];
 if(e->name_len>=sizeof path)return -1;
 memcpy(path,e->name,e->name_len);path[e->name_len]=0;
 int fd=file_parent(root,path,name);if(fd<0)return -1;
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
/* Failed staging directories are deliberately retained for explicit inspection.
 * A partial stage can never become active; no recursive deletion is performed.
 */
int pf_install_initial(int root,const unsigned char *archive,size_t an,const char *ah,
 const unsigned char *manifest,size_t mn,const char *mh){
 int rc=-1,lock=-1,apps=-1,app=-1,gens=-1,stage=-1,data=-1;
 pf_file *files=NULL;pf_zip_entry *entries=NULL;
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
 if(current!=0){rc=current>0?-2:-1;goto done;}
 gens=dir_at(app,"generations",1);if(gens<0||fsync(app))goto done;
 /* Content-addressed initial generation; collisions fail closed. */
 char generation[65],staging[80],pointer[80];
 memcpy(generation,ah,64);generation[64]=0;
 if(snprintf(staging,sizeof staging,".stage-%s",generation)<0||
    snprintf(pointer,sizeof pointer,".pointer-%s",generation)<0)goto done;
 if(exists_at(gens,generation)!=0||mkdirat(gens,staging,0700))goto done;
 stage=dir_at(gens,staging,0);if(stage<0)goto done;
 data=dir_at(stage,"data",1);if(data<0)goto done;
 for(size_t i=0;i<count;i++)if(write_member(data,entries+i))goto done;
 if(fsync(data)||new_file(stage,"manifest.json",manifest,mn)||new_file(stage,"archive.sha256",ah,64)||new_file(stage,"manifest.sha256",mh,64)||fsync(stage))goto done;
 if(renameat(gens,staging,gens,generation)||fsync(gens))goto done;
 if(new_file(app,pointer,generation,64))goto done;
 if(renameat(app,pointer,app,"CURRENT"))goto done;
 rc=fsync(app)?-3:0;
 done:
 if(data>=0)close(data);
 if(stage>=0)close(stage);
 if(gens>=0)close(gens);
 if(app>=0)close(app);
 if(apps>=0)close(apps);
 if(lock>=0)close(lock);
 free(entries);free(files);return rc;
}
