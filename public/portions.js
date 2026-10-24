import {base,group,requiresCooking} from './engine.js';

export const PORTION_SOURCES={
  adults:['Adult daily serves · Australian Government','https://www.eatforhealth.gov.au/food-essentials/how-much-do-we-need-each-day/recommended-number-serves-adults'],
  children:['Children’s daily serves · Australian Government','https://www.eatforhealth.gov.au/food-essentials/how-much-do-we-need-each-day/recommended-number-serves-children-adolescents-and-toddlers'],
  sizes:['Standard serving sizes · Australian Government','https://www.eatforhealth.gov.au/food-essentials/how-much-do-we-need-each-day/serve-sizes'],
};
export const FOOD_GROUP_LABELS={vegetables:'Vegetables',fruit:'Fruit',grains:'Grains',protein:'Protein foods',dairy:'Dairy & alternatives',oil:'Unsaturated oils',seasoning:'Seasoning',manual:'Custom portion'};
// Daily standard serves. Columns: vegetables, fruit, grains, protein foods, dairy.
const childBands=[
  {min:2,max:3,male:[2.5,1,4,1,1.5],female:[2.5,1,4,1,1.5]},
  {min:4,max:8,male:[4.5,1.5,4,1.5,2],female:[4.5,1.5,4,1.5,1.5]},
  {min:9,max:11,male:[5,2,5,2.5,2.5],female:[5,2,4,2.5,3]},
  {min:12,max:13,male:[5.5,2,6,2.5,3.5],female:[5,2,5,2.5,3.5]},
  {min:14,max:18,male:[5.5,2,7,2.5,3.5],female:[5,2,7,2.5,3.5]},
];
const adultBands=[
  {min:19,max:50,male:[6,2,6,3,2.5],female:[5,2,6,2.5,2.5]},
  {min:51,max:70,male:[5.5,2,6,2.5,2.5],female:[5,2,4,2,4]},
  {min:71,max:120,male:[5,2,4.5,2.5,3.5],female:[5,2,3,2,4]},
];
export function validatePeople(people){
  return Array.isArray(people)&&people.length>0&&people.length<=12&&people.every(p=>Number.isInteger(Number(p.age))&&Number(p.age)>=2&&Number(p.age)<=120&&['male','female'].includes(p.sex)&&['kid','adult'].includes(p.type)&&((p.type==='kid'&&p.age<18)||(p.type==='adult'&&p.age>=18)));
}
export function dailyServes(person){
  const age=Number(person.age),band=[...childBands,...adultBands].find(b=>age>=b.min&&age<=b.max);
  if(!band||!['male','female'].includes(person.sex))throw Error('Choose a valid age (2–120) and nutrition reference.');
  const row=band[person.sex];
  const oil=age<=3?4.5:age<=11?8.5:age<=13?13:age<=18?17:person.sex==='male'&&age<70?34:17;
  return {...Object.fromEntries(['vegetables','fruit','grains','protein','dairy'].map((k,i)=>[k,row[i]])),oil,band:`${band.min}–${band.max===120?'older':band.max}`,source:age<=18?'children':'adults'};
}
export function servingReference(f,{cooked=false}={}){
  const n=base(f).toLowerCase(),g=group(f),cookedState=cooked||!requiresCooking(f)&&/boiled|cooked|roasted|baked|fried|grilled|stew|porridge/i.test(f.name);
  const manual={group:'manual',grams:null,basis:'No matching standard serve. Enter an edible gram amount per diner.'};
  if(/garlic|ginger|chilli|chili/.test(n)||g==='14')return{group:'seasoning',grams:1,basis:'Culinary starting amount, not a recommended nutrient serving.'};
  if(n==='avocado')return{group:'seasoning',grams:30,basis:'Optional culinary amount; avocado is not counted as a fruit serving in this plan.'};
  if(/stew|sauce|salad from|samosa|cake|biscuit|ferfer|chechebsa|fetfet|chukame|ice cream/i.test(f.name))return manual;
  if(g==='01'){
    if(/bread|enjera|injera/.test(n))return{group:'grains',grams:40,basis:'40 g bread/flatbread standard serve; applied as a planning proxy to injera.'};
    if(/porridge/.test(f.name))return{group:'grains',grams:120,basis:'120 g cooked porridge per standard serve.'};
    if(cookedState&&!/flour|bran/.test(n))return{group:'grains',grams:100,basis:'100 g cooked grain per serve, a planning choice within the published 75–120 g range.'};
    return manual;
  }
  if(['02','04'].includes(g)&&!/flour|dried|powder/.test(f.name))return{group:'vegetables',grams:75,basis:'75 g edible vegetables per standard serve.'};
  if(g==='05'&&!/juice|dry|dried/.test(f.name))return{group:'fruit',grams:150,basis:'150 g fresh fruit per standard serve.'};
  if(g==='03')return cookedState&&!/flour|roasted/.test(f.name)?{group:'protein',grams:150,basis:'150 g cooked legumes per protein-food serve; not also counted as vegetables.'}:manual;
  if(g==='06')return{group:'protein',grams:30,basis:'30 g nuts/seeds per occasional protein-food serve. Grind for young children.'};
  if(n==='tofu')return{group:'protein',grams:170,basis:'170 g tofu per standard protein-food serve.'};
  if(g==='07'&&!/liver|kidney|heart|tongue|brain|tripe|sausage|fatty/.test(f.name)){
    const poultry=/chicken|turkey|duck|poultry/.test(n);return{group:'protein',grams:cookedState?(poultry?80:65):(poultry?100:95),basis:cookedState?`${poultry?80:65} g cooked lean ${poultry?'poultry':'red meat'} per serve.`:`${poultry?100:95} g raw lean meat per serve; raw/cooked weights are not interchangeable.`};
  }
  if(g==='08')return{group:'protein',grams:120,basis:'120 g edible egg (about two large eggs) per standard serve.'};
  if(g==='09')return{group:'protein',grams:cookedState?100:115,basis:`${cookedState?100:115} g ${cookedState?'cooked':'raw'} fish per standard serve.`};
  if(g==='10'&&/yoghurt|yogurt/.test(n))return{group:'dairy',grams:200,basis:'200 g yoghurt per standard dairy serve.'};
  if(g==='10'&&/cheese/.test(n))return{group:'dairy',grams:/ricotta/.test(n)?120:40,basis:'40 g hard cheese or 120 g ricotta per standard serve; check the selected type.'};
  if(g==='11'&&n==='oil')return{group:'oil',grams:1,basis:'Age/sex oil allowance in grams, using the midpoint of the published range.'};
  return manual;
}

