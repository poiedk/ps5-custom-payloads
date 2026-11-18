/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "inflate.h"
#include "tar.h"
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
static voidpf pf_alloc(voidpf opaque,uInt count,uInt size){
 (void)opaque;
 if(size&&count>SIZE_MAX/size)return Z_NULL;
 return calloc(count,size);
}
static void pf_release(voidpf opaque,voidpf value){(void)opaque;free(value);}
void pf_inflate_free(void *out){free(out);}
int pf_inflate_exact(const unsigned char *raw,size_t n,size_t expected,unsigned char **out){
 if(!out)return -1;
 *out=NULL;
 if(!raw||!n||n>PF_ZIP_MAX_ARCHIVE||expected>PF_ZIP_MAX_MEMBER||
    n>UINT_MAX||expected>=UINT_MAX||(expected+199u)/200u>n)return -1;
 unsigned char *result=malloc(expected+1u);
 if(!result)return -1;
 z_stream stream;memset(&stream,0,sizeof(stream));
 stream.zalloc=pf_alloc;stream.zfree=pf_release;
 stream.next_in=(Bytef *)raw;stream.avail_in=(uInt)n;
 stream.next_out=result;stream.avail_out=(uInt)(expected+1u);
 if(inflateInit2(&stream,-MAX_WBITS)!=Z_OK){free(result);return -1;}
 int status=inflate(&stream,Z_FINISH);
 int valid=status==Z_STREAM_END&&stream.total_in==n&&stream.avail_in==0&&stream.total_out==expected;
 if(inflateEnd(&stream)!=Z_OK)valid=0;
 if(!valid){free(result);return -1;}
 *out=result;return 0;
}

int pf_gzip_expand(const unsigned char *raw,size_t n,unsigned char **out,size_t *size){
 if(!out||!size)return -1;
 *out=NULL;*size=0;
 if(!raw||n<18||n>PF_ZIP_MAX_ARCHIVE||n>UINT_MAX||raw[0]!=0x1f||raw[1]!=0x8b||raw[2]!=8)return -1;
 const unsigned char *p=raw+n-4;
 size_t expected=(uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
 if(expected>PF_TAR_LIMIT||expected>=UINT_MAX||(expected+199u)/200u>n)return -1;
 unsigned char *result=malloc(expected+1u);
 if(!result)return -1;
 z_stream stream;memset(&stream,0,sizeof stream);
 stream.zalloc=pf_alloc;stream.zfree=pf_release;
 stream.next_in=(Bytef *)raw;stream.avail_in=(uInt)n;
 stream.next_out=result;stream.avail_out=(uInt)(expected+1u);
 if(inflateInit2(&stream,MAX_WBITS+16)!=Z_OK){free(result);return -1;}
 int status=inflate(&stream,Z_FINISH);
 int valid=status==Z_STREAM_END&&stream.total_in==n&&stream.avail_in==0&&stream.total_out==expected;
 if(inflateEnd(&stream)!=Z_OK)valid=0;
 if(!valid){free(result);return -1;}
 *out=result;*size=expected;return 0;
}
