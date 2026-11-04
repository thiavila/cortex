const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../skills/tarefas/app/local-adapter.js'), 'utf8');
function client(handler, options = {}) {
  const requests = [], saved = options.saved || new Map(); let cleared = false;
  const window = { CORTEX_LOCAL: { board: 'board-one', api: '/api', rememberAuth: !!options.persistent }, addEventListener() {} };
  vm.runInNewContext(source, { window, location: { hash: options.hash === undefined ? '#token=test-secret' : options.hash, pathname: '/', search: '' },
    history: { replaceState() { cleared = true; } }, URLSearchParams, setTimeout, clearTimeout,
    localStorage: { getItem: k => saved.get(k), setItem: (k, v) => saved.set(k, v) },
    sessionStorage: { getItem: k => saved.get(k), setItem: (k, v) => saved.set(k, v) },
    crypto: require('node:crypto').webcrypto,
    fetch: async (url, options) => {
      const body = JSON.parse(options.body); requests.push(body);
      const result = await handler(body, options.headers.Authorization);
      return { status: result.error?.code === 'unauthorized' ? 401 : result.error ? 400 : 200, ok: !result.error, json: async () => result };
    },
  });
  return { window, requests, cleared: () => cleared };
}
const schema = { id: 'schema', exists: true, version: 1, data: { versao: 4 } };
test('pagination keeps all documents and auth token is removed from visible URL', async () => {
  const c = client(r => r.op === 'get' ? schema : r.cursor ?
    { docs: [{ id: 'b', exists: true, version: 2, data: { titulo: 'B' } }], next_cursor: null } :
    { docs: [{ id: 'a', exists: true, version: 1, data: { titulo: 'A' } }], next_cursor: 'next' });
  const db = await c.window.cortexLocal.ready();
  const rows = await db.collection('tasks').get();
  assert.deepEqual(Array.from(rows.docs, d => d.id), ['a', 'b']);
  assert.equal(rows.docs[1].data().titulo, 'B');
  assert.equal(c.cleared(), true);
});
test('update uses observed version, reports conflict and does not silently retry', async () => {
  const c = client(r => r.collection === 'config' ? schema : r.op === 'get' ?
    { id: 'a', exists: true, version: 3, data: { titulo: 'A' } } :
    { error: { code: 'conflict', message: 'stale version' } });
  const db = await c.window.cortexLocal.ready(), ref = db.doc('tasks/a');
  await ref.get();
  await assert.rejects(ref.update({ titulo: 'B' }), e => e.code === 'conflict');
  const writes = c.requests.filter(r => r.op === 'update');
  assert.equal(writes.length, 1); assert.equal(writes[0].if_version, 3);
  assert.ok(writes[0].mutation_id);
});
test('set is create-only and subscription can be cancelled', async () => {
  const c = client(r => r.collection === 'config' ? schema :
    { id: 'new', exists: r.op === 'set', version: r.op === 'set' ? 1 : 0, data: r.data || null });
  const db = await c.window.cortexLocal.ready();
  await db.doc('tasks/new').set({ titulo: 'New' });
  assert.equal(Object.hasOwn(c.requests.find(r => r.op === 'set'), 'if_version'), false);
  let stop;
  await new Promise((resolve, reject) => {
    stop = db.doc('tasks/new').onSnapshot(s => { assert.equal(s.id, 'new'); resolve(); }, reject);
  });
  stop();
});
test('snapshot data is copied instead of exposing the version cache to optimistic UI changes', async () => {
  const c = client(r => r.collection === 'config' ? schema :
    { id: 'a', exists: true, version: 1, data: { tags: ['original'] } });
  const db = await c.window.cortexLocal.ready();
  const s = await db.doc('tasks/a').get();
  s.data().tags.push('mutated');
  assert.equal(s.data().tags.length, 1);
});

test('persistent authorization survives new tabs and stale bookmark fragments', async () => {
  const saved = new Map();
  let seen=[];
  const handler=(req,auth)=>{seen.push(auth);return auth==='Bearer test-secret'?schema:{error:{code:'unauthorized'}};};
  await client(handler,{persistent:true,saved}).window.cortexLocal.ready();
  assert.equal(saved.get('cortex-token:board-one'),'test-secret');
  await client(handler,{persistent:true,saved,hash:''}).window.cortexLocal.ready();
  seen=[];
  await client(handler,{persistent:true,saved,hash:'#token=expired'}).window.cortexLocal.ready();
  assert.deepEqual(seen,['Bearer expired','Bearer test-secret']);
  assert.equal(saved.get('cortex-token:board-one'),'test-secret');
});
test('a rejected bootstrap credential is never persisted', async()=>{
 const saved=new Map();
 const c=client(()=>({error:{code:'unauthorized'}}),{persistent:true,saved});
 await assert.rejects(c.window.cortexLocal.ready());
 assert.equal(saved.size,0);
});


test('queued edits advance across own writes but never across an external version', async () => {
  let version = 1;
  const c = client(r => {
    if (r.collection === 'config') return schema;
    if (r.op === 'get') return { id:'a', exists:true, version, data:{ titulo:'A' } };
    if (r.if_version !== version) return {error:{code:'conflict'}};
    return {id:'a', exists:true, version:++version, data:r.data};
  });
  const db = await c.window.cortexLocal.ready();
  const first = db.doc('tasks/a'), second = db.doc('tasks/a'), third = db.doc('tasks/a');
  await Promise.all([first.get(), second.get(), third.get()]);
  await first.update({titulo:'B'});
  await second.update({status:'fazendo'});
  version++; // Another client writes: the queued stale reference must fail.
  await assert.rejects(third.update({titulo:'Stale'}), e=>e.code==='conflict');
  assert.deepEqual(c.requests.filter(r=>r.op==='update').map(r=>r.if_version),[1,2,3]);
});

