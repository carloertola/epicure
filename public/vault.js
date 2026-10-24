export const VAULT_KEY='gursha-private-v1';
const encoder=new TextEncoder(),decoder=new TextDecoder();
const ITERATIONS=310000,MAX_BYTES=10*1024*1024;
export const emptyJournal=()=>({version:1,meals:[],entries:[]});
const b64=bytes=>{let text='';for(let i=0;i<bytes.length;i+=8192)text+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(text);};
const unb64=text=>Uint8Array.from(atob(text),c=>c.charCodeAt(0));
export function parseEnvelope(text){
  if(typeof text!=='string'||text.length>MAX_BYTES*1.5)throw Error('This backup is too large.');
  const e=JSON.parse(text);
  if(e?.app!=='Gursha'||e.version!==1||e.algorithm!=='AES-GCM'||e.kdf!=='PBKDF2-SHA256'||!Number.isInteger(e.iterations)||e.iterations<ITERATIONS||e.iterations>1000000||typeof e.salt!=='string'||typeof e.iv!=='string'||typeof e.ciphertext!=='string'||unb64(e.salt).length!==16||unb64(e.iv).length!==12||unb64(e.ciphertext).length<16)throw Error('This is not a supported Gursha encrypted backup.');
  return e;
}
export function validateJournal(data){
  if(data?.version!==1||!Array.isArray(data.meals)||!Array.isArray(data.entries)||data.meals.length>500||data.entries.length>10000)throw Error('This journal has an invalid format or is too large.');
  const validItems=items=>Array.isArray(items)&&items.length>0&&items.length<=30&&items.every(r=>r&&/^\d{6}$/.test(r.id)&&/^\d{6}$/.test(r.ingredientId)&&Number.isFinite(r.grams)&&r.grams>0&&r.grams<=60000&&typeof r.knownProfile==='boolean');
  const validNutrition=n=>n?.values&&n.missing&&n.flagged&&Object.keys(n.values).length<=50&&Object.entries(n.values).every(([k,v])=>/^[a-z_0-9]+$/.test(k)&&Number.isFinite(v)&&v>=0&&v<1e12)&&[n.missing,n.flagged].every(values=>Object.values(values).every(v=>Number.isInteger(v)&&v>=0&&v<=30));
  for(const m of data.meals){
    if(typeof m?.id!=='string'||typeof m.title!=='string'||!m.title.trim()||m.title.length>120||!Array.isArray(m.people)||!m.people.length||m.people.length>12||!validItems(m.ingredients)||!Array.isArray(m.steps)||m.steps.length>40||!Array.isArray(m.rows)||m.rows.length!==m.ingredients.length||!Array.isArray(m.equipment)||!Array.isArray(m.pairings)||!Number.isFinite(m.share)||m.share<.1||m.share>1||!validNutrition(m.nutrition))throw Error('A saved meal is invalid.');
    if(m.people.some(p=>!p?.person||!['male','female'].includes(p.person.sex)||!['adult','kid'].includes(p.person.type)||!Number.isInteger(p.person.age)||p.person.age<2||p.person.age>120||typeof p.person.label!=='string'||!p.daily||!['children','adults'].includes(p.daily.source)||!validItems(p.items))||m.steps.some(s=>typeof s?.title!=='string'||typeof s.text!=='string'||s.text.length>5000)||m.rows.some(r=>!/^\d{6}$/.test(r?.ingredientId)||(r.profileId!==null&&!/^\d{6}$/.test(r.profileId))||!r.reference||typeof r.reference.group!=='string'||typeof r.method!=='string'))throw Error('A saved meal has invalid portions or preparation steps.');
  }
  for(const e of data.entries)if(typeof e?.id!=='string'||typeof e.personKey!=='string'||!e.personKey||e.personKey.length>40||typeof e.personLabel!=='string'||e.personLabel.length>40||typeof e.title!=='string'||e.title.length>120||!/^\d{4}-\d{2}-\d{2}$/.test(e.date)||Number.isNaN(Date.parse(e.date+'T12:00:00Z'))||!validNutrition(e.nutrition)||!Number.isInteger(e.ingredientCount)||e.ingredientCount<1||e.ingredientCount>30||!Number.isFinite(e.fraction)||e.fraction<=0||e.fraction>5)throw Error('An intake entry is invalid.');
  return data;
}
async function derive(passphrase,salt,iterations){
  const material=await crypto.subtle.importKey('raw',encoder.encode(passphrase),'PBKDF2',false,['deriveKey']);
  return crypto.subtle.deriveKey({name:'PBKDF2',salt,iterations,hash:'SHA-256'},material,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);
}
export class PrivateJournal{
  constructor(storage=globalThis.localStorage){this.storage=storage;this.key=null;this.data=null;this.raw=null;this.salt=null;this.iterations=ITERATIONS;}
  exists(){return!!this.storage.getItem(VAULT_KEY);}
  get unlocked(){return!!this.key&&!!this.data;}
  async create(passphrase){
    if(this.exists())throw Error('A journal already exists. Unlock it instead.');
    if(passphrase.length<12)throw Error('Use a passphrase of at least 12 characters.');
    this.salt=crypto.getRandomValues(new Uint8Array(16));this.key=await derive(passphrase,this.salt,ITERATIONS);this.data=emptyJournal();this.raw=null;
    try{await this.save();}catch(e){this.lock();throw e;}
  }
  async decode(text,passphrase){
    const envelope=parseEnvelope(text),salt=unb64(envelope.salt),key=await derive(passphrase,salt,envelope.iterations);
    let plain;try{plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:unb64(envelope.iv)},key,unb64(envelope.ciphertext));}catch{throw Error('The passphrase is incorrect, or this backup is damaged.');}
    return{key,salt,iterations:envelope.iterations,data:validateJournal(JSON.parse(decoder.decode(plain)))};
  }
  async unlock(passphrase){
    const raw=this.storage.getItem(VAULT_KEY);if(!raw)throw Error('Create a journal first.');
    const decoded=await this.decode(raw,passphrase);Object.assign(this,decoded,{raw});
  }
  async save(){
    if(!this.unlocked)throw Error('Unlock your private journal first.');
    validateJournal(this.data);const plain=encoder.encode(JSON.stringify(this.data));if(plain.length>MAX_BYTES)throw Error('Your journal is full. Export a backup before removing older entries.');
    const expected=this.raw,iv=crypto.getRandomValues(new Uint8Array(12)),cipher=await crypto.subtle.encrypt({name:'AES-GCM',iv},this.key,plain);
    const raw=JSON.stringify({app:'Gursha',version:1,algorithm:'AES-GCM',kdf:'PBKDF2-SHA256',iterations:this.iterations,salt:b64(this.salt),iv:b64(iv),ciphertext:b64(new Uint8Array(cipher))});
    const commit=()=>{if(this.storage.getItem(VAULT_KEY)!==expected)throw Error('This journal changed in another tab. Lock and unlock it before saving again.');this.storage.setItem(VAULT_KEY,raw);this.raw=raw;};
    if(globalThis.navigator?.locks)await navigator.locks.request('gursha-journal-write',commit);else commit();
  }
  async importBackup(text,passphrase){
    const decoded=await this.decode(text,passphrase),previous={key:this.key,data:this.data,salt:this.salt,iterations:this.iterations,raw:this.raw};
    Object.assign(this,decoded,{raw:this.storage.getItem(VAULT_KEY)});
    try{await this.save();}catch(e){Object.assign(this,previous);throw e;}
  }
  exportBackup(){if(!this.unlocked)throw Error('Unlock your journal before exporting.');if(!this.raw)throw Error('Save your journal first.');return this.raw;}
  lock(){this.key=null;this.data=null;this.salt=null;this.raw=null;}
}
