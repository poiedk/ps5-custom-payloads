import json, os, re, urllib.request, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'payloads_v2.json'
def get(repo):
    headers = {'Accept':'application/vnd.github+json','User-Agent':'dk-custom-catalog','X-GitHub-Api-Version':'2022-11-28'}
    if os.getenv('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+repo+'/releases?per_page=30',headers=headers),timeout=30) as response:
        return json.load(response)
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
        digest=a.get('digest') or ''
        if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest):
            raise ValueError('missing upstream SHA-256 digest')
        url=a['browser_download_url']
        if not url.lower().startswith(('https://github.com/'+s['repo']+'/releases/download/').lower()):
            raise ValueError('unexpected download URL')
        return dict(id=s['id'],name=s['name'],filename=s['id']+'.elf',url=url,source_direct=url,version=r['tag_name'],last_update=r['published_at'][:10],category='Utilities & Tools',checksum=digest[7:].lower(),source='https://github.com/'+s['repo']+'/releases',description='Verify firmware compatibility before use.')
    raise ValueError('no matching release asset')
def write(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def main():
    previous={x['id']:x for x in json.loads(OUT.read_text())['payloads']} if OUT.exists() else {}
    results=[]; errors=[]
    for s in json.loads((ROOT/'sources.json').read_text()):
        try:
            results.append(select(s,get(s['repo'])))
        except Exception as e:
            errors.append(s['id']+': '+str(e))
            if s['id'] in previous:
                results.append(previous[s['id']])
    for e in errors:
        print(e,file=sys.stderr)
    if not results:
        raise SystemExit('No qualifying assets; refusing to overwrite catalog')
    write(OUT,{'name':'DK PS5 Custom Payloads','payloads':results})
    write(ROOT/'payloads.json',results)
    write(ROOT/'status.json',{'warnings':errors})
if __name__=='__main__':
    main()
