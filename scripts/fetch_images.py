"""Fetch illustrative ingredient photographs with Wikimedia attribution metadata.

Source images are selected from the named Wikipedia food article and checked
against Commons license metadata. Images illustrate a family, not a cultivar,
preparation state, or a sufficient basis for identifying unfamiliar wild foods.
"""
import concurrent.futures
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / 'public/images/foods'
DATA = ROOT / 'public/data/images.json'
DEST.mkdir(parents=True, exist_ok=True)
UA = 'Epicure/1.0 (educational food composition explorer; https://carloertola.com)'
API = 'https://en.wikipedia.org/w/api.php'
COMMONS = 'https://commons.wikimedia.org/w/api.php'

# These are explicit food-article names, not generated image URLs.
ARTICLES = {
 'barley':'Pearl barley','teff':'Teff','wheat':'Wheat','emmer wheat':'Emmer',
 'maize':'Maize','oats':'Rolled oats','millet':'Millet','sorghum':'Sorghum',
 'rice':'Rice','quinoa':'Quinoa','bread':'Bread','enjera':'Injera',
 'pasta':'Pasta','noodles':'Noodle','popcorn':'Popcorn','breakfast cereal':'Breakfast cereal',
 'lentil':'Lentil','chickpea':'Chickpea','broad beans':'Vicia faba',
 'field peas':'Split pea','pea':'Pea','kidney bean':'Kidney bean',
 'haricot (white) bean':'Navy bean','soybean':'Soybean','lupine':'Lupin bean',
 'vetch (grass pea)':'Lathyrus sativus','sword bean':'Canavalia gladiata',
 'groundnut (peanut)':'Peanut','sesame seed':'Sesame','linseed':'Flaxseed',
 'pumpkin seed':'Pumpkin seed','safflower seed':'Safflower','niger seed':'Guizotia abyssinica',
 'nuts':'Nut (fruit)','amaranthus':'Amaranth','anchote':'Coccinia abyssinica',
 'bamboo shoot':'Bamboo shoot','beetroot':'Beetroot','broccoli':'Broccoli',
 'cabbage':'Cabbage','carrot':'Carrot','cassava':'Cassava','cauliflower':'Cauliflower',
 'celery':'Celery','cucumber':'Cucumber','eggplant':'Eggplant','false banana':'Ensete ventricosum',
 'garlic':'Garlic','ginger':'Ginger','green beans':'Green bean','green onion':'Scallion',
 'green peppers':'Bell pepper','kale':'Kale','ethiopian kale':'Brassica carinata',
 'leek':'Leek','lettuce':'Lettuce','moringa':'Moringa oleifera','mushrooms':'Edible mushroom',
 'okra':'Okra','onion':'Onion','potato':'Potato','pumpkin':'Pumpkin','raddish':'Radish',
 'spinach':'Spinach','squash':'Squash (plant)','sweet potato':'Sweet potato','swiss chard':'Chard',
 'taro':'Taro','tomato':'Tomato','yam':'Yam (vegetable)',
 'apple':'Apple','apricots':'Apricot','avocado':'Avocado','banana':'Banana',
 'breadfruit':'Breadfruit','cherry':'Cherry','custard apple':'Custard apple','date':'Date palm',
 'fig':'Fig','grapefruit':'Grapefruit','grapes':'Grape','guava':'Guava','lemon':'Lemon',
 'lime':'Lime (fruit)','mango':'Mango','melon':'Melon','orange':'Orange (fruit)',
 'papaya':'Papaya','passion fruit':'Passion fruit (fruit)','peach':'Peach','pear':'Pear',
 'pineapple':'Pineapple','plum':'Plum','pomegranate':'Pomegranate','prickly pear':'Prickly pear',
 'tamarind':'Tamarind','tangerine':'Tangerine','watermelon':'Watermelon',
 'basil':'Basil','sacred basil':'Ocimum tenuiflorum','cardamom':'Cardamom',
 'false cardamom':'Aframomum corrorima','chili':'Chili pepper','cinnamon':'Cinnamon',
 'cloves':'Clove','coriander':'Coriander','fenugreek':'Fenugreek','mustard':'Mustard seed',
 'nutmeg':'Nutmeg','oregano':'Oregano','pepper':'Black pepper','rosemary':'Rosemary',
 'rue':'Ruta chalepensis','thyme':'Thyme','turmeric':'Turmeric','spices':'Berbere',
 "bishop's weed":'Trachyspermum ammi',
 'beef':'Beef','calf (veal)':'Veal','camel meat':'Camel meat','chicken':'Chicken as food',
 'goat':'Goat meat','pork':'Pork','sheep':'Lamb and mutton','egg':'Egg as food',
 'fish':'Fish as food','carp':'Common carp','catfish':'Catfish','nile perch':'Nile perch',
 'nile tilapia':'Nile tilapia','sardine':'Sardines as food','tuna':'Tuna as food',
 'butter':'Butter','butter milk':'Buttermilk','cheese':'Cheese','cheese mozzarella':'Mozzarella',
 'cream':'Cream','milk':'Milk','sourmilk':'Soured milk','yoghurt':'Yogurt','ice cream':'Ice cream',
 'tofu':'Tofu','soybean milk':'Soy milk','soybean sauce':'Soy sauce',
 'coffee':'Coffee','tea':'Tea','water':'Drinking water','juice':'Juice',
 'beer (5% v/v alcohol)':'Beer','wine':'Wine','mead':'Mead','tella':'Tella',
 'carbonated beverage':'Soft drink','flavoured drink':'Soft drink',
 'oil':'Vegetable oil','fish oil':'Fish oil','honey':'Honey','sugar (cane)':'Sugar',
 'sugar cane':'Sugarcane','salt':'Salt','baking powder':'Baking powder','yeast':'Baker\'s yeast',
 'mayonnaise':'Mayonnaise','marmalade':'Marmalade','jam':'Jam','syrup':'Syrup',
 'biscuit':'Biscuit','biscuits':'Biscuit','chocolate':'Chocolate','candies':'Candy',
 'toffees':'Toffee','chewing gum':'Chewing gum','cream cake':'Layer cake',
 'samosa from baked refined wheat flour':'Samosa','broth':'Broth',
 'red chilli powder with salt and spices':'Berbere',
 'spice blend from red pepper with salt and spices':'Berbere',
 'spice paste from chili':'Awaze','spice paste from green chilli':'Chili paste',
}

