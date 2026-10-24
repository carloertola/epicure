import test from 'node:test';import assert from 'node:assert/strict';
import {PrivateJournal,VAULT_KEY,parseEnvelope} from '../public/vault.js';
class MemoryStore{constructor(){this.map=new Map();}getItem(key){return this.map.get(key)??null;}setItem(key,value){this.map.set(key,value);}removeItem(key){this.map.delete(key);}}
const pass='Test only long passphrase 2026';
const entry={id:'test-entry',title:'Private tomato meal',personKey:'me',personLabel:'Me',date:'2026-10-25',ingredientCount:1,fraction:1,nutrition:{values:{energy_kcal:250},missing:{energy_kcal:0},flagged:{energy_kcal:0}}};
test('journal encrypts records, locks, and rejects wrong passwords and tampering',async()=>{
  const storage=new MemoryStore(),journal=new PrivateJournal(storage);await journal.create(pass);journal.data.entries.push(entry);await journal.save();const raw=storage.getItem(VAULT_KEY);
  assert.ok(!raw.includes('Private tomato'));assert.ok(!raw.includes(pass));assert.equal(parseEnvelope(raw).algorithm,'AES-GCM');journal.lock();assert.equal(journal.data,null);assert.equal(journal.key,null);
  await assert.rejects(()=>journal.unlock('incorrect passphrase'),/incorrect/);await journal.unlock(pass);assert.equal(journal.data.entries[0].title,entry.title);
  const envelope=JSON.parse(raw);envelope.ciphertext=(envelope.ciphertext[0]==='A'?'B':'A')+envelope.ciphertext.slice(1);await assert.rejects(()=>journal.decode(JSON.stringify(envelope),pass),/incorrect|damaged/);
});
test('every save uses a fresh nonce and backups restore only with the correct passphrase',async()=>{
  const store=new MemoryStore(),journal=new PrivateJournal(store);await journal.create(pass);const first=JSON.parse(journal.exportBackup());await journal.save();const second=JSON.parse(journal.exportBackup());assert.notEqual(first.iv,second.iv);
  journal.data.entries.push(entry);await journal.save();const backup=journal.exportBackup(),restored=new PrivateJournal(new MemoryStore());await restored.importBackup(backup,pass);assert.equal(restored.data.entries.length,1);
  const previous=restored.exportBackup();await assert.rejects(()=>restored.importBackup(backup,'wrong password'));assert.equal(restored.exportBackup(),previous);
});
test('concurrent tabs cannot silently overwrite a newer journal',async()=>{
  const store=new MemoryStore(),one=new PrivateJournal(store);await one.create(pass);const two=new PrivateJournal(store);await two.unlock(pass);one.data.entries.push(entry);await one.save();await assert.rejects(()=>two.save(),/another tab/);await two.unlock(pass);assert.equal(two.data.entries.length,1);
});
test('invalid backups and weak new passphrases are rejected',async()=>{
  const j=new PrivateJournal(new MemoryStore());await assert.rejects(()=>j.create('short'),/12/);assert.throws(()=>parseEnvelope('{}'),/supported/);assert.throws(()=>parseEnvelope('x'.repeat(16*1024*1024)),/large/);
});
