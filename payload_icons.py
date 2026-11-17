import base64, hashlib, io, json, os, re, urllib.request
from urllib.parse import quote
from pathlib import PurePosixPath
from PIL import Image, ImageDraw, ImageFont
Image.MAX_IMAGE_PIXELS = 16000000
LIMIT = 3*1024*1024

def fetch(url, api=False):
    headers={'User-Agent':'dk-custom-catalog'}
    if api and url.startswith('https://api.github.com/') and os.getenv('GITHUB_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=15) as response:
        data=response.read(LIMIT+1)
    if len(data)>LIMIT:
        raise ValueError('image or metadata too large')
    return data

def official(s):
    repo=s['repo']
    cb=s.get('provider')=='codeberg'
    api=('https://codeberg.org/api/v1/repos/' if cb else 'https://api.github.com/repos/')+repo
    branch=json.loads(fetch(api,True))['default_branch']
    tree=json.loads(fetch(api+'/git/trees/'+quote(branch,safe='')+'?recursive=1',True))
    candidates=[]
    for item in tree.get('tree',[]):
        p=item.get('path','')
        if item.get('type')!='blob' or item.get('size',0)>LIMIT:
            continue
        path=PurePosixPath(p)
        if path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp','.ico'):
            continue
        if any(x.lower() in ('vendor','third_party','node_modules','dependencies','screenshots','examples','tests','lib','libs') for x in path.parts[:-1]):
            continue
        stem=path.stem.lower()
        if not re.search(r'(^|[-_ ])(logo|icon|icon0|appicon|favicon)([-_ ]|$)',stem):
            continue
        score=0 if 'logo' in stem else 1 if stem in ('icon','icon0','appicon') else 2
        candidates.append((score,len(path.parts),p))
    for _,__,p in sorted(candidates)[:5]:
        url=('https://codeberg.org/'+repo+'/raw/branch/' if cb else 'https://raw.githubusercontent.com/'+repo+'/')+quote(branch,safe='')+'/'+quote(p,safe='/')
        try:
            with Image.open(io.BytesIO(fetch(url))) as im:
                im=im.convert('RGBA')
                if min(im.size)<24: continue
                im.thumbnail((116,116),Image.Resampling.LANCZOS)
                canvas=Image.new('RGBA',(128,128),(0,0,0,0))
                canvas.alpha_composite(im,((128-im.width)//2,(128-im.height)//2))
                return canvas,url
        except Exception:
            continue
    raise ValueError('no eligible upstream logo')

def custom(s):
    palette=['#155E75','#4338CA','#9D174D','#166534','#92400E','#374151','#6D28D9','#075985']
    digest=hashlib.sha256(s['id'].encode()).digest()
    im=Image.new('RGBA',(128,128),(0,0,0,0))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((3,3,124,124),radius=27,fill=palette[digest[0]%len(palette)])
    d.rounded_rectangle((9,9,118,118),radius=22,outline='#FFFFFF55',width=2)
    aliases={'kraken-mount':'KM','shadowkraken':'SK','alembic':'AL','prosperomgr':'PM','hearbridge':'HB','omnipad-ce':'CE','omnipad':'OP','lz4-compression':'LZ4','glm':'GLM','ghosttoothapi':'GT','anypad':'AP'}
    label=aliases.get(s['id'],s['name'][:2].upper())
    try: font=ImageFont.truetype('DejaVuSans-Bold.ttf',43 if len(label)>2 else 50)
    except OSError: font=ImageFont.load_default(size=40)
    d.text((64,61),label,font=font,anchor='mm',fill='white')
    return im

def bounded_png(im):
    for size in (128,112,96,80,64,48,32):
        canvas=im.copy()
        canvas.thumbnail((size,size),Image.Resampling.LANCZOS)
        for colors in (256,128,64,32,16):
            buf=io.BytesIO()
            canvas.quantize(colors=colors,method=Image.Quantize.FASTOCTREE).save(buf,format='PNG',optimize=True)
            data=buf.getvalue()
            if len('data:image/png;base64,')+4*((len(data)+2)//3)<=12288:
                return data
    raise ValueError('icon cannot fit PLDMGR limit')

def build_icons(results,sources):
    icons={}; report={}
    for entry in results:
        s=sources[entry['id']]
        try:
            im,source=official(s)
            report[s['id']]={'type':'upstream','url':source}
        except Exception as e:
            im=custom(s)
            report[s['id']]={'type':'custom','reason':str(e)}
        data=bounded_png(im)
        key=hashlib.sha256(data).hexdigest()
        icons[key]='data:image/png;base64,'+base64.b64encode(data).decode('ascii')
        entry['icon_key']=key
    return {'icons':icons},report