def request(url, binary=False):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(1 + attempt * 2)

def api(base, **params):
    return request(base + '?' + urllib.parse.urlencode({'action':'query','format':'json',**params}))

def clean_html(s):
    return re.sub('<[^>]+>', '', s or '').strip()

def fetch(item):
    key, article = item
    slug = re.sub(r'[^a-z0-9]+','-',key.lower()).strip('-')
    try:
        result = api(API, titles=article, redirects=1, prop='pageimages', piprop='name|thumbnail', pithumbsize=640)
        page = next(iter(result['query']['pages'].values()))
        name = page.get('pageimage')
        thumb = page.get('thumbnail',{}).get('source')
        if not name or not thumb:
            return key, {'missing':True,'article':article,'reason':'No representative article image'}
        info = api(COMMONS, titles='File:'+name, prop='imageinfo', iiprop='extmetadata|url', iiurlwidth=640)
        imagepage = next(iter(info['query']['pages'].values()))
        ii = imagepage.get('imageinfo',[{}])[0]
        meta = ii.get('extmetadata',{})
        license_name = meta.get('LicenseShortName',{}).get('value','')
        if not license_name:
            return key, {'missing':True,'article':article,'reason':'No Commons license metadata'}
        download = ii.get('thumburl') or thumb
        ext = '.png' if '.png' in download.lower().split('?')[0][-15:] else '.jpg'
        if '.svg' in download.lower() and '.png' not in download.lower():
            return key, {'missing':True,'article':article,'reason':'Vector illustration, photograph preferred'}
        target = DEST / (slug+ext)
        if not target.exists():
            target.write_bytes(request(download, binary=True))
        return key, {
            'src':'/images/foods/'+target.name,
            'alt':key.capitalize()+' — illustrative family image',
            'source':ii.get('descriptionurl','https://commons.wikimedia.org/wiki/File:'+urllib.parse.quote(name)),
            'article':'https://en.wikipedia.org/wiki/'+urllib.parse.quote(page.get('title',article).replace(' ','_')),
            'license':clean_html(license_name),
            'licenseUrl':meta.get('LicenseUrl',{}).get('value',''),
            'credit':clean_html(meta.get('Artist',{}).get('value','Wikimedia Commons contributor')),
            'description':clean_html(meta.get('ImageDescription',{}).get('value',''))[:700],
            'illustrative':True,
        }
    except Exception as exc:
        return key, {'missing':True,'article':article,'reason':str(exc)[:180]}

