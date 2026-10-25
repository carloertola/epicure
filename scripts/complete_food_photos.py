"""Collect licensed candidates for review; publication is an explicit second step."""
import concurrent.futures
import json
import pathlib
import re
import sys
from PIL import Image, ImageDraw, ImageOps
from fetch_images import ROOT, COMMONS, api, request

DEST = ROOT / 'tmp/food-photo-review'
DEST.mkdir(parents=True, exist_ok=True)
QUERIES = {
    'custard apple': 'intitle:Custard-Apple-Cherimoya',
    'prickly pear': 'intitle:prickly intitle:pear fruit cut',
    'veal': 'intitle:veal meat raw',
    'brain': 'intitle:calf intitle:brain food',
    'heart': 'intitle:heart beef raw',
    'kidney': 'intitle:veal intitle:kidney',
    'liver': 'intitle:veal intitle:liver',
    'tongue': 'intitle:beef intitle:tongue raw',
    'tripe': 'intitle:tripe raw',
    'camel meat': 'intitle:camel intitle:meat',
    'fish oil': 'intitle:cod intitle:liver intitle:oil',
    'tella': 'intitle:tella',
    'borde': 'intitle:borde drink',
    'cheka': 'intitle:cheka drink',
    'korefe': 'intitle:korefe',
    'shamita': 'intitle:shamita',
    'abara': 'intitle:abara drink',
    'gin': 'intitle:gin glass drink -intitle:cocktail -intitle:tonic',
    'vermouth': 'intitle:vermouth glass',
    'spirits': 'intitle:whisky intitle:glass',
    'sugar cane': 'intitle:sugarcane intitle:juice glass',
    'green chilli paste': 'intitle:green intitle:chili sauce',
    'red chilli paste': 'intitle:awaze',
}

def collect(item):
    key, query = item
    result = api(COMMONS, generator='search', gsrsearch=query+' filetype:bitmap',
                 gsrnamespace=6, gsrlimit=3, prop='imageinfo',
                 iiprop='extmetadata|url', iiurlwidth=480)
    found = []
    for p in sorted(result.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 99)):
        ii = p.get('imageinfo', [{}])[0]
        if not ii.get('thumburl') or not ii.get('extmetadata', {}).get('LicenseShortName'):
            continue
        path = DEST / (re.sub(r'[^a-z0-9]+', '-', key)+f'-{len(found)}.jpg')
        try:
            if not path.exists():
                path.write_bytes(request(ii['thumburl'], binary=True))
            Image.open(path).verify()
        except Exception as exc:
            print('Failed', key, str(exc)[:120], flush=True)
            continue
        found.append({'title': p['title'], 'info': ii, 'path': str(path)})
    print(key, json.dumps([p['title'] for p in found], ensure_ascii=True), flush=True)
    return key, found

def contacts(data):
    keys = [key for key in data if data[key]]
    for offset in range(0, len(keys), 7):
        chunk = keys[offset:offset+7]
        out = Image.new('RGB', (900, 180*len(chunk)), 'white')
        draw = ImageDraw.Draw(out)
        for row, key in enumerate(chunk):
            for col, item in enumerate(data[key]):
                pic = ImageOps.contain(Image.open(item['path']).convert('RGB'), (290, 140))
                out.paste(pic, (col*300, row*180))
                draw.text((col*300+3, row*180+142), f'{key} [{col}]', fill='black')
                draw.text((col*300+3, row*180+158), item['title'][5:47], fill='black')
        out.save(DEST / f'contact-{offset//7}.jpg')

if __name__ == '__main__':
    file = DEST / 'candidates.json'
    data = json.loads(file.read_text(encoding='utf-8')) if file.exists() else {}
    pending = [(k, q) for k, q in QUERIES.items() if k not in data]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for key, found in pool.map(collect, pending):
            data[key] = found
            file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    contacts(data)
