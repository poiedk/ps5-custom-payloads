/* Read-only native smoke test. No package installation, filesystem or networking. */
#include "core.h"
#include "sha256.h"
#include "zip.h"
#include "manifest.h"
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
    puts("PayloadForge native preflight: OK (read-only; not installer)");
    return 0;
}