test('revision conflict restarts the whole collection without mixing pages', async () => {
  let reads=0;
  const c=client(r=>{
    if(r.collection==='config') return schema;
    reads++;
    if(reads===1) return {docs:[{id:'old',version:1,data:{}}],next_cursor:'old-cursor'};
    if(reads===2) return {error:{code:'conflict'}};
    return {docs:[{id:'current',version:2,data:{}}],next_cursor:null};
  });
  const db=await c.window.cortexLocal.ready();
  const rows=await db.collection('tasks').get();
  assert.deepEqual(Array.from(rows.docs,x=>x.id),['current']);
  assert.equal(reads,3);
});

test('subscription republishes the same snapshot after a transient failure', async()=>{
 let fail=false, recovered=false;
 const c=client(r=>r.collection==='config'?schema:fail?{error:{code:'unavailable'}}:{id:'a',exists:true,version:1,data:{}});
 const db=await c.window.cortexLocal.ready();
 let stop;
 await new Promise((resolve,reject)=>{
   const deadline=setTimeout(()=>{stop();reject(new Error('recovery timed out'));},4000);
   let hits=0;
   stop=db.doc('tasks/a').onSnapshot(()=>{
     hits++;
     if(hits===1){fail=true;db.refresh();}
     else {recovered=true;stop();clearTimeout(deadline);resolve();}
   },()=>{fail=false;db.refresh();});
 });
 assert.equal(recovered,true);
});

test('deleting a parent clears both child relationships in sequential versioned writes', async()=>{
 const records=new Map([['parent',{version:1,data:{titulo:'Parent',historico:[]}}],
   ['child',{version:1,data:{titulo:'Child',pai:'parent',relacionadas:['parent'],historico:[]}}]]);
 const c=client(r=>{
   if(r.collection==='config')return schema;
   const row=records.get(r.id);
   if(r.op==='get')return {id:r.id,exists:!!row,version:row?.version||0,data:row?.data};
   if(r.if_version!==row?.version)return {error:{code:'conflict'}};
   row.version++;
   row.data=r.op==='delete'?null:{...row.data,...r.data};
   return {id:r.id,exists:r.op!=='delete',version:row.version,data:row.data};
 });
 const db=await c.window.cortexLocal.ready();
 await db.doc('tasks/parent').get();await db.doc('tasks/child').get();
 const tasks=Array.from(records,([id,row])=>({id,...row.data}));
 const board=fs.readFileSync(path.join(__dirname,'../skills/tarefas/app/board-src.html'),'utf8');
 const context=vm.createContext({db,tasks,canWrite:true,ui:{},byId:id=>tasks.find(x=>x.id===id),
   nowIso:()=>new Date().toISOString(),HIST_MAX:100,projetosOf:()=>[],render(){},toast(){},t:x=>x});
 vm.runInContext(board.slice(board.indexOf('const chains = {}'),board.indexOf('function setStatus('))+
   board.slice(board.indexOf('function deleteTask('),board.indexOf('function linkRelated(')),context);
 vm.runInContext('deleteTask("parent")',context);
 await vm.runInContext('Promise.all(Object.values(chains))',context);
 const child=records.get('child');
 assert.equal(child.data.pai,null);assert.deepEqual(Array.from(child.data.relacionadas),[]);
 assert.equal(child.version,3);assert.equal(child.data.historico.length,2);
});

test('local task IDs stay distinct across deletion and page reload',()=>{
 const board=fs.readFileSync(path.join(__dirname,'../skills/tarefas/app/board-src.html'),'utf8');
 const fn=board.slice(board.indexOf('function newId('),board.indexOf('async function addTask('));
 const make=()=>{const ctx=vm.createContext({db:{local:true},idSlug:()=> 'same-title',crypto:require('node:crypto').webcrypto});
   vm.runInContext(fn,ctx);return vm.runInContext('newId("Same title")',ctx);};
 const a=make(),b=make();assert.notEqual(a,b);assert.ok(a.length<=60);
});


test('cold writes refuse to substitute a newer server version for an unseen one',async()=>{
 const c=client(r=>r.collection==='config'?schema:{id:'a',exists:true,version:9,data:{titulo:'Remote'}});
 const db=await c.window.cortexLocal.ready();
 await assert.rejects(db.doc('tasks/a').update({titulo:'Unseen'}),e=>e.code==='conflict');
 assert.equal(c.requests.filter(r=>r.collection==='tasks').length,0);
});

test('deleted recurrence occurrence is not recreated and its cursor still advances',async()=>{
 const board=fs.readFileSync(path.join(__dirname,'../skills/tarefas/app/board-src.html'),'utf8');
 const fn=board.slice(board.indexOf('async function materializar('),board.indexOf('function saveRec('));
 let advanced=false;
 const ctx=vm.createContext({db:{local:true,doc:()=>({update:async body=>{advanced=body.ultima==='2026-11-03';}})},
  canWrite:true,loaded:true,recLoaded:true,prefsLoaded:true,recs:[{id:'routine'}],
  todayStr:()=> '2026-11-03',addDays:(s,n)=>n===1?'2026-11-04':s,
  recNext:(r,start)=>start<='2026-11-03'?'2026-11-03':null,recInicio:()=> '2026-11-03',
  recOpen:()=>null,nowIso:()=>new Date().toISOString(),queue:async(k,fn)=>fn(),
  recTaskId:()=> 'routine--2026-11-03',col:()=>({doc:()=>({
    get:async()=>({exists:false,version:2}),set:async()=>{throw new Error('Tombstone must not be reused');}
  })})});
 vm.runInContext(fn,ctx);await vm.runInContext('materializar()',ctx);
 assert.equal(advanced,true);
});
