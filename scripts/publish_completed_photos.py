"""Publish reviewed source photos and explicit generated/ingredient references."""
import json
import pathlib
import re
import shutil
from fetch_images import ROOT, clean_html

path = ROOT / 'public/data/images.json'
images = json.loads(path.read_text(encoding='utf-8'))
candidates = json.loads((ROOT/'tmp/food-photo-review/candidates.json').read_text(encoding='utf-8'))
foods = json.loads((ROOT/'public/data/foods.json').read_text(encoding='utf-8'))['foods']

def publish(key, index, slug, alt, fit='cover'):
    item = candidates[key][index]
    target = ROOT/'public/images/foods'/(slug+'-reference.jpg')
    shutil.copyfile(item['path'], target)
    ii = item['info']
    meta = ii['extmetadata']
    return {'src': '/images/foods/'+target.name, 'alt': alt,
            'source': ii['descriptionurl'],
            'license': clean_html(meta['LicenseShortName']['value']),
            'licenseUrl': meta.get('LicenseUrl', {}).get('value', ''),
            'credit': clean_html(meta.get('Artist', {}).get('value', 'Wikimedia Commons contributor')),
            'description': clean_html(meta.get('ImageDescription', {}).get('value', ''))[:700],
            'illustrative': True, 'visuallyVerified': True, 'fit': fit}

def generated(slug, alt):
    return {'src': '/images/foods/'+slug+'-illustration.png', 'alt': alt,
            'source': 'data/image-illustrations.html#'+slug,
            'license': 'Project-generated illustration',
            'licenseUrl': 'data/image-illustrations.html#usage',
            'credit': 'Generated for Gursha with OpenAI ImageGen',
            'description': 'AI-generated culinary illustration, not a photograph or a species-identification guide.',
            'illustrative': True, 'generated': True, 'visuallyVerified': True, 'fit': 'contain'}

images['custard apple'] = publish('custard apple', 0, 'custard-apple', 'Custard apple, whole and cut open — fruit-family reference')
images['prickly pear'] = publish('prickly-fruit', 2, 'prickly-pear', 'Cut prickly pear fruit with magenta pulp — fruit-family reference')
images['calf (veal)'] = generated('veal', 'Raw veal cutlets — AI-generated ingredient illustration')
images['camel meat'] = publish('camel-final', 0, 'camel-meat', 'Camel meat — illustrative ingredient photograph')
images['fish oil'] = publish('fish oil', 0, 'cod-liver-oil', 'Cod liver oil bottle — illustrative product reference', 'contain')
images['tella'] = publish('tella-drink', 1, 'tella', 'Tella in a drinking cup — illustrative cereal-based fermented beverage photograph')
images['gin (47.9% v/v alcohol)'] = publish('gin-bottle', 2, 'gin', 'Gin bottle — category reference, not the recorded brand or alcohol strength', 'contain')
images['vermouth'] = publish('vermouth', 0, 'vermouth', 'Vermouth bottle — category reference, not the specific sweet/dry variant or alcohol strength', 'contain')
images['vodka or whisky (37.1% v/v alcohol)'] = publish('spirits', 0, 'whisky', 'Whisky in a tasting glass — category reference for this vodka-or-whisky entry', 'contain')
images['sugar cane'] = publish('sugar cane', 1, 'sugarcane-juice', 'Glass of sugarcane juice — illustrative beverage photograph')
images['spice paste from green chilli'] = publish('green-sauce', 0, 'green-chilli-paste', 'Green chilli paste (sambal ijo) — paste-family reference, not this exact recipe')
images['spice paste from chili'] = publish('red-paste', 0, 'red-chilli-paste', 'Red chilli paste (sambal rica) — paste-family reference, not this exact recipe')

# The table specifies only "cereal based" for these recipes. Show a labeled
# beverage-family reference rather than claiming an unrelated stock recipe.
for key in ['abara', 'borde', 'cheka', 'korefe', 'shamita']:
    images[key] = {**images['tella'], 'alt': 'Cereal-based fermented beverage reference (tella); not a photograph of this specific '+key+' recipe', 'recipeIllustration': True}
for key, ingredient in [('juice from husked', 'barley'), ('soup from flaked oats with water', 'oats')]:
    images[key] = {**images[ingredient], 'alt': 'Illustrative '+ingredient+' ingredient; not a photograph of this specific drink or soup', 'illustratedIngredient': ingredient, 'recipeIllustration': True}

organs = {
    'brain': generated('veal-brain', 'Calf brain — AI-generated culinary ingredient illustration'),
    'heart': publish('heart-final', 0, 'veal-heart', 'Calf heart — organ-family ingredient reference'),
    'kidney': generated('veal-kidney', 'Calf kidney with its lobulated shape — AI-generated ingredient illustration'),
    'liver': publish('liver', 0, 'veal-liver', 'Raw veal liver — organ-family ingredient reference'),
    'tongue': generated('veal-tongue', 'Calf tongue — AI-generated culinary ingredient illustration'),
    'tripe': publish('tripe', 0, 'tripe', 'Raw tripe with its folded honeycomb texture — organ-family reference'),
}
for food in foods:
    if food['baseName'] == 'calf (veal)':
        for part, picture in organs.items():
            if re.search(r'\b'+part+r'\b', food['name'], re.I):
                images.setdefault('byFoodId', {})[food['id']] = picture
                break

for food in foods:
    pic = images.get('byFoodId', {}).get(food['id']) or images.get(food['baseName'], {})
    assert pic.get('src'), food['name']
    assert (ROOT/'public'/pic['src'].lstrip('/')).is_file(), pic['src']
path.write_text(json.dumps(images, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
auditpath = ROOT/'public/data/image-audit.json'
audit = json.loads(auditpath.read_text(encoding='utf-8'))
audit.update(covered=len(foods), missing=[], missingCount=0,
             baseKeysWithPhotos=sum(bool(p.get('src')) for p in images.values()),
             note='Every food has a local image reference. Photographs and AI-generated illustrations show ingredient families, not exact recipes, varieties, preparation states or identification evidence. Recipe/ingredient aliases and generated pictures are explicitly labeled in the food detail and credits.')
auditpath.write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'Covered {len(foods)}/{len(foods)} food entries. No missing pictures.')
