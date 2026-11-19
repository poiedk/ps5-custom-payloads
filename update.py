import json, os, re, urllib.request, urllib.error, pathlib, sys
from payload_icons import build_icons
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'payloads_v2.json'
def get(repo):
    headers = {'Accept':'application/vnd.github+json','User-Agent':'dk-custom-catalog','X-GitHub-Api-Version':'2022-11-28'}
    if os.getenv('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+repo+'/releases?per_page=30',headers=headers),timeout=30) as response:
        return json.load(response)
def get_codeberg(repo):
    url='https://codeberg.org/api/v1/repos/'+repo+'/releases?limit=30'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'dk-custom-catalog','Accept':'application/json'}),timeout=30) as response:
        return json.load(response)
def codeberg_digest(s,r,a):
    base='https://codeberg.org/'+s['repo']+'/releases/download/'
    for side in r['assets']:
        if side['name'].lower() not in (a['name'].lower()+'.sha256','sha256sums','sha256sums.txt'):
            continue
        url=side['browser_download_url']
        if not url.lower().startswith(base.lower()):
            raise ValueError('unexpected checksum URL')
        with urllib.request.urlopen(url,timeout=30) as response:
            raw=response.read(65537).decode('utf-8')
        for line in raw.splitlines():
            m=re.fullmatch(r'([a-fA-F0-9]{64})(?:\s+\*?(.+))?',line.strip())
            if m and ((not m[2] and side['name'].lower()==a['name'].lower()+'.sha256') or m[2]==a['name']):
                return 'sha256:'+m[1]
    return ''
def select(s, releases):
    for r in releases:
        if r['draft'] or (r['prerelease'] and not s.get('prerelease')):
            continue
        assets = [a for a in r['assets'] if re.fullmatch(s['pattern'],a['name'],re.I)]
        if len(assets)>1:
            raise ValueError('ambiguous assets')
        if not assets:
            continue
        a=assets[0]
        digest=a.get('digest') or (codeberg_digest(s,r,a) if s.get('provider')=='codeberg' else '')
        if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest):
            raise ValueError('missing upstream SHA-256 digest')
        url=a['browser_download_url']
        host='https://codeberg.org/' if s.get('provider')=='codeberg' else 'https://github.com/'
        if not url.lower().startswith((host+s['repo']+'/releases/download/').lower()):
            raise ValueError('unexpected download URL')
        return dict(id=s['id'],name=s['name'],filename=s['id']+'.elf',url=url,source_direct=url,version=r['tag_name'],last_update=r['published_at'][:10],category='Utilities & Tools',checksum=digest[7:].lower(),source=host+s['repo']+'/releases',description='Verify firmware compatibility before use.')
    raise ValueError('no matching release asset')
def write(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def main():
    previous={x['id']:x for x in json.loads(OUT.read_text())['payloads']} if OUT.exists() else {}
    results=[]; errors=[]
    archive_path=ROOT/'unavailable.json'
    archive=json.loads(archive_path.read_text()) if archive_path.exists() else {'schema_version':1,'payloads':[], 'icons':{}}
    retired={x['id']:x for x in archive['payloads']}
    missing=set()
    sources=json.loads((ROOT/'sources.json').read_text())
    for s in sources:
        try:
            getter=get_codeberg if s.get('provider')=='codeberg' else get
            try:
                releases=getter(s['repo'])
            except urllib.error.HTTPError as e:
                if e.code!=404: raise
                try:
                    releases=getter(s['repo'])
                except urllib.error.HTTPError as retry:
                    if retry.code==404: missing.add(s['id'])
                    raise
            results.append(select(s,releases))
            retired.pop(s['id'],None)
        except Exception as e:
            errors.append(s['id']+': '+str(e))
            if s['id'] in missing and s['id'] in previous:
                meta={k:v for k,v in previous[s['id']].items() if k not in ('url','source_direct')}
                retired[s['id']]={**meta,'availability':'source_unavailable','reason':'repeated_http_404','download_available':False,'notice':'Source unavailable (404). Installed copies are not removed.'}
            elif s['id'] in previous:
                results.append(previous[s['id']])
    for e in errors:
        print(e,file=sys.stderr)
    if not results and not retired:
        raise SystemExit('No qualifying assets; refusing to overwrite catalog')
    icon_path=ROOT/'icons.json'
    cached=json.loads(icon_path.read_text()).get('icons',{}) if icon_path.exists() else {}
    cached.update(archive.get('icons',{}))
    archive['payloads']=list(retired.values())
    archive['icons']={x['icon_key']:cached[x['icon_key']] for x in retired.values() if x.get('icon_key') in cached}
    write(archive_path,archive)
    icons,icon_report=build_icons(results,{s['id']:s for s in sources},cached,previous)
    write(ROOT/'icons.json',icons)
    write(OUT,{'name':'DK PS5 Custom Payloads','icons_url':'icons.json','payloads':results})
    write(ROOT/'payloads.json',results)
    write(ROOT/'status.json',{'warnings':errors,'icons':icon_report})
if __name__=='__main__':
    main()
