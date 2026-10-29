/* Cortex local transport. No Claude globals; all persistent writes go through SQLite. */
(() => {
  "use strict";
  if (!window.CORTEX_LOCAL) return;
  const cfg = window.CORTEX_LOCAL;
  const key = "cortex-token:" + cfg.board;
  let token = new URLSearchParams(location.hash.slice(1)).get("token");
  try {
    if (token) sessionStorage.setItem(key, token);
    else token = sessionStorage.getItem(key);
  } catch (_) { /* In-memory token still works when storage is unavailable. */ }
  if (location.hash) history.replaceState(null, "", location.pathname + location.search);
  const cache = new Map(), subscriptions = new Set();
  let epoch = 0;
  const copy = value => value == null ? value : JSON.parse(JSON.stringify(value));
  const fault = (code, message) => Object.assign(new Error(message), { code });
  async function call(request) {
    if (!token) throw fault("unauthorized", "Open the URL printed by Cortex / Abra a URL do Cortex.");
    const response = await fetch(cfg.api, {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
      body: JSON.stringify(request), cache: "no-store", credentials: "omit",
    });
    const result = await response.json();
    if (!response.ok || result.error) {
      const error = result.error || {};
      throw fault(error.code || "unavailable", error.message || "Cortex unavailable");
    }
    return result;
  }
  const snapshot = item => ({ id: item.id, exists: item.exists !== false, version: item.version,
    data: () => copy(item.data) });
  function remember(collection, item) {
    const path = collection + "/" + item.id;
    const previous = cache.get(path);
    if (!previous || item.version >= previous.version) cache.set(path, copy(item));
  }
  async function readCollection(collection) {
    const docs = []; let cursor;
    do {
      const page = await call({ op: "list", collection, limit: 200, ...(cursor ? { cursor } : {}) });
      docs.push(...page.docs); cursor = page.next_cursor;
    } while (cursor);
    return { docs };
  }
  async function poll(sub) {
    if (!sub.active || sub.busy) { if (sub.busy) sub.again = true; return; }
    sub.busy = true;
    const started = epoch;
    try {
      const result = sub.id == null ? await readCollection(sub.collection) :
        await call({ op: "get", collection: sub.collection, id: sub.id });
      if (!sub.active) return;
      if (started !== epoch) { sub.again = true; return; }
      const digest = JSON.stringify(result);
      if (digest !== sub.last || sub.force) {
        sub.last = digest; sub.force = false;
        if (sub.id == null) {
          result.docs.forEach(item => remember(sub.collection, item));
          sub.next({ docs: result.docs.map(snapshot) });
        } else { remember(sub.collection, result); sub.next(snapshot(result)); }
      }
    } catch (err) { if (sub.active && sub.error) sub.error(err); }
    finally {
      sub.busy = false;
      if (sub.active) {
        clearTimeout(sub.timer);
        sub.timer = setTimeout(() => poll(sub), sub.again ? 0 : 2000);
        sub.again = false;
      }
    }
  }
  function subscribe(collection, id, next, error) {
    const sub = { collection, id, next, error, active: true, busy: false };
    subscriptions.add(sub); poll(sub);
    return () => { sub.active = false; clearTimeout(sub.timer); subscriptions.delete(sub); };
  }
  function refresh() {
    subscriptions.forEach(sub => { sub.force = true; clearTimeout(sub.timer); poll(sub); });
  }
  function doc(path) {
    const slash = path.indexOf("/"), collection = path.slice(0, slash), id = path.slice(slash + 1);
    if (slash < 1 || !id) throw fault("invalid_argument", "Invalid document path");
    // A reference carries the version the user actually saw, not a silently refreshed version.
    let known = copy(cache.get(path));
    const ref = {
      async get() {
        const item = await call({ op: "get", collection, id });
        known = copy(item); remember(collection, item); return snapshot(item);
      },
      onSnapshot(next, error) { return subscribe(collection, id, next, error); },
      set(data) { return write("set", data); },
      update(data) { return write("update", data); },
      delete() { return write("delete"); },
    };
    async function write(op, data) {
      if (op !== "set" && !known) await ref.get();
      const request = { op, collection, id, mutation_id: crypto.randomUUID() };
      if (data !== undefined) request.data = data;
      // set is deliberately create-only: it cannot overwrite an existing card.
      if (op !== "set") request.if_version = known.version;
      epoch++;
      try {
        const result = await call(request);
        known = copy(result); remember(collection, result); return snapshot(result);
      } finally { epoch++; refresh(); }
    }
    return ref;
  }
  window.cortexLocal = {
    async ready() {
      await call({ op: "get", collection: "config", id: "schema" });
      return { local: true, doc, refresh,
        collection(name) { return { doc: id => doc(name + "/" + id),
          async get() { const page = await readCollection(name); page.docs.forEach(x => remember(name, x)); return { docs: page.docs.map(snapshot) }; },
          onSnapshot(next, error) { return subscribe(name, null, next, error); } }; },
      };
    },
  };
  window.addEventListener("pagehide", () => subscriptions.forEach(sub => {
    sub.active = false; clearTimeout(sub.timer);
  }));
})();
