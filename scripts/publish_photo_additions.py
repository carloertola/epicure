"""Publish only visually reviewed candidates; never mutate the shared catalog."""
import json
import pathlib
import re
import shutil
from fetch_images import ROOT, clean_html

CHOICES={
 'garlic':0,'ginger':0,'cassava':2,'sesame seed':0,'linseed':0,
 'fig':0,'cloves':3,'coriander':0,'fenugreek':3,'nuts':0,
 'pepper black':2,'pepper long':0,'pepper red powder':0,
 'papaya':1,'peach':3,'salt':1,'yeast':1,'sugar (cane)':0,'sardine':0,
}
data=json.loads((ROOT/'source/gap-candidates/candidates.json').read_text(encoding='utf-8'))
out={'images':{},'byFoodId':{}}
def publish(key,index):
    item=next(v for v in data[key] if v['index']==index)
    source=pathlib.Path(item['path'])
    if not source.exists(): raise ValueError(f'Missing downloaded file: {source}')
    slug=re.sub(r'[^a-z0-9]+','-',key).strip('-')
    target=ROOT/'public/images/foods'/(slug+'-verified.jpg')
    shutil.copyfile(source,target)
    ii=item['info']; meta=ii.get('extmetadata',{})
    return {'src':'/images/foods/'+target.name,
        'alt':key.capitalize()+' — illustrative ingredient photograph',
        'source':ii['descriptionurl'],
        'license':clean_html(meta.get('LicenseShortName',{}).get('value','')),
        'licenseUrl':meta.get('LicenseUrl',{}).get('value',''),
        'credit':clean_html(meta.get('Artist',{}).get('value','Wikimedia Commons contributor')),
        'description':clean_html(meta.get('ImageDescription',{}).get('value',''))[:700],
        'illustrative':True,'imageKind':'ingredient','visuallyVerified':True}
published={key:publish(key,idx) for key,idx in CHOICES.items()}
published['yeast']['alt']='Instant dry yeast package — illustrative ingredient product photograph'
published['yeast']['imageKind']='ingredient-package'
published['sardine']['alt']='Opened canned sardines with lemon — illustrative ingredient photograph'
published['sugar (cane)']['alt']='Refined white sugar crystals — illustrative ingredient photograph'
for key,value in published.items():
    if not key.startswith('pepper '): out['images'][key]=value
images=json.loads((ROOT/'public/data/images.json').read_text(encoding='utf-8'))
sweet={**images['green peppers'],'alt':'Sweet bell peppers in several colors — illustrative ingredient photograph'}
out['byFoodId']['040021']=sweet
out['byFoodId']['040022']=sweet
out['byFoodId']['140002']=published['pepper black']
out['byFoodId']['140046']={**published['pepper long'],
 'alt':'Long pepper at left alongside other peppercorns — illustrative ingredient photograph'}
out['byFoodId']['140007']=published['pepper red powder']
out['images']['pepper']={'missing':True,
 'reason':'Ambiguous family name; use food-specific sweet, black, long or powdered pepper image',
 'illustrative':True}
(ROOT/'public/data/image-additions.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
foods=json.loads((ROOT/'public/data/foods.json').read_text(encoding='utf-8'))['foods']
combined={**images,**out['images']}
byid={**images.get('byFoodId',{}),**out['byFoodId']}
covered=sum(bool((byid.get(f['id']) or combined.get(f['baseName']) or {}).get('src')) for f in foods)
print(json.dumps({'newBasePhotos':len(out['images'])-1,'foodSpecificOverrides':len(out['byFoodId']),'coveredAfterMerge':covered,'total':len(foods)}))