def main():
    existing = json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else {}
    pending = [(k,v) for k,v in ARTICLES.items() if k not in existing or existing[k].get('missing')]
    articles = list(dict.fromkeys(v for k,v in pending))
    pages = {}
    for offset in range(0,len(articles),30):
        result = api(API, titles='|'.join(articles[offset:offset+30]), redirects=1, prop='pageimages', piprop='name|thumbnail', pithumbsize=640)
        found = {p['title']:p for p in result['query']['pages'].values()}
        redirects = {v['from']:v['to'] for v in result['query'].get('redirects',[])}
        normalized = {v['from']:v['to'] for v in result['query'].get('normalized',[])}
        for title in articles[offset:offset+30]:
            actual = normalized.get(title,title)
            actual = redirects.get(actual,actual)
            pages[title] = found.get(actual,{})
        print('Article metadata',min(offset+30,len(articles)),'/',len(articles),flush=True)
    filenames = list(dict.fromkeys('File:'+p['pageimage'] for p in pages.values() if p.get('pageimage')))
    infos = {}
    for offset in range(0,len(filenames),30):
        result = api(COMMONS,titles='|'.join(filenames[offset:offset+30]),prop='imageinfo',iiprop='extmetadata|url',iiurlwidth=640)
        infos.update({p['title']:p for p in result['query']['pages'].values()})
        print('License metadata',min(offset+30,len(filenames)),'/',len(filenames),flush=True)
    def prepared(item):
        key,article = item
        page = pages.get(article,{})
        name = page.get('pageimage','')
        ii = infos.get('File:'+name.replace('_',' '),{}).get('imageinfo',[{}])[0]
        meta = ii.get('extmetadata',{})
        if not meta.get('LicenseShortName') or not ii.get('thumburl'):
            return key,{'missing':True,'article':article,'reason':'No Commons photo and license metadata'}
        url = ii['thumburl']
        slug = re.sub(r'[^a-z0-9]+','-',key.lower()).strip('-')
        ext = '.png' if url.split('?')[0].lower().endswith('.png') else '.jpg'
        target = DEST / (slug+ext)
        try:
            if not target.exists():
                target.write_bytes(request(url,binary=True))
            return key,{
                'src':'/images/foods/'+target.name,
                'alt':key.capitalize()+' — illustrative family image',
                'source':ii['descriptionurl'],
                'article':'https://en.wikipedia.org/wiki/'+urllib.parse.quote(page.get('title',article).replace(' ','_')),
                'license':clean_html(meta['LicenseShortName']['value']),
                'licenseUrl':meta.get('LicenseUrl',{}).get('value',''),
                'credit':clean_html(meta.get('Artist',{}).get('value','Wikimedia Commons contributor')),
                'description':clean_html(meta.get('ImageDescription',{}).get('value',''))[:700],
                'illustrative':True,
            }
        except Exception as exc:
            return key,{'missing':True,'article':article,'reason':str(exc)[:180]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for key, value in pool.map(prepared,pending):
            existing[key] = value
            DATA.write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding='utf-8')
            print(key, 'MISSING '+value.get('reason','') if value.get('missing') else value['src'],flush=True)
    print('Downloaded',sum(not v.get('missing') for v in existing.values()),'of',len(existing),flush=True)

if __name__ == '__main__':
    main()
