/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "version.h"
#include <stddef.h>
#include <string.h>
typedef struct{const char *p;size_t n;} span;
typedef struct{span core[3],pre[32];size_t count;} version;
static int digit(char c){return c>='0'&&c<='9';}
static int valid(char c){return digit(c)||(c>='a'&&c<='z')||(c>='A'&&c<='Z')||c=='-';}
static int numeric(span s){for(size_t i=0;i<s.n;i++)if(!digit(s.p[i]))return 0;return s.n!=0;}
static int number_ok(span s){return numeric(s)&&(s.n==1||s.p[0]!='0');}
static int cmp_num(span a,span b){
 if(a.n!=b.n)return a.n>b.n?1:-1;
 int k=memcmp(a.p,b.p,a.n);return k>0?1:k<0?-1:0;
}
static int cmp_str(span a,span b){
 size_t n=a.n<b.n?a.n:b.n;int k=memcmp(a.p,b.p,n);
 if(k)return k>0?1:-1;
 return a.n>b.n?1:a.n<b.n?-1:0;
}
static int parse(const char *s,version *v){
 if(!s||!strlen(s)||strlen(s)>64)return -1;
 memset(v,0,sizeof(*v));for(int i=0;i<3;i++)v->core[i]=(span){"0",1};
 if(*s=='v'||*s=='V')s++;
 for(int i=0;i<3;i++){
  const char *start=s;while(digit(*s))s++;
  span x={start,(size_t)(s-start)};if(!number_ok(x))return -1;
  v->core[i]=x;if(*s!='.')break;if(i==2)return -1;s++;
 }
 if(*s=='-'){
  s++;for(;;){
   const char *start=s;while(valid(*s))s++;
   span x={start,(size_t)(s-start)};
   if(!x.n||v->count>=32||(numeric(x)&&!number_ok(x)))return -1;
   v->pre[v->count++]=x;if(*s!='.')break;s++;
  }
 }
 if(*s=='+'){
  s++;for(;;){const char *start=s;while(valid(*s))s++;if(s==start)return -1;if(*s!='.')break;s++;}
 }
 return *s?-1:0;
}
int pf_version_compare(const char *left,const char *right,int *result){
 if(!result)return -1;
 *result=0;version a,b;if(parse(left,&a)||parse(right,&b))return -1;
 for(int i=0;i<3;i++){int k=cmp_num(a.core[i],b.core[i]);if(k){*result=k;return 0;}}
 if(!a.count||!b.count){*result=a.count==b.count?0:a.count?-1:1;return 0;}
 size_t n=a.count<b.count?a.count:b.count;
 for(size_t i=0;i<n;i++){
  int an=numeric(a.pre[i]),bn=numeric(b.pre[i]);
  int k=an!=bn?(an?-1:1):an?cmp_num(a.pre[i],b.pre[i]):cmp_str(a.pre[i],b.pre[i]);
  if(k){*result=k;return 0;}
 }
 *result=a.count>b.count?1:a.count<b.count?-1:0;return 0;
}
