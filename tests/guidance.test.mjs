import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {pairingAdvice, preparationAdvice, spiceSuggestions, nutrient} from '../public/guidance.js';
const {foods}=JSON.parse(fs.readFileSync(new URL('../public/data/foods.json',import.meta.url)));
const plate=(...ids)=>ids.map(id=>({id,grams:100}));
test('finds both supported interactions in the example meal',()=>{
  const advice=pairingAdvice(plate('030073','040030','050003'),foods);
  assert.deepEqual(advice.map(a=>a.key),['iron','fat']);
  assert.ok(advice.every(a=>a.pair[0].id!==a.pair[1].id));
});
test('a tiny vitamin C portion is not presented as an established selected pairing',()=>{
  const advice=pairingAdvice([{id:'030073',grams:100},{id:'040030',grams:1}],foods);
  assert.ok(!advice.some(a=>a.key==='iron'));
  const addition=advice.find(a=>a.key==='iron-add');
  assert.ok(addition.add);
  assert.ok(!['030073','040030'].includes(addition.add.id));
});
test('missing and anomalous nutrient values do not trigger synergy claims',()=>{
  const example=[{id:'030001',groupId:'03',name:'Bean, boiled',nutrients:{iron:20},quality:{iron:['source-anomaly']}},{id:'050001',groupId:'05',name:'Orange, raw',nutrients:{vitamin_c:50}}];
  assert.equal(nutrient(example[0],'iron'),0);
  assert.equal(nutrient(example[0],'fat'),0);
  assert.deepEqual(pairingAdvice(plate('030001','050001'),example),[]);
  assert.deepEqual(pairingAdvice([],foods),[]);
});
test('one food is never paired with itself',()=>{
  const f={id:'040001',groupId:'04',name:'Vegetable, raw',nutrients:{iron:3,vitamin_c:50,beta_carotene:900,fat:5}};
  assert.deepEqual(pairingAdvice(plate(f.id),[f]),[]);
});
test('preparation matches the actual ingredient rather than words in a recipe',()=>{
  const food=id=>foods.find(f=>f.id===id);
  assert.equal(preparationAdvice(food('030029')).source,'beans');
  assert.equal(preparationAdvice(food('060008')).method,'Grind or crush');
  assert.equal(preparationAdvice(food('010103')).method,'Ferment, then cook');
  assert.equal(preparationAdvice(food('040030')).source,'tomato');
  const beefKidney=foods.find(f=>/^Beef, kidney, raw/.test(f.name));
  assert.equal(preparationAdvice(beefKidney).source,'safety');
});
test('spice pairings fit savory ingredients and retain the evidence limitation',()=>{
  const suggestions=spiceSuggestions(plate('030073','040030','050003'),foods);
  assert.ok(suggestions.some(b=>b.id==='warm'));
  assert.ok(suggestions.some(b=>b.id==='herby'));
  assert.ok(!suggestions.some(b=>b.id==='sweet'));
  const turmeric=suggestions.find(b=>b.id==='golden');
  assert.equal(turmeric.limited,true);
  for(const b of suggestions)assert.equal(b.foods.length,2);
});
test('the mustard recommendation is specific to broccoli and explains what was tested',()=>{
  const suggestion=spiceSuggestions(plate('040037'),foods).find(b=>b.id==='mustard');
  assert.equal(suggestion.source,'mustard');
  assert.deepEqual(suggestion.foods.map(f=>f.id),['060010','140002']);
  assert.match(suggestion.text,/not part of the tested effect/);
  assert.ok(!spiceSuggestions(plate('040030'),foods).some(b=>b.id==='mustard'));
});
