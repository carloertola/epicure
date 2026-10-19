"""Apply visually inspected photo choices, honest labels, and ingredient aliases."""
import json
import pathlib
import re
import shutil
from fetch_images import ROOT, clean_html

path=ROOT/'public/data/images.json'
images=json.loads(path.read_text(encoding='utf-8'))
candidates_path=ROOT/'source/image-candidates/candidates.json'
candidates=json.loads(candidates_path.read_text(encoding='utf-8')) if candidates_path.exists() else {}
choices={'teff':3,'emmer wheat':0,'maize':0,'millet':0,'sorghum':2,'rice':2,'quinoa':0,'noodles':0,'popcorn':0,'broad beans':1,'pea':2,'vetch (grass pea)':0,'groundnut (peanut)':0}
for key,choice in choices.items():
    item=next((x for x in candidates.get(key,[]) if x['index']==choice),None)
    if not item: continue
    ii=item['info']; meta=ii.get('extmetadata',{})
    target=ROOT/'public/images/foods'/(re.sub(r'[^a-z0-9]+','-',key).strip('-')+'-food.jpg')
    shutil.copyfile(item['path'],target)
    images[key]={
        'src':'/images/foods/'+target.name,'alt':key.capitalize()+' — illustrative ingredient photograph',
        'source':ii['descriptionurl'],'license':clean_html(meta.get('LicenseShortName',{}).get('value','')),
        'licenseUrl':meta.get('LicenseUrl',{}).get('value',''),
        'credit':clean_html(meta.get('Artist',{}).get('value','Wikimedia Commons contributor')),
        'description':clean_html(meta.get('ImageDescription',{}).get('value',''))[:700],
        'illustrative':True,'imageKind':'ingredient',
    }

# Do not use a live animal, microscopy, botanical plate, wrong dish, or rock
# as an ingredient identification photograph. Missing images stay explicit.
unavailable=['calf (veal)','camel meat','tella','sugar (cane)','sugar cane','salt','yeast',
 'spice paste from green chilli','maize' if 'maize' not in choices else '',
 'sesame seed','linseed','groundnut (peanut)' if 'groundnut (peanut)' not in choices else '',
 'cassava','garlic','ginger','custard apple','fig','papaya','peach','cloves','coriander',
 'fenugreek','pepper']
for key in unavailable:
    if key and key in images:
        images[key]={'missing':True,'reason':'Edible-part photograph awaiting visual verification','illustrative':True}

aliases={'maize (corn)':'maize','sheep (mutton)':'sheep','chickpeas':'chickpea','chilli':'chili',
 'pasta (macaroni or spaghetti)':'pasta','goat meat':'goat','bamboo shoots':'bamboo shoot',
 'pasta (boiled)':'pasta'}
foods=json.loads((ROOT/'public/data/foods.json').read_text(encoding='utf-8'))['foods']
recipe_words=[('enjera','enjera'),('anchote','anchote'),('false banana','false banana'),
 ('potato','potato'),('green beans','green beans'),('cabbage','cabbage'),('avocado','avocado'),
 ('barley','barley'),('teff','teff'),('sorghum','sorghum'),('millet','millet'),('maize','maize'),
 ('wheat','wheat'),('tomato','tomato'),('lentil','lentil'),('kidney bean','kidney bean'),
 ('kale','kale'),('coffee','coffee'),('tea infusion','tea'),('honey','honey'),
 ('samosa','samosa from baked refined wheat flour'),('red pepper','spices'),
 ('soup from fish','fish'),('soup from goat','goat'),('soup from sheep','sheep'),
 ('cottage cheese','cheese'),('okra','okra'),('pasta','pasta'),('cookies','biscuit')]
for food in foods:
    key=food['baseName']
    if key in images: continue
    target=aliases.get(key)
    is_recipe=not bool(target)
    if not target:
        target=next((image for word,image in recipe_words if word in key),None)
    if target and target in images and not images[target].get('missing'):
        images[key]={**images[target],'illustratedIngredient':target,
            'alt':f'Illustrative {target} ingredient; not a photograph of this specific dish' if is_recipe else images[target]['alt'],
            'recipeIllustration':is_recipe}

images['hero']={**images['enjera'],'alt':'Injera with an assortment of Ethiopian dishes'}
path.write_text(json.dumps(images,ensure_ascii=False,indent=2),encoding='utf-8')
missing=[{'id':f['id'],'name':f['name'],'baseName':f['baseName']} for f in foods if f['baseName'] not in images or images[f['baseName']].get('missing')]
audit={'entries':len(foods),'covered':len(foods)-len(missing),'missing':missing,
 'note':'Photos are illustrative ingredient families; prepared-dish aliases explicitly depict an ingredient, not the recipe. Plant photos may depict the crop. Photos do not confirm cultivar, harvest maturity, edible species or preparation state.',
 'baseKeysWithPhotos':sum(not v.get('missing') for v in images.values()),
 'visuallyReplacedLeads':list(choices)}
(ROOT/'public/data/image-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in audit.items() if k!='missing'}))
