/* Read-only native smoke test. No package installation, filesystem or networking. */
#include "core.h"
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
    puts("PayloadForge native preflight: OK (read-only; not installer)");
    return 0;
}
