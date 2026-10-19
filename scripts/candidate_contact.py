import json
import sys
from PIL import Image, ImageOps, ImageDraw
from fetch_images import ROOT
dest=ROOT/'source'/(sys.argv[1] if len(sys.argv)>1 else 'image-candidates')
data=json.loads((dest/'candidates.json').read_text(encoding='utf-8'))
items=list(data.items())
for start in range(0,len(items),10):
    section=items[start:start+10]
    out=Image.new('RGB',(1000,190*len(section)),'white')
    draw=ImageDraw.Draw(out)
    for row,(key,photos) in enumerate(section):
        for col,item in enumerate(photos):
            from pathlib import Path
            if not Path(item['path']).exists(): continue
            out.paste(ImageOps.contain(Image.open(item['path']).convert('RGB'),(195,150)),(col*200,row*190))
            draw.text((col*200+3,row*190+152),f"{key} [{item['index']}]",fill='black')
            draw.text((col*200+3,row*190+165),item['title'][5:35],fill='black')
    out.save(dest/f'contact-{start//10}.jpg')