export function allocatePortions(rows,people,share=1/3){
  if(!validatePeople(people))throw Error('Complete each diner’s age and nutrition reference.');
  if(!Number.isFinite(share)||share<.1||share>1)throw Error('Choose a meal share between 10% and 100%.');
  const counts={};for(const row of rows){const r=row.reference;if(r.group!=='manual'&&r.group!=='seasoning')counts[r.group]=(counts[r.group]||0)+1;}
  return people.map((person,index)=>{
    const daily=dailyServes(person);
    const items=rows.map(row=>{
      const ref=row.reference;
      let grams,standardServes=null;
      if(ref.group==='manual')grams=Number(row.customGrams);
      else if(ref.group==='seasoning')grams=ref.grams*(person.age<9?.5:1);
      else{standardServes=daily[ref.group]*share/counts[ref.group];grams=standardServes*ref.grams;}
      if(!Number.isFinite(grams)||grams<=0||grams>5000)throw Error(`Enter a portion between 0.1 and 5,000 g for ${base(row.food)}.`);
      return{id:row.profile?.id||row.food.id,ingredientId:row.food.id,grams:Math.round(grams*10)/10,standardServes,knownProfile:!!row.profile};
    });
    return{person:{...person,age:Number(person.age),label:`Diner ${index+1}`},daily,items};
  });
}
