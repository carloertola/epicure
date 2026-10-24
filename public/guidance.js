import {base, group, portion, requiresCooking} from './engine.js';

export const SOURCES = {
  iron: ['Vitamin C & plant iron · NIH', 'https://ods.od.nih.gov/factsheets/Iron-HealthProfessional/'],
  fat: ['Carotenoids & dietary fat · human study', 'https://pubmed.ncbi.nlm.nih.gov/15735074/'],
  vitaminC: ['Vitamin C & cooking · NIH', 'https://ods.od.nih.gov/factsheets/VitaminC-HealthProfessional/'],
  tomato: ['Heating tomatoes · food study', 'https://pubmed.ncbi.nlm.nih.gov/11982434/'],
  fermentation: ['Teff fermentation & phytate · food study', 'https://pubmed.ncbi.nlm.nih.gov/29052470/'],
  grinding: ['Milling flaxseed · human study', 'https://jn.nutrition.org/article/S0022-3166(22)10507-9/fulltext'],
  beans: ['Preparing kidney beans · FDA', 'https://www.fda.gov/food/chemical-contaminants-pesticides/natural-toxins-food'],
  safety: ['Safe cooking temperatures · USDA', 'https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/safe-temperature-chart'],
  spices: ['Herbs & spices in place of salt · NIH', 'https://www.nhlbi.nih.gov/health/dash/living-with-dash'],
  turmeric: ['Turmeric: evidence & limitations · NIH', 'https://www.nccih.nih.gov/health/turmeric'],
  mustard: ['Mustard seed & cooked broccoli · human study', 'https://pubmed.ncbi.nlm.nih.gov/29806738/'],
  children: ['Preparing nuts for young children · NHS', 'https://www.nhs.uk/baby/weaning-and-feeding/foods-to-avoid-giving-babies-and-young-children/'],
};

// These are practical display thresholds, not clinical cutoffs or absorption estimates.
export function nutrient(food, key, grams = 100) {
  const n = food.nutrients[key];
  return Number.isFinite(n) && !food.quality?.[key]?.includes('source-anomaly') ? n * grams / 100 : 0;
}
export function pairingAdvice(items, foods) {
  const chosen = items.map(row => ({...row, food: foods.find(f => f.id === row.id)})).filter(r => r.food);
  const iron = chosen.filter(r => ['01','03','04','06'].includes(group(r.food)) && nutrient(r.food, 'iron', r.grams) >= 1);
  const vitaminC = chosen.filter(r => !requiresCooking(r.food) && nutrient(r.food, 'vitamin_c', r.grams) >= 10);
  const color = chosen.filter(r => ['02','04','05'].includes(group(r.food)) && nutrient(r.food, 'beta_carotene', r.grams) >= 300);
  const fat = chosen.filter(r => nutrient(r.food, 'fat', r.grams) >= 2 && ['06','10','11','05','08','09'].includes(group(r.food)));
  const result = [];
  const differentPair = (a,b) => a.flatMap(x => b.filter(y => y.id !== x.id).map(y => [x,y]))[0];
  const ironPair = differentPair(iron, vitaminC), fatPair = differentPair(color, fat);
  if (ironPair) result.push({key:'iron', title:'Help your body absorb plant iron', pair:ironPair.map(r=>r.food), evidence:'Established interaction', text:'Vitamin C eaten in the same meal can improve nonheme iron absorption. Your selected portions bring both together. Enjoy these foods in the same meal.', source:'iron'});
  if (fatPair) result.push({key:'fat', title:'Give carotenoids a helping hand', pair:fatPair.map(r=>r.food), evidence:'Supported by human studies', text:'Dietary fat helps the absorption of carotenoids from vegetables. These foods bring carotenoids and fat to the same meal; no absorption percentage is predicted.', source:'fat'});
  const selectedBases = new Set(chosen.map(r => base(r.food).toLowerCase()));
  const candidate = patterns => patterns.map(p => foods.find(f => p.test(f.name) && !selectedBases.has(base(f).toLowerCase()) && !requiresCooking(f))).find(Boolean);
  if (iron.length && !ironPair) {
    const add = candidate([/^Orange,.*raw/i,/^Tomato,.*raw/i,/^Guava,.*raw/i]);
    if(add) result.push({key:'iron-add', title:'Add a vitamin C companion', pair:[iron[0].food,add], add, evidence:'Established interaction', text:'Pair this plant iron food with a vitamin C food at the same meal. An orange or fresh tomato is a practical addition. The benefit depends on the whole meal and your iron status.', source:'iron'});
  }
  if (color.length && !fatPair) {
    const add = candidate([/^Avocado,.*raw/i,/^Sesame seed,.*kernel.*raw/i,/^Oil,.*olive/i]);
    if(add) result.push({key:'fat-add', title:'Pair colorful vegetables with fat', pair:[color[0].food,add], add, evidence:'Supported by human studies', text:'Include some avocado, seeds or oil with carotenoid-rich vegetables. Dietary fat can help carotenoid absorption; the useful amount varies with the meal.', source:'fat'});
  }
  return result;
}

