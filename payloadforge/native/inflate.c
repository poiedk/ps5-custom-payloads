/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "inflate.h"
#include "zip.h"
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
