"""Collect Commons candidates for the everyday ingredient photo gaps."""
import concurrent.futures
import json
import pathlib
import re
import sys
import hashlib
from fetch_images import api, request, COMMONS, ROOT
from PIL import Image, ImageOps, ImageDraw

QUERIES={
 'garlic':'intitle:garlic intitle:bulb',
 'ginger':'intitle:ginger intitle:root',
 'cassava':'intitle:cassava intitle:roots',
 'sesame seed':'intitle:sesame intitle:seeds',
 'linseed':'intitle:flax intitle:seeds',
 'papaya':'intitle:papaya intitle:cut',
 'fig':'intitle:fig intitle:fruit',
 'peach':'intitle:peach intitle:cross',
 'cloves':'intitle:cloves spice',
 'coriander':'intitle:coriander intitle:seeds',
 'fenugreek':'intitle:fenugreek intitle:seeds',
 'salt':'intitle:"table salt" -intitle:electron -intitle:lake -intitle:single',
 'yeast':'intitle:yeast intitle:instant',
 'sugar (cane)':'intitle:sugar intitle:granulated',
 'nuts':'intitle:nuts intitle:mixed',
 'sardine':'intitle:sardines intitle:canned',
 'pepper black':'intitle:black intitle:peppercorns',
 'pepper long':'intitle:long intitle:pepper',
 'pepper red powder':'intitle:paprika intitle:powder',
}
DEST=ROOT/'source/gap-candidates'
DEST.mkdir(exist_ok=True)
def search(item):
    key,query=item
    result=api(COMMONS,generator='search',gsrsearch=query+' filetype:bitmap',gsrnamespace=6,gsrlimit=4,prop='imageinfo',iiprop='extmetadata|url',iiurlwidth=480)
    found=[]
    for p in sorted(result.get('query',{}).get('pages',{}).values(),key=lambda x:x.get('index',99)):
        ii=p.get('imageinfo',[{}])[0]
        if not ii.get('thumburl') or not ii.get('extmetadata',{}).get('LicenseShortName'): continue
        ix=len(found)
        digest=hashlib.sha256(p['title'].encode()).hexdigest()[:7]
        found.append({'index':ix,'key':key,'title':p['title'],'info':ii,'path':str(DEST/(re.sub(r'[^a-z0-9]+','-',key).strip('-')+f'-{ix}-{digest}.jpg'))})
    print(key,json.dumps([v['title'] for v in found],ensure_ascii=True),flush=True)
    return key,found
def download(item):
    path=pathlib.Path(item['path'])
    if not path.exists(): path.write_bytes(request(item['info']['thumburl'],binary=True))
    return item

if __name__=='__main__':
    if len(sys.argv)>1:
        selected=sys.argv[1:]
        QUERIES={k:v for k,v in QUERIES.items() if k in selected}
        data=json.loads((DEST/'candidates.json').read_text(encoding='utf-8'))
    else:
        data={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures=[pool.submit(search,item) for item in QUERIES.items()]
        for future in concurrent.futures.as_completed(futures):
            key,found=future.result(); data[key]=found
            (DEST/'candidates.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    items=[v for key in QUERIES for v in data[key]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures=[pool.submit(download,item) for item in items]
        for future in concurrent.futures.as_completed(futures):
            try: future.result()
            except Exception as exc: print('Download failed',str(exc)[:120],flush=True)
    for offset in range(0,len(QUERIES),8):
        keys=list(QUERIES)[offset:offset+8]
        out=Image.new('RGB',(1000,len(keys)*190),'white'); draw=ImageDraw.Draw(out)
        for row,key in enumerate(keys):
            for col,item in enumerate(data[key]):
                if not pathlib.Path(item['path']).exists(): continue
                try: im=ImageOps.contain(Image.open(item['path']).convert('RGB'),(245,150))
                except Exception: continue
                out.paste(im,(col*250,row*190))
                draw.text((col*250+3,row*190+152),f"{key} [{item['index']}]",fill='black')
                draw.text((col*250+3,row*190+165),item['title'][5:40],fill='black')
        out.save(DEST/f'contact-{offset//8}.jpg')
