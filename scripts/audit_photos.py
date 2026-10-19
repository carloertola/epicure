import json
import pathlib
from PIL import Image, ImageOps, ImageDraw

root = pathlib.Path(__file__).resolve().parents[1]
data = json.loads((root/'public/data/images.json').read_text(encoding='utf-8'))
items = [(k,v) for k,v in data.items() if not v.get('missing')]
for offset in range(0,len(items),50):
    chunk = items[offset:offset+50]
    out = Image.new('RGB',(1000,170*((len(chunk)+4)//5)),'white')
    draw = ImageDraw.Draw(out)
    for i,(k,v) in enumerate(chunk):
        photo = Image.open(root/'public'/v['src'].lstrip('/')).convert('RGB')
        out.paste(ImageOps.contain(photo,(196,140)),((i%5)*200,(i//5)*170))
        draw.text(((i%5)*200+3,(i//5)*170+145),k[:28],fill='black')
    out.save(root/f'source/contact-{offset//50}.jpg')
