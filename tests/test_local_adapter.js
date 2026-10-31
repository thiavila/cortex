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
