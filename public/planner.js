import {base,group,requiresCooking,totals} from './engine.js';
import {servingReference,allocatePortions,validatePeople} from './portions.js';
import {preparationAdvice,pairingAdvice,spiceSuggestions} from './guidance.js';
export const EQUIPMENT=[['stove','Stove & pot'],['steamer','Steamer'],['oven','Oven'],['microwave','Microwave'],['blender','Blender'],['grinder','Grinder'],['fermentation','Fermentation jar & safe recipe']];
export const sameFamily=(a,b)=>group(a)===group(b)&&base(a).toLowerCase()===base(b).toLowerCase();
export function methodsFor(food,equipment){
  const has=k=>equipment.includes(k),g=group(food),name=base(food).toLowerCase(),out=[];
  if(!requiresCooking(food))out.push({id:'recorded',label:/raw/i.test(food.name)?'Fresh / as recorded':'Already prepared / as recorded',equipment:[]});
  if(/cassava/.test(name)&&requiresCooking(food))return[];
  if(['07','08','09'].includes(g)){
    if(has('stove'))out.push({id:'boil',label:g==='08'?'Boil until fully cooked':'Cook thoroughly on the stove',equipment:['stove']});
    if(has('oven')&&g!=='08')out.push({id:'roast',label:'Roast / bake safely',equipment:['oven']});
    return out;
  }
  if(['01','02','03','04'].includes(g)&&has('stove'))out.push({id:'boil',label:'Boil / cook in water',equipment:['stove']});
  if(['02','04'].includes(g)&&has('steamer'))out.push({id:'steam',label:'Steam briefly',equipment:['steamer']});
  if(g==='04'&&has('microwave'))out.push({id:'microwave',label:'Microwave with a little water',equipment:['microwave']});
  if(['02','04'].includes(g)&&has('oven'))out.push({id:'roast',label:'Roast / bake',equipment:['oven']});
  if((g==='06'||/garlic|ginger|spice|mustard|pepper|coriander|linseed/.test(name))&&(has('grinder')||has('blender')))out.push({id:'grind',label:'Grind / crush',equipment:[has('grinder')?'grinder':'blender']});
  if(['04','05'].includes(g)&&has('blender')&&!requiresCooking(food))out.push({id:'blend',label:'Blend with a little water',equipment:['blender']});
  if(name==='teff'&&has('fermentation')&&has('stove'))out.push({id:'ferment',label:'Ferment, then cook as injera',equipment:['fermentation','stove']});
  return out;
}
export function preferredMethod(food,equipment){
  const options=methodsFor(food,equipment),name=base(food).toLowerCase();
  const preferred=/linseed|flaxseed/.test(name)?'grind':name==='teff'?'ferment':group(food)==='04'&&Number(food.nutrients.vitamin_c)>=15?'steam':requiresCooking(food)?'boil':'recorded';
  return options.find(m=>m.id===preferred)?.id||options[0]?.id||'';
}
export function recordedProfile(food,method,foods){
  if(['recorded','blend','grind'].includes(method))return food; // Added water contributes no tracked nutrients; weigh the ingredient before adding it.
  if(method==='ferment')return null; // No verified raw flour -> cooked injera yield is available.
  const patterns={boil:/boiled|cooked/i,steam:/steam/i,microwave:/microwave/i,roast:/roasted|baked|grilled/i};
  const pattern=patterns[method];if(!pattern)return null;
  const identity=f=>f.name.toLowerCase().split(',').slice(1).map(s=>s.trim()).filter(s=>s&&!/raw|boiled|cooked|roasted|baked|fried|grilled|steamed|microwaved|drained|as part|without salt|without.*fat/.test(s)).join('|');
  return foods.filter(f=>sameFamily(food,f)&&identity(f)===identity(food)&&pattern.test(f.name)&&!/stew|with oil|with butter|with sauce|sautéed/i.test(f.name)).sort((a,b)=>Number(/drained/i.test(b.name))-Number(/drained/i.test(a.name))||a.name.length-b.name.length)[0]||null;
}
export function makeRows(ingredients,equipment,methods,foods,custom={}){
  return ingredients.map(id=>{
    const food=foods.find(f=>f.id===id);if(!food)throw Error('An ingredient is no longer available.');
    const options=methodsFor(food,equipment),method=methods[id]||preferredMethod(food,equipment);
    if(!options.some(m=>m.id===method))throw Error(`Choose available equipment and a suitable method for ${base(food)}.`);
    const profile=recordedProfile(food,method,foods);
    const reference=servingReference(profile||food,{cooked:['boil','steam','microwave','roast'].includes(method)});
    return{food,method,profile,reference,customGrams:custom[id]};
  });
}
export function estimateNutrition(items,foods,keys){
  const converted=new Set(),profiles=foods.map(f=>{if(f.nutrients.energy_kcal==null&&Number.isFinite(f.nutrients.energy_kj)&&!f.quality?.energy_kj?.includes('source-anomaly')){converted.add(f.id);return{...f,nutrients:{...f.nutrients,energy_kcal:f.nutrients.energy_kj/4.184},quality:{...f.quality,energy_kcal:['converted-from-kJ']}};}return f;});
  const known=items.filter(r=>r.knownProfile!==false),t=totals(known,profiles,keys),unknown=items.length-known.length;
  for(const key of keys)t.missing[key]+=unknown;
  t.derived={energy_kcal:known.filter(r=>converted.has(r.id)).length};
  return t;
}
export function cookingStep(row,grams,youngChild){
  const food=row.food,name=base(food),g=group(food),amount=`${grams.toFixed(1).replace(/\.0$/,'')} g`,method=row.method;
  let text;
  if(method==='recorded')text=requiresCooking(food)?`Cook ${name} before eating.`:/raw/i.test(food.name)?`Wash and prepare ${amount} edible ${name}. Serve fresh.`:`Use ${amount} of ${name} in the recorded prepared state: ${food.name}.`;
  if(method==='boil')text=/kidney bean|haricot.*bean/i.test(name)?`For dry ${name}, soak at least 5 hours, discard the water, and boil in fresh water for at least 30 minutes. Do not use a slow cooker alone. Then weigh out ${amount} cooked edible beans.`:g==='07'||g==='09'?`Cook ${name} on the stove. Verify the safe internal temperature for the exact food and cut using the linked USDA chart. Weigh out ${amount} cooked edible food, excluding bones.`:g==='08'?`Cook eggs until the white and yolk are firm; egg dishes should reach 71°C / 160°F. Weigh out ${amount} edible cooked egg without the shell.`:`Cook ${name} in water until fully cooked, following the food’s package directions or a reliable recipe. Weigh out ${amount} cooked edible food${row.profile&&/drained/i.test(row.profile.name)?' after draining':''}.`;
  if(method==='steam')text=`Steam ${name} using your steamer, stopping when suitably tender. Weigh out ${amount} cooked edible food. Avoid prolonged heating when preserving vitamin C is your priority.`;
  if(method==='microwave')text=`Put ${name} in a microwave-safe covered dish with a little water. Microwave in short intervals until cooked, stirring as needed. Weigh out ${amount} cooked edible food.`;
  if(method==='roast')text=`Roast ${name} in your oven using a reliable recipe for that ingredient. ${['07','09'].includes(g)?'Verify the safe internal temperature for the exact food/cut with a thermometer. ':''}Weigh out ${amount} cooked edible food. Add any oil as its own ingredient if you use it.`;
  if(method==='grind')text=`Weigh ${amount} edible ${name}, then grind or crush using your ${/linseed/i.test(name)?'grinder or suitable blender':'selected appliance'}. Add to the meal${/mustard/i.test(name)?' after cooking if pairing with cooked broccoli':''}.`;
  if(method==='blend')text=`Weigh ${amount} edible ${name} before adding water, then blend. Keep the pulp; discarded solids would change the nutrient estimate. Record milk, oil or other additions separately.`;
  if(method==='ferment')text=`Use a tested food-safe teff injera recipe, your fermentation jar and stove. Measure ${amount} raw teff flour for this plan. Ferment and cook according to that recipe; this app does not invent fermentation time or a flour-to-injera yield.`;
  if(youngChild&&g==='06')text+=' For children under five, use finely ground nuts/seeds mixed into food, or a smooth paste stirred into the meal; do not serve whole nuts or a spoonful of nut butter.';
  return{title:`${{recorded:'Prepare',boil:'Cook',steam:'Steam',microwave:'Microwave',roast:'Roast',grind:'Grind',blend:'Blend',ferment:'Ferment & cook'}[method]} ${name}`,text,source:youngChild&&g==='06'?'children':['07','08','09'].includes(g)?'safety':/kidney bean|haricot.*bean/i.test(name)?'beans':preparationAdvice(food).source};
}
export function generatePlan({people,ingredients,equipment,methods={},custom={},share=1/3},foods,components){
  if(!validatePeople(people))throw Error('Complete the diner details first.');
  if(!Array.isArray(ingredients)||!ingredients.length||ingredients.length>30||new Set(ingredients).size!==ingredients.length)throw Error('Choose 1–30 different ingredients.');
  if(people.some(p=>p.age<18)&&ingredients.some(id=>/beer|wine|tella|mead|alcohol/i.test(foods.find(f=>f.id===id)?.name||'')))throw Error('Remove alcoholic drinks from a meal planned for children.');
  const rows=makeRows(ingredients,equipment,methods,foods,custom),allocations=allocatePortions(rows,people,Number(share));
  const batch=rows.map(row=>({id:row.profile?.id||row.food.id,ingredientId:row.food.id,knownProfile:!!row.profile,grams:Math.round(allocations.reduce((sum,p)=>sum+p.items.find(r=>r.ingredientId===row.food.id).grams,0)*10)/10}));
  const young=people.some(p=>p.age<5),steps=rows.map((row,i)=>cookingStep(row,batch[i].grams,young));
  steps.unshift({title:'Set up your ingredients',text:'Wash your hands and produce. Use separate utensils for raw animal foods and ready-to-eat foods. The quantities below are edible weights in the stated raw or cooked state.'});
  steps.push({title:'Bring the meal together',text:'Combine the cooked components and add fresh vitamin C ingredients near serving time. Divide each ingredient according to the diner portions below; each person’s share can differ. Record any extra oil, sauce or other additions.'});
  const keys=components.filter(c=>!['edible','energy_kj'].includes(c.key)).map(c=>c.key);
  return{version:1,id:crypto.randomUUID(),title:rows.slice(0,3).map(r=>base(r.food)).join(', ')+' meal',people:allocations,ingredients:batch,rows:rows.map(r=>({ingredientId:r.food.id,profileId:r.profile?.id||null,method:r.method,reference:r.reference})),steps,equipment,share:Number(share),nutrition:estimateNutrition(batch,foods,keys),sources:['EPHI & FAO · Ethiopian Food Composition Table 2025','Australian Government · Eat for Health standard serves'],pairings:pairingAdvice(batch.filter(r=>r.knownProfile),foods),spices:spiceSuggestions(batch,foods)};
}
export function localDate(date=new Date()){return`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;}
export function periodRange(date,period){
  const start=new Date(`${date}T12:00:00`),end=new Date(start);
  if(Number.isNaN(start.getTime()))throw Error('Choose a valid date.');
  if(period==='week'){const day=(start.getDay()+6)%7;start.setDate(start.getDate()-day);end.setTime(start.getTime());end.setDate(end.getDate()+6);}
  if(period==='month'){start.setDate(1);end.setMonth(end.getMonth()+1,0);}
  if(period==='year'){start.setMonth(0,1);end.setMonth(11,31);}
  return{start:localDate(start),end:localDate(end)};
}
export function aggregateEntries(entries,start,end,person='all'){
  const selected=entries.filter(e=>e.date>=start&&e.date<=end&&(person==='all'||e.personKey===person)),values={},missing={},flagged={},derived={energy_kcal:0};
  for(const entry of selected)for(const [key,value]of Object.entries(entry.nutrition.values)){values[key]=(values[key]||0)+value;missing[key]=(missing[key]||0)+(entry.nutrition.missing[key]||0);flagged[key]=(flagged[key]||0)+(entry.nutrition.flagged[key]||0);}
  for(const entry of selected)derived.energy_kcal+=entry.nutrition.derived?.energy_kcal||0;
  return{values,missing,flagged,derived,count:selected.length,entries:selected};
}
