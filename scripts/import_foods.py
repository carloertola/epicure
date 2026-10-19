"""Reproducible, coordinate-aware import of the supplied EFCT 2025 PDF.

No imputation or correction of printed nutrient values is performed.
Run: python scripts/import_foods.py path/to/Ethiopian-Food-Composition-Table-2025.pdf
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ['macros', 'minerals', 'vitaminsBC', 'vitaminsADE', 'fats']
COLS = [
 [('edible','Edible portion coefficient','coefficient','EDIBLE'),('energy','Energy','kJ(kcal)','ENERC'),('water','Water','g','WATER'),('protein','Protein','g','PROTCNT'),('fat','Fat','g','FAT'),('carbohydrate','Available carbohydrate','g','CHOAVLDF'),('fiber','Total dietary fiber','g','FIBTG'),('ash','Ash','g','ASH')],
 [('calcium','Calcium','mg','CA'),('iron','Iron','mg','FE'),('magnesium','Magnesium','mg','MG'),('phosphorus','Phosphorus','mg','P'),('potassium','Potassium','mg','K'),('sodium','Sodium','mg','NA'),('zinc','Zinc','mg','ZN'),('copper','Copper','mg','CU'),('manganese','Manganese','mg','MN'),('selenium','Selenium','mcg','SE')],
 [('thiamin','Thiamin (B1)','mg','THIA'),('riboflavin','Riboflavin (B2)','mg','RIBF'),('niacin_equivalent','Niacin equivalents','mg','NIAEQ'),('niacin','Niacin','mg','NIA'),('vitamin_b6','Vitamin B6','mg','VITB6C'),('folate','Folate','mcg','FOL'),('vitamin_b12','Vitamin B12','mcg','VITB12'),('vitamin_c','Vitamin C','mg','VITC')],
 [('beta_carotene','Beta-carotene equivalents','mcg','CARTBEQ'),('retinol','Retinol','mcg','RETOL'),('vitamin_a_re','Vitamin A RE','mcg','VITA'),('vitamin_a_rae','Vitamin A RAE','mcg','VITA_RAE'),('vitamin_d','Vitamin D','mcg','VITD'),('vitamin_e','Vitamin E','mg','VITE'),('alpha_tocopherol','Alpha-tocopherol','mg','TOCPHA')],
 [('phytate','Phytate','mg','PHYTCPP'),('cholesterol','Cholesterol','mg','CHOLE'),('saturated_fat','Saturated fatty acids','g','FASAT'),('monounsaturated_fat','Monounsaturated fatty acids','g','FAMS'),('polyunsaturated_fat','Polyunsaturated fatty acids','g','FAPU'),('linoleic_acid','Linoleic acid','g','F18D2CN6'),('alpha_linolenic_acid','Alpha-linolenic acid','g','F18D3CN3')]
]
GROUPS = ['Cereals and their products','Starchy roots, tubers, and their products','Legumes and their products','Vegetables and their products','Fruits and their products','Nuts, seeds, and their products','Meat, poultry, and their products','Eggs and their products','Fish, seafood, and their products','Milk and its products','Fats and oils','Beverages','Sugar and sweetened products','Condiments and spices','Miscellaneous','Soups and sauces','Mixed']
EXPECTED_COUNTS = [157,44,73,82,32,16,123,15,23,25,20,35,16,41,4,10,11]

def clean(text):
    return re.sub(r'\s+', ' ', text).strip().replace('(cid:415)', 'ti').replace('(cid:414)', 'tt').replace('(cid:444)', 'ti')

def joined(words):
    # Group physical lines before joining so wrapped descriptions retain order.
    lines = collections.defaultdict(list)
    for w in words:
        lines[round(w['top'] / 2) * 2].append(w)
    return clean(' '.join(' '.join(w['text'] for w in sorted(line,key=lambda w:w['x0'])) for _,line in sorted(lines.items())))

def parse_number(raw):
    s=raw.strip().lower()
    flags=[]
    if '[' in s or ']' in s: flags.append('lower-quality')
    s=s.replace('[','').replace(']','')
    if s in ('tr','trace'): return None,flags+['trace']
    if s=='<lod': return None,flags+['below-detection-limit']
    if not s or s in ('-','—','na','n/a'): return None,flags+['missing']
    s=s.replace('[','').replace(']','').replace(',','')
    if re.fullmatch(r'[-+]?\d+(?:\.\d+)?',s): return float(s),flags
    return None,flags+['unparsed']

def main(pdf_path):
    rows=[]; page_audit=[]; issues=[]
    with pdfplumber.open(pdf_path) as pdf:
        for pno in range(45,345):
            p=pdf.pages[pno-1]
            words=p.extract_words(x_tolerance=1.5,y_tolerance=2)
            sec=(pno-45)%5; cols=COLS[sec]
            tag_line=next(w['top'] for w in words if w['text']=='Tagnames' and w['top']<160)
            tags=sorted([w for w in words if abs(w['top']-tag_line)<4 and w['x0']>180],key=lambda w:w['x0'])
            if len(tags)!=len(cols): raise ValueError(f'Page {pno}: expected {len(cols)} columns, got {tags}')
            actual_tags=[w['text'] for w in tags]
            if actual_tags!=[c[3] for c in cols]: issues.append({'page':pno,'headerTags':actual_tags,'expectedTags':[c[3] for c in cols],'note':'Source header labels differ; physical column order retained.'})
            centers=[(w['x0']+w['x1'])/2 for w in tags]
            bounds=[(a+b)/2 for a,b in zip(centers,centers[1:])]
            left=centers[0]-(centers[1]-centers[0])/2
            words=[w for w in words if not (w['top']>p.height-65 and w['text']==str(pno-12) and abs((w['x0']+w['x1'])/2-p.width/2)<40)]
            codes=sorted([w for w in words if w['x0']<105 and re.fullmatch(r'\d{6}',w['text'])],key=lambda w:w['top'])
            english_x=next(w['x0'] for w in words if w['text']=='Food' and w['top']<110)
            amharic_x=next((w['x0'] for w in words if w['text']=='Food' and w['top']<110 and w['x0']>english_x+30),left)
            page_rows=[]
            expected_cells=len(cols)+(3 if sec==0 else 2)
            page_grids=[]
            for sample_code in codes:
                sample_cells=[r for r in p.rects if r['x0']<sample_code['x0'] and r['x1']>=sample_code['x1'] and r['top']<=sample_code['top'] and r['bottom']>=sample_code['bottom'] and r['width']<80]
                if not sample_cells: continue
                sample_cell=max(sample_cells,key=lambda r:r['width']*r['height'])
                grid=sorted([r for r in p.rects if abs(r['top']-sample_cell['top'])<.1 and abs(r['bottom']-sample_cell['bottom'])<.1 and r['width']>=12],key=lambda r:r['x0'])
                if len(grid)==expected_cells: page_grids.append(grid)
            if not page_grids: raise ValueError(f'Page {pno}: no complete row grid')
            for idx,code in enumerate(codes):
                end=codes[idx+1]['top']-1 if idx+1<len(codes) else p.height-40
                code_cells=[r for r in p.rects if r['x0']<code['x0'] and r['x1']>=code['x1'] and r['top']<=code['top'] and r['bottom']>=code['bottom'] and r['width']<80]
                if not code_cells:
                    issues.append({'page':pno,'id':code['text'],'note':'Unshaded source row has no rectangles; physical code baseline and nearby row columns used.'})
                    code_cell={'top':code['top']-1.8,'bottom':code['bottom']+1.8,'non_stroking_color':None}
                else: code_cell=max(code_cells,key=lambda r:r['width']*r['height'])
                cells=sorted([r for r in p.rects if abs(r['top']-code_cell['top'])<0.1 and abs(r['bottom']-code_cell['bottom'])<0.1 and r['width']>=12],key=lambda r:r['x0'])
                # Shaded table cell rectangles encode exact row and column extents.
                # Their geometry changes on some pages independently of the header.
                if len(cells)!=expected_cells:
                    issues.append({'page':pno,'id':code['text'],'note':'Merged or split source cells; nearby complete row grid used for columns.','cells':len(cells),'expected':expected_cells})
                    cells=min(page_grids,key=lambda grid:abs(grid[0]['top']-code_cell['top']))
                row_start=code_cell['top']; row_end=code_cell['bottom']
                if idx+1<len(codes):
                    next_code=codes[idx+1]
                    next_cells=[r for r in p.rects if r['x0']<next_code['x0'] and r['x1']>=next_code['x1'] and r['top']<=next_code['top'] and r['bottom']>=next_code['bottom'] and r['width']<80]
                    end=max(next_cells,key=lambda r:r['width']*r['height'])['top'] if next_cells else next_code['top']-2
                row_words=[w for w in words if row_start-0.1<=w['top']<end]
                stats=[w for w in row_words if w['x0']<english_x+10 and w['text'] in ('Non-African','SD','n')]
                cutoff=min([w['top'] for w in stats],default=end)
                body=[w for w in words if row_start-0.1<=w['top'] and w['bottom']<=row_end+0.1]
                # Some final rows are followed by a group title; only accept name-column words.
                name=joined([w for w in body if cells[1]['x0']<=(w['x0']+w['x1'])/2<cells[1]['x1']])
                amharic=joined([w for w in body if cells[2]['x0']<=(w['x0']+w['x1'])/2<cells[2]['x1']]) if sec==0 else ''
                values={}; flags={}; non_african={}; stats_values={}
                for j,(key,_,_,_) in enumerate(cols):
                    cell=cells[j+(3 if sec==0 else 2)];lo=cell['x0'];hi=cell['x1']
                    candidates=[w for w in body if lo<=(w['x0']+w['x1'])/2<hi]
                    value=joined(candidates).replace(' ','')
                    values[key]=value
                    if len(candidates)>1: issues.append({'page':pno,'id':code['text'],'key':key,'multipleTokens':value})
                    for kind,marker in [('nonAfrican','Non-African'),('sdOrRange','SD'),('sampleCount','n')]:
                        lines=[w['top'] for w in stats if w['text']==marker]
                        if lines:
                            found=joined([w for w in row_words if lo<=(w['x0']+w['x1'])/2<hi and abs(w['top']-lines[0])<2])
                            if found:
                                if kind=='nonAfrican': non_african[key]=found
                                else: stats_values.setdefault(key,{})[kind]=found
                page_rows.append({'code':code['text'],'name':name,'amharic':amharic,'page':pno,'section':SECTIONS[sec],'raw':values,'nonAfrican':non_african,'statistics':stats_values,'sourceColor':code_cell['non_stroking_color']})
            rows.extend(page_rows)
            page_audit.append({'page':pno,'section':SECTIONS[sec],'rows':len(codes),'codes':[r['code'] for r in page_rows]})
            p.close()
            if pno%25==19: print(f'Extracted page {pno}',flush=True)
    (ROOT/'source'/'extracted-rows.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
    build(rows, page_audit, issues, pdf_path)

def build(rows, page_audit, issues, pdf_path):
    # A repeated printed code gets its own entry rather than silently discarding a row.
    foods=[]; by_code=collections.defaultdict(list)
    for row in rows:
        if row['section']=='macros':
            code=row['code']; n=len(by_code[code]); entry={'id':code if n==0 else f'{code}-{n+1}','code':code,'name':row['name'],'amharic':row['amharic'],'groupId':code[:2],'nutrients':{},'raw':{},'quality':{},'nonAfrican':{},'statistics':{},'pages':{}}
            foods.append(entry); by_code[code].append(entry)
    # Source sections contain repeated rows absent from their corresponding macro
    # page. Join by printed code, never by ordinal; preserve each occurrence.
    for target in foods:
        for section in SECTIONS:
            candidates=[r for r in rows if r['code']==target['code'] and r['section']==section]
            if not candidates: raise ValueError(f'{target["code"]}: no {section} row')
            expected_page=next(r['page'] for r in rows if r['code']==target['code'] and r['section']=='macros')+SECTIONS.index(section)
            row=min(candidates,key=lambda r:abs(r['page']-expected_page))
            target['pages'][section]=row['page']
            target['raw'].update(row['raw']);target['nonAfrican'].update(row['nonAfrican']);target['statistics'].update(row['statistics'])
            if len(candidates)>1:
                issues.append({'id':target['code'],'section':section,'occurrencePages':[r['page'] for r in candidates],'chosenPage':row['page'],'conflictingValues':any(r['raw']!=row['raw'] for r in candidates),'note':'Source repeats this food in a nutrient section; closest matching macro batch retained.'})
    for f in foods:
        for key,raw in f['raw'].items():
            if key=='energy':
                match=re.fullmatch(r'(\[?\d+(?:\.\d+)?\]?)\((\[?\d+(?:\.\d+)?\]?)\)*',raw)
                kj_only=bool(re.fullmatch(r'\d+(?:\.\d+)?',raw))
                for k,value in [('energy_kj',match.group(1) if match else raw if kj_only else ''),('energy_kcal',match.group(2) if match else '')]:
                    number,flags=parse_number(value);f['nutrients'][k]=number
                    if flags: f['quality'][k]=flags
                if not match: issues.append({'id':f['id'],'key':'energy','raw':raw,'note':'Source contains only kJ or an ambiguous malformed expression. No missing kcal value is inferred.'})
            else:
                number,flags=parse_number(raw);f['nutrients'][key]=number
                if flags: f['quality'][key]=flags
        f['baseName']=f['name'].split(',')[0].strip().lower()
        lower=f['name'].lower()
        f['methods']=[method for method in ['boiled','steamed','roasted','baked','fried','grilled','sauteed','sautéed','fermented','dried','sprouted','germinated','pasteurized','powdered'] if method in lower]
        recipe=bool(re.search(r'\b(with|sauce|stew|ferfer|fetfet|porridge|bread|enjera|injera|shiro|ambasha|kita|genfo|besso|salad|biscuit|cake)\b',lower)) or f['groupId'] in ['16','17']
        f['state']='cooked' if re.search(r'\b(boiled|steamed|roasted|baked|fried|grilled|sauteed|sautéed|cooked)\b',lower) else 'raw' if re.search(r'\braw\b',lower) else 'recipe' if recipe and 'as part of a recipe' not in lower else 'raw'
        f['stateBasis']='description-inferred' if f['state']!='raw' or 'raw' in lower else 'source-default-raw'
        f['conditions']={category:[term for term in terms if re.search(r'\b'+re.escape(term)+r'\b',lower)] for category,terms in {'maturity':['ripe','unripe','mature','immature','young','fresh'],'physical':['dried','dry','powder','flour','whole grain','split','peeled','with skin','without skin','canned','fluid','frozen'],'additions':['without salt','with salt','without fat','with oil','fortified','unfortified'],'liquid':['drained','as part of a recipe']}.items()}
        f['timings']=re.findall(r'\b\d+(?:\.\d+)?\s*(?:min\.?|minutes?|hours?|days?)\b',lower)
        if f['groupId']=='01':
            f['quality'].setdefault('retinol',[]).append('source-anomaly')
            f['sourceNotes']=['The cereal retinol column in the supplied PDF contains an apparent ascending row sequence (visually checked on PDF pages 48 and 98). The printed value is preserved, but should not be used as a reliable retinol estimate without publisher verification.']
    components=[]
    for section,cols in zip(SECTIONS,COLS):
        for key,label,unit,tag in cols:
            if key=='energy':
                components.extend([{'key':'energy_kj','label':'Energy','unit':'kJ','tag':tag,'section':section},{'key':'energy_kcal','label':'Energy','unit':'kcal','tag':tag,'section':section}])
            else: components.append({'key':key,'label':label,'unit':unit,'tag':tag,'section':section})
    counts=collections.Counter(f['groupId'] for f in foods)
    metadata={'title':'Ethiopian Food Composition Table 2025','citation':'Ethiopian Public Health Institute (EPHI) and Food and Agriculture Organization of the United Nations (FAO). 2025. The Ethiopian Food Composition Table 2025. Addis Ababa, Ethiopia.','copyright':'© Ethiopian Public Health Institute (EPHI), 2025. Reproduced with acknowledgement; no endorsement is implied.','basis':'Per 100 g edible portion, fresh weight basis; edible is a coefficient, not a nutrient amount.','sourceFile':pdf_path.name,'sourceSha256':hashlib.sha256(pdf_path.read_bytes()).hexdigest(),'pdfPages':[45,344],'printedPageOffset':12,'declaredFoods':727,'declaredComponents':39,'printedColumnsIncludingEdible':40,'numericKeysIncludingEdibleAndBothEnergyUnits':41,'limitations':['Harvest, maturity, preparation and cooking conditions are available only when specified by the source food description.','Trace and missing values are null, not zero. Bracketed source values are lower quality.','The source table combines energy kJ(kcal); both source units are represented separately.','The condensed PDF contains 39 nutritional component columns plus an edible portion coefficient. It does not contain the complete 69-component Excel dataset.']}
    metadata['importedFoods']=len(foods)
    metadata['sourcePdf']='/data/source-table.pdf'
    metadata['limitations'].extend(['The guide declares 727 foods, but its condensed table contains 722 distinct printed food codes: 43 roots/tubers versus 44 declared, and 37 condiments/spices versus 41 declared. Missing rows have not been invented.','The cereal retinol column contains an apparent sequential-number error in the PDF itself. All 157 affected entries retain the printed value and carry a source-anomaly quality flag; exclude these values from nutritional recommendations.','Food state, methods, timings and conditions are simple description-derived search aids, not publisher classification. Source descriptions remain authoritative.'])
    payload={'metadata':metadata,'components':components,'groups':[{'id':f'{i+1:02}','name':name,'declaredCount':EXPECTED_COUNTS[i],'importedCount':counts[f'{i+1:02}']} for i,name in enumerate(GROUPS)],'foods':foods}
    audit={'sourceSha256':metadata['sourceSha256'],'foodRows':len(foods),'uniquePrintedCodes':len(by_code),'duplicatePrintedCodes':{k:[{'id':f['id'],'name':f['name'],'page':f['pages'].get('macros')} for f in v] for k,v in by_code.items() if len(v)>1},'groups':payload['groups'],'pages':page_audit,'issues':issues,'componentKeyCount':len(components),'qualityFlagCounts':dict(collections.Counter(flag for f in foods for flags in f['quality'].values() for flag in flags))}
    audit['validation']={'allFoodsHaveFiveCitations':all(len(f['pages'])==5 for f in foods),'allFoodsHave41NumericKeys':all(len(f['nutrients'])==41 for f in foods),'allFoodNamesPresent':all(bool(f['name']) for f in foods),'nonNegativeNumericValues':all(v>=0 for f in foods for v in f['nutrients'].values() if v is not None),'noUnparsedValues':not any('unparsed' in flags for f in foods for flags in f['quality'].values())}
    audit['validation']['allPrintedCodesPresentAcrossSections']=all(set(r['code'] for r in rows if r['section']==section)==set(by_code) for section in SECTIONS)
    audit['sourceErrata']=[{'component':'retinol','groupId':'01','affectedFoods':157,'pdfPagesVisuallyChecked':[48,98],'finding':'Printed values form an apparent ascending row sequence. Retained with source-anomaly flag; not suitable for recommendations pending publisher verification.'}]
    audit['numericCoverage']={c['key']:{'known':sum(f['nutrients'][c['key']] is not None for f in foods),'total':len(foods)} for c in components}
    (ROOT/'public'/'data'/'foods.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    (ROOT/'source'/'data-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'public'/'data'/'data-audit.json').write_text(json.dumps(audit,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k in ('foodRows','uniquePrintedCodes','componentKeyCount','qualityFlagCounts','validation','sourceErrata')},indent=2,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('pdf',type=Path);parser.add_argument('--reuse-extraction',action='store_true');args=parser.parse_args()
    if args.reuse_extraction:
        previous=json.loads((ROOT/'source'/'data-audit.json').read_text(encoding='utf-8'))
        extraction_issues=[issue for issue in previous['issues'] if 'page' in issue and 'row' not in issue]
        build(json.loads((ROOT/'source'/'extracted-rows.json').read_text(encoding='utf-8')),previous['pages'],extraction_issues,args.pdf)
    else: main(args.pdf)