export function preparationAdvice(f) {
  const name = base(f).toLowerCase(), g = group(f);
  if (/kidney bean|haricot.*bean/.test(name)) return {method:'Soak, then boil', text:'For dry kidney beans: soak for at least 5 hours, discard the water, then boil in fresh water for at least 30 minutes. Do not rely on a slow cooker alone. Already canned or properly cooked beans do not need this dry-bean process.', why:'Proper cooking takes priority over nutrient retention.', source:'beans'};
  if (/linseed|flaxseed/.test(name)) return {method:'Grind or crush', text:'Use milled or crushed flaxseed rather than intact seeds. A human study found greater availability of lignan metabolites after milling. This is specific to flaxseed, not a guarantee for every seed.', why:'Break the seed coat to make its contents more accessible.', source:'grinding'};
  if (name==='teff'||(/enjera|injera/.test(name)&&/teff/i.test(f.name))) return {method:'Ferment, then cook', text:'For teff-based injera, fermentation can reduce phytate, which binds minerals. The reduction varies with the flour and fermentation process. Use an established food-safe recipe; no specific iron-absorption gain is assumed.', why:'Less phytate may improve mineral availability.', source:'fermentation'};
  if (g==='03') return {method:'Cook thoroughly', text:'Prepare dry pulses according to a reliable recipe or package directions until fully cooked. Choose a matching boiled entry below and weigh the cooked portion for its nutrient reading.', why:'Raw and cooked weights describe different foods.'};
  if (name==='tomato') return {method:'Choose raw or gently cooked', text:'Keep some tomato raw when vitamin C is the priority. Heating can make lycopene more accessible, but reduces vitamin C. Both methods have a place; there is no single winner for every nutrient.', why:'A tradeoff between vitamin C retention and lycopene accessibility.', source:'tomato'};
  if (g==='04') return {method:'Steam or microwave briefly', text:'For vegetables suitable for these methods, use a little water and stop when cooked to your liking. Vitamin C can be lost with heat and water, especially during prolonged boiling. Retention varies by vegetable.', why:'Limit water and prolonged heating to help retain vitamin C.', source:'vitaminC'};
  if (g==='05') return {method:'Enjoy fresh, when suitable', text:'For fruits normally eaten raw, wash and eat fresh to avoid cooking losses of vitamin C. Juice and cooked fruit have different profiles; use the entry matching what you eat.', why:'Vitamin C is sensitive to heat and storage.', source:'vitaminC'};
  if (['07','08','09'].includes(g)) return {method:'Cook to a safe temperature', text:'Use a food thermometer and the USDA temperature chart for the exact meat, fish or egg dish. Match your nutrient entry to the cooked food and its actual edible weight.', why:'Food safety comes first; there is no universal best cooking method.', source:'safety'};
  if (requiresCooking(f)) return {method:'Cook before eating', text:'This is an uncooked staple. Follow a reliable recipe and choose its matching cooked entry when weighing the finished food. There is not enough food-specific evidence here to rank all preparation methods.', why:'No cooking yield or nutrient retention is guessed.'};
  return {method:'Match the food you eat', text:'Use the preparation described in your selected entry. There is not enough specific evidence in this app to name one best method for this food.', why:'Recorded variants can differ in water, variety and added ingredients.'};
}

export function spiceSuggestions(items, foods) {
  const selected = items.map(r=>foods.find(f=>f.id===r.id)).filter(Boolean);
  const names = selected.map(f=>f.name).join(' ').toLowerCase();
  const blend = (id,title,ids,text,how,limited=false) => ({id,title,foods:ids.map(id=>foods.find(f=>f.id===id)).filter(Boolean),text,how,limited,source:limited?'turmeric':'spices'});
  const out=[];
  if(selected.some(f=>/^Broccoli,/i.test(f.name))) out.push({...blend('mustard','Mustard seed + black pepper',['060010','140002'],'A small human study found that ground brown mustard seed added to cooked broccoli increased sulforaphane availability. Black pepper is an optional flavor partner; it was not part of the tested effect.','Grind raw brown mustard seeds and add after cooking the broccoli. Finish with black pepper to taste.'),source:'mustard',evidence:'Small human study · mustard only'});
  if(selected.some(f=>group(f)==='03')) out.push(blend('warm','Ginger + coriander',['140015','140010'],'A warm match for lentils, beans and chickpeas. Using these instead of extra salt adds flavor without adding salt.','Crush coriander seeds; stir into the cooking liquid with ground ginger.'));
  if(/tomato|vegetable|kale|carrot|fish|chicken/.test(names)||selected.some(f=>group(f)==='04')) out.push(blend('herby','Basil + oregano',['140019','140030'],'A simple match for vegetables and tomato-based dishes. The practical nutritional benefit is replacing some added salt.','Stir dried herbs into the dish and adjust to taste.'));
  if(selected.some(f=>group(f)==='01'||group(f)==='10'||(group(f)==='05'&&/banana|apple|pear|mango|date|peach|plum/.test(base(f).toLowerCase())))) out.push(blend('sweet','Cinnamon + cardamom',['140008','140003'],'A fragrant option for porridge, fruit or plain yoghurt. Use for flavor; a nutritional synergy between these spices is not established.','Crush cardamom seeds and add a small pinch with cinnamon.'));
  out.push(blend('golden','Turmeric + black pepper',['140023','140002'],'Piperine is used in some curcumin supplements, but a pinch of these spices has no proven meal-wide absorption or health benefit. Enjoy this combination for flavor.','Stir small amounts into a savory dish; this is culinary seasoning, not a supplement dose.',true));
  return out.slice(0,3);
}

export function defaultPortion(f) { return portion(f); }
