import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {dailyServes,servingReference,allocatePortions,validatePeople} from '../public/portions.js';
import {generatePlan,methodsFor,recordedProfile,estimateNutrition,periodRange,aggregateEntries} from '../public/planner.js';
const db=JSON.parse(fs.readFileSync(new URL('../public/data/foods.json',import.meta.url))),foods=db.foods,f=id=>foods.find(f=>f.id===id);
const people=[{type:'adult',age:30,sex:'female'},{type:'kid',age:8,sex:'male'}];
test('age and sex serving references preserve boundaries and child categories',()=>{
  assert.equal(dailyServes({age:3,sex:'male'}).protein,1);assert.equal(dailyServes({age:8,sex:'female'}).dairy,1.5);assert.equal(dailyServes({age:8,sex:'male'}).dairy,2);
  assert.equal(dailyServes({age:11,sex:'male'}).grains,5);assert.equal(dailyServes({age:12,sex:'male'}).grains,6);assert.equal(dailyServes({age:18,sex:'female'}).grains,7);assert.equal(dailyServes({age:19,sex:'female'}).grains,6);
  assert.equal(dailyServes({age:70,sex:'male'}).vegetables,5.5);assert.equal(dailyServes({age:71,sex:'male'}).vegetables,5);
  assert.throws(()=>dailyServes({age:1,sex:'female'}));assert.equal(validatePeople([{age:8,type:'adult',sex:'male'}]),false);assert.equal(validatePeople(people),true);
});
test('portion allocation divides a group across ingredients without doubling recommended serves',()=>{
  const rows=['040030','040005'].map(id=>({food:f(id),profile:f(id),reference:servingReference(f(id))}));
  const result=allocatePortions(rows,people,1/3);
  assert.equal(result[0].items.reduce((s,r)=>s+r.grams,0),125);assert.equal(result[1].items.reduce((s,r)=>s+r.grams,0),112.6);
  assert.throws(()=>allocatePortions([{food:f('010103'),profile:null,reference:{group:'manual',grams:null}}],people,1/3),/Enter a portion/);
});
test('manual portions and legumes are never silently counted as another food group',()=>{
  assert.equal(servingReference(f('030073')).group,'protein');assert.equal(servingReference(f('010103')).group,'manual');
  const rows=[{food:f('010103'),profile:null,reference:{group:'manual',grams:null},customGrams:80}];
  assert.deepEqual(allocatePortions(rows,people).map(p=>p.items[0].grams),[80,80]);
});
test('equipment rules block raw beans without cooking and fermentation without both tools',()=>{
  assert.deepEqual(methodsFor(f('030029'),[]),[]);assert.ok(methodsFor(f('030029'),['stove']).some(m=>m.id==='boil'));
  assert.ok(!methodsFor(f('010103'),['fermentation']).some(m=>m.id==='ferment'));assert.ok(methodsFor(f('010103'),['fermentation','stove']).some(m=>m.id==='ferment'));
});
test('cooked profile matching preserves animal part and food descriptors',()=>{
  const lean=f('070002');assert.ok(lean);
  const profile=recordedProfile(lean,'boil',foods);assert.ok(profile);assert.match(profile.name,/assorted parts, lean/);assert.doesNotMatch(profile.name,/kidney|brain|liver/);
  const kidney=foods.find(f=>/^Beef, kidney, raw$/.test(f.name));const cooked=recordedProfile(kidney,'boil',foods);assert.ok(cooked);assert.match(cooked.name,/kidney/);
});
test('unavailable processed profiles remain unknown in totals and plans',()=>{
  const draft={people,ingredients:['040030'],equipment:['steamer'],methods:{'040030':'steam'},share:1/3};
  const result=generatePlan(draft,foods,db.components);assert.equal(result.ingredients[0].knownProfile,false);assert.equal(result.nutrition.missing.energy_kcal,1);assert.equal(result.nutrition.values.energy_kcal,0);
  const t=estimateNutrition([{id:'040030',grams:100,knownProfile:false}],foods,['iron']);assert.equal(t.missing.iron,1);
});
test('known kilojoules are converted to kcal transparently without altering the source',()=>{
  const avocado=f('050003');assert.equal(avocado.nutrients.energy_kcal,null);
  const t=estimateNutrition([{id:avocado.id,grams:100,knownProfile:true}],foods,['energy_kcal']);
  assert.equal(t.values.energy_kcal,644/4.184);assert.equal(t.missing.energy_kcal,0);assert.equal(t.derived.energy_kcal,1);assert.equal(avocado.nutrients.energy_kcal,null);
});
test('planner scales the household batch and rejects incomplete or unsafe choices',()=>{
  const draft={people,ingredients:['030073','040030'],equipment:[],share:1/3};const result=generatePlan(draft,foods,db.components);
  for(const row of result.ingredients)assert.ok(Math.abs(row.grams-result.people.reduce((s,p)=>s+p.items.find(i=>i.ingredientId===row.ingredientId).grams,0))<.01);
  assert.throws(()=>generatePlan({...draft,ingredients:['030029']},foods,db.components),/equipment/);assert.throws(()=>generatePlan({...draft,people:[{age:1,type:'kid',sex:'female'}]},foods,db.components));
  const wine=foods.find(f=>/^Wine,/.test(f.name));if(wine)assert.throws(()=>generatePlan({...draft,ingredients:[wine.id]},foods,db.components),/alcoholic/);
});
test('journal periods use calendar weeks/months and filter individual profiles',()=>{
  assert.deepEqual(periodRange('2026-10-25','week'),{start:'2026-10-19',end:'2026-10-25'});assert.deepEqual(periodRange('2024-02-10','month'),{start:'2024-02-01',end:'2024-02-29'});assert.deepEqual(periodRange('2026-10-25','year'),{start:'2026-01-01',end:'2026-12-31'});
  const nutrition={values:{energy_kcal:100,iron:2},missing:{iron:1},flagged:{iron:0}};const entries=[{date:'2026-10-20',personKey:'me',nutrition},{date:'2026-10-25',personKey:'other',nutrition},{date:'2026-11-01',personKey:'me',nutrition}];
  const t=aggregateEntries(entries,'2026-10-01','2026-10-31','me');assert.equal(t.count,1);assert.equal(t.values.energy_kcal,100);assert.equal(t.missing.iron,1);
});
