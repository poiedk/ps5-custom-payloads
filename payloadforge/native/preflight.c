/* Read-only native smoke test. No package installation, filesystem or networking. */
#include "core.h"
#include "sha256.h"
#include "zip.h"
#include "manifest.h"
#include "constraints.h"
#include "inflate.h"
#include "http.h"
#include <stdio.h>
#include <string.h>
#define EXPECT(x) do { if (!(x)) { fprintf(stderr,"FAIL: %s\n",#x); return 1; } } while(0)
int main(void){
    const char *paths[]={"settings.json","assets/icon.png","../outside","/absolute","a/../b","a\\b","a//b","a:stream"};
    const int okay[]={1,1,0,0,0,0,0,0};
    for(size_t i=0;i<sizeof(okay)/sizeof(okay[0]);i++)EXPECT(pf_path_valid(paths[i],strlen(paths[i]))==okay[i]);
    EXPECT(pf_id_valid("demo-1",6)); EXPECT(!pf_id_valid("../demo",7));
    EXPECT(pf_format_detect((const unsigned char *)"\x7f""ELF",4)==PF_ELF);
    EXPECT(pf_format_detect((const unsigned char *)"PK\x03\x04",4)==PF_ZIP);
    EXPECT(pf_format_detect((const unsigned char *)"\x1f\x8b",2)==PF_GZIP);
    EXPECT(pf_sha256_matches("abc",3,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
    EXPECT(!pf_sha256_matches("abd",3,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
    pf_zip_entry entry; size_t count=1;
    EXPECT(pf_zip_scan((const unsigned char *)"invalid",7,&entry,1,&count)!=0 && count==0);
    pf_manifest plan; pf_file file;
    EXPECT(pf_manifest_parse((const unsigned char *)"{}",2,&plan,&file,1)!=0 && plan.count==0);
    EXPECT(pf_constraint_match("1.2.3",">=1,<2")==1);
    EXPECT(pf_constraint_match("2",">=1,<2")==0);
    EXPECT(pf_constraint_match("1",">2,^1")==-1);
    const pf_dep needs[]={{"library",">=2"}};
    pf_package_state states[2]={
        {.id="demo",.version="1",.dependencies=needs,.dependency_count=1},
        {.id="library",.version="2"}
    };
    EXPECT(pf_state_validate(states,2)==0);
    EXPECT(pf_state_validate(states,1)==-2);
    const unsigned char compressed[]={0xcb,0x48,0xcd,0xc9,0xc9,0x07,0x00};
    unsigned char *expanded=NULL;
    EXPECT(pf_inflate_exact(compressed,sizeof compressed,5,&expanded)==0);
    int valid=expanded&&!memcmp(expanded,"hello",5);
    pf_inflate_free(expanded);
    EXPECT(valid);
    const unsigned char gzip_hello[]={0x1f,0x8b,0x08,0x00,0x00,0x00,0x00,0x00,0x02,0x03,0xcb,0x48,0xcd,0xc9,0xc9,0x07,0x00,0x86,0xa6,0x10,0x36,0x05,0x00,0x00,0x00};
    size_t expanded_n=0;expanded=NULL;
    EXPECT(pf_gzip_expand(gzip_hello,sizeof gzip_hello,&expanded,&expanded_n)==0);
    valid=expanded&&expanded_n==5&&!memcmp(expanded,"hello",5);
    pf_inflate_free(expanded);
    EXPECT(valid);
    const char token[]="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    const char request[]="GET /api/health HTTP/1.1\r\nHost: 127.0.0.1:8765\r\nAuthorization: Bearer 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\r\n\r\n";
    pf_http_request parsed;
    EXPECT(pf_http_parse((const unsigned char *)request,sizeof request-1,8765,token,&parsed)==200);
    EXPECT(parsed.route==PF_HTTP_HEALTH);
    puts("PayloadForge native preflight: OK (read-only; not installer)");
    return 0;
}
