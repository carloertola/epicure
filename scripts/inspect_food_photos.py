"""Build small candidate contact sheets from Commons food-photo searches."""
import concurrent.futures
import json
import pathlib
import re
from PIL import Image, ImageOps, ImageDraw
from fetch_images import api, request, COMMONS, ROOT

SEARCHES = {
 'teff':'teff grains', 'wheat':'wheat grains', 'emmer wheat':'emmer grains',
 'maize':'maize corn cob', 'millet':'millet grains', 'sorghum':'sorghum grains',
 'rice':'uncooked rice grains', 'quinoa':'quinoa seeds food',
 'noodles':'noodles food bowl', 'popcorn':'popped popcorn',
 'broad beans':'broad beans seeds food','pea':'green peas food',
 'soybean':'soybean seeds food','vetch (grass pea)':'Lathyrus sativus seeds',
 'sword bean':'sword bean seeds','groundnut (peanut)':'shelled peanuts',
 'sesame seed':'sesame seeds food','linseed':'flax seeds',
 'safflower seed':'safflower seeds','niger seed':'niger seeds food',
 'amaranthus':'amaranth leaves food','anchote':'anchote tubers',
 'bamboo shoot':'bamboo shoots food','cassava':'cassava roots',
 'garlic':'garlic bulbs','ginger':'ginger root',
 'leek':'leeks vegetable','taro':'taro roots',
 'custard apple':'custard apple fruit','fig':'fig fruit sliced',
 'date':'dried dates fruit','papaya':'papaya fruit sliced',
 'peach':'peaches fruit','tamarind':'tamarind pods',
 'cloves':'dried cloves spice','coriander':'coriander seeds spice',
 'fenugreek':'fenugreek seeds','pepper':'black peppercorns',
 'oregano':'dried oregano spice','turmeric':'turmeric powder roots',
 "bishop's weed":'ajwain seeds','calf (veal)':'raw veal meat',
 'camel meat':'camel meat food','tella':'tella beer glass',
 'sugar (cane)':'white sugar crystals','sugar cane':'sugarcane stalks',
 'salt':'table salt spoon','yeast':'bakers yeast fresh',
 'spice paste from green chilli':'green chili paste',
 'nuts':'mixed edible nuts','prickly pear':'prickly pear fruit',
 'sardine':'fresh sardines fish','fish oil':'fish oil bottle',
 'spice paste from chili':'awaze sauce',
}
DEST=ROOT/'source/image-candidates'
DEST.mkdir(exist_ok=True)

def search(item):
    key,query=item
    result=api(COMMONS,generator='search',gsrsearch=query+' filetype:bitmap',gsrnamespace=6,gsrlimit=5,prop='imageinfo',iiprop='extmetadata|url',iiurlwidth=320)
    pages=sorted(result.get('query',{}).get('pages',{}).values(),key=lambda x:x.get('index',99))
    found=[]
    for i,p in enumerate(pages):
        ii=p.get('imageinfo',[{}])[0]
        if not ii.get('thumburl'): continue
        path=DEST/(re.sub('[^a-z0-9]','-',key)+f'-{i}.jpg')
        try:
            if not path.exists(): path.write_bytes(request(ii['thumburl'],binary=True))
            found.append({'index':i,'path':str(path),'title':p['title'],'info':ii})
        except Exception: pass
    return key,found

if __name__=='__main__':
    data={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for key,found in pool.map(search,SEARCHES.items()):
            data[key]=found
            (DEST/'candidates.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            print(key,json.dumps([v['title'] for v in found],ensure_ascii=True),flush=True)
    (DEST/'candidates.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    canvas=Image.new('RGB',(1000,190*len(data)),'white')
    draw=ImageDraw.Draw(canvas)
    for row,(key,items) in enumerate(data.items()):
        for col,item in enumerate(items):
            img=ImageOps.contain(Image.open(item['path']).convert('RGB'),(195,150))
            canvas.paste(img,(col*200,row*190))
            draw.text((col*200+3,row*190+152),f"{key} [{item['index']}]",fill='black')
            draw.text((col*200+3,row*190+165),item['title'][5:35],fill='black')
    canvas.save(DEST/'candidates.jpg')
