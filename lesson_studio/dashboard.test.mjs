import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
import {audienceState, branchGraph, columnMetadata, companionURL, errorMessage,
  layer, purchaseBranch, safeLink, validAction, publicLesson, applyAction} from './dashboard-core.mjs';
import {cameraChannel} from './dashboard-sync.mjs';

const graph = {
  nodes:[
    {id:'source.raw.pos', name:'pos', kind:'source', queryable:false},
    {id:'base', name:'base_pos_transactions', kind:'model', queryable:true},
    {id:'stg', name:'stg_pos_transactions', kind:'model', queryable:true},
    {id:'purchase', name:'mtt_dynamic_pricing', kind:'model', queryable:true},
    {id:'other', name:'mtt_ai_slas', kind:'model', queryable:true},
  ],
  edges:[{source:'source.raw.pos', target:'base'}, {source:'base', target:'stg'}, {source:'stg', target:'purchase'}],
};

test('manifest IDs, layer placement, branch ancestry, and action validation', () => {
  assert.deepEqual(graph.nodes.map(layer), [0,1,2,3,3]);
  assert.equal(purchaseBranch(graph), 'purchase');
  assert.deepEqual(branchGraph(graph, 'purchase').nodes.map(node => node.id), ['source.raw.pos','base','stg','purchase']);
  assert.equal(branchGraph(graph, 'purchase').edges.length, 3);
  assert.equal(branchGraph(graph, 'all'), graph);
  const state = {graph, model:null, observations:{}, selected:'purchase'};
  assert.equal(validAction({type:'select', value:'other'}, state), true);
  assert.equal(validAction({type:'select', value:'model.invented'}, state), false);
  for (const type of ['start','token','base','url','__proto__']) assert.equal(validAction({type, value:'purchase'}, state), false);
  assert.equal(validAction({type:'sqlTab', value:'compiled'}, state), true);
});

test('metadata joins by actual column name, never infers ownership or test results', () => {
  const model = {columns:[{name:'amount', description:'Synthetic amount', owner:'data team', meta:{unit:'USD'}}],
    tests:[{name:'not_null', column_name:'amount'}, {name:'unique', column_name:'id'}]};
  const result = columnMetadata(model, {name:'amount', type:'DECIMAL(10,2)'});
  assert.equal(result.owner, 'data team');
  assert.equal(result.classification, 'not documented');
  assert.equal(result.data_type, 'not documented');
  assert.equal(result.tests.length, 1);
  assert.equal(result.tests[0].name, 'not_null');
  assert.equal('passed' in result, false);
  assert.equal(columnMetadata(model, {name:'unknown', type:'VARCHAR'}).description, 'not documented');
});

test('runtime URL and outbound links reject credentials, remote hosts and secret parameters', () => {
  assert.equal(companionURL('http://127.0.0.1:4174'), 'http://127.0.0.1:4174');
  for (const value of ['http://127.0.0.1.evil:4174', 'https://example.com', 'javascript:alert(1)',
    'http://user:secret@127.0.0.1', 'http://127.0.0.1:4174/path', 'http://127.0.0.1:4174?token=secret',
    'http://127.0.0.1:4174/#secret']) assert.throws(() => companionURL(value));
  assert.equal(safeLink('http://127.0.0.1:8080/projects/p/dashboards/d'), 'http://127.0.0.1:8080/projects/p/dashboards/d');
  assert.equal(safeLink('http://127.0.0.1:8080/?token=secret'), null);
  assert.equal(safeLink('https://evil.example'), null);
});

test('audience serialization is allowlisted: no runtime secrets, start controls, or notes', () => {
  const serialized = JSON.stringify(audienceState({
    page:'Question', graph, token:'private-token', base:'private-origin', notes:'private-notes',
    requests:{headers:{'X-Evidence-Token':'private-header'}},
    provenance:{label:'saved local snapshot', mode:'saved_snapshot_read_only',
      snapshot_path:'/private/snapshot.duckdb', snapshot_exists:true,
      snapshot_modified_at:'2026-11-17T10:00:00Z', snapshot_build_provenance:'unknown',
      snapshot_built_from_manifest:'unknown', manifest_path:'/private/manifest.json',
      manifest_sha256:'abc123', manifest_generated_at:'2026-11-16T10:00:00Z',
      manifest_loaded_at:'2026-11-17T11:00:00Z', warning:'private-unrendered-warning',
      future_config:'private-future-config'},
    services:{dagster:{url:'http://127.0.0.1:3000', runtime_database:'/private/runtime', owned:true, state:'running'},
      lightdash:{dashboard_url:'http://127.0.0.1:8080/?secret=abc'}},
  }));
  for (const word of ['private-token','private-origin','private-notes','private-header','private/runtime',
    'private/snapshot','private/manifest','private-unrendered-warning','private-future-config','owned']) assert.equal(serialized.includes(word), false);
  assert.deepEqual(JSON.parse(serialized).provenance, {
    label:'saved local snapshot', mode:'saved_snapshot_read_only', snapshot_exists:true,
    snapshot_modified_at:'2026-11-17T10:00:00Z', snapshot_build_provenance:'unknown',
    snapshot_built_from_manifest:'unknown', manifest_sha256:'abc123',
    manifest_generated_at:'2026-11-16T10:00:00Z', manifest_loaded_at:'2026-11-17T11:00:00Z',
  });
  assert.equal(JSON.parse(serialized).services.lightdash.dashboard_url, null);
});

test('portable lesson public fields, bounded camera projection, and compound focus actions', () => {
  const lesson = {title:'Public', disclosure:'Synthetic', notes:'PRIVATE', scenes:[
    {kicker:'01', title:'<plain>', body:'Question', points:['One', {notes:'PRIVATE'}],
      notes:'PRIVATE', evidence:'PRIVATE', seconds:99, url:'PRIVATE', type:'website'},
    null,
  ]};
  assert.deepEqual(publicLesson(lesson), {title:'Public', disclosure:'Synthetic', scenes:[
    {kicker:'01', title:'<plain>', body:'Question', points:['One']},
    {kicker:'', title:'', body:'', points:[]},
  ]});
  const state = {graph, model:null, observations:{}, selected:'purchase', lesson};
  assert.equal(applyAction(state, {type:'inspect', value:{model:'base', card:'table'}}), true);
  assert.equal(state.selected, 'base');
  assert.equal(state.activeCard, 'table');
  assert.equal(state.pinnedColumn, null);
  const tableCamera = state.camera;
  assert.equal(applyAction(state, {type:'inspect', value:{model:'stg', card:'sql'}}), true);
  assert.equal(state.selected, 'stg');
  assert.equal(state.activeCard, 'sql');
  assert.notDeepEqual(state.camera, tableCamera);
  for (const action of [
    {type:'inspect', value:{model:'invented', card:'sql'}},
    {type:'inspect', value:{model:'base', card:'operator'}},
    {type:'route', value:'__proto__'}, {type:'focus', value:'operator'},
    ...[NaN, Infinity, 100001, '1'].map(cx => ({type:'camera', value:{cx, cy:0, zoom:1}})),
    {type:'camera', value:{cx:0, cy:0, zoom:0}},
  ]) assert.equal(applyAction(state, action), false);
  assert.equal(applyAction(state, {type:'route', value:'trust'}), true);
  assert.equal(state.activeCard, 'trust');
  applyAction(state, {type:'camera', value:{cx:3, cy:4, zoom:0.5, token:'PRIVATE'}});
  const projected = audienceState(state);
  assert.deepEqual(projected.camera, {cx:3, cy:4, zoom:0.5});
  assert.equal(JSON.stringify(projected).includes('PRIVATE'), false);
  assert.equal(audienceState({...state, camera:{cx:Infinity, cy:0, zoom:1}, activeCard:'operator'}).camera, undefined);
  assert.equal(audienceState({...state, activeCard:'operator'}).activeCard, undefined);
});

test('camera-only channel coalesces frames, delivers final position, rejects foreign messages and never echoes by itself', () => {
  const origin = 'http://127.0.0.1:4173', frames = [], deskPosts = [], audiencePosts = [];
  const desk = {postMessage:(data, target) => deskPosts.push({data, target})};
  const audience = {postMessage:(data, target) => audiencePosts.push({data, target})};
  let deskCamera, audienceCamera;
  const privateChannel = cameraChannel({peer:() => audience, origin, frame:callback => frames.push(callback),
    apply:camera => { deskCamera = camera; privateChannel.publish(camera); }});
  const cleanChannel = cameraChannel({peer:() => desk, origin, frame:callback => frames.push(callback),
    apply:camera => { audienceCamera = camera; }});
  for (let cx = 0; cx < 100; cx++) cleanChannel.publish({cx, cy:5, zoom:1, notes:'PRIVATE', observations:{huge:[]}});
  assert.equal(frames.length, 1);
  frames.shift()(); // Final position still arrives after input has stopped.
  assert.equal(deskPosts.length, 1);
  assert.deepEqual(deskPosts[0], {data:{type:'evidence-camera-v1', camera:{cx:99, cy:5, zoom:1}}, target:origin});
  const event = {source:audience, origin, data:deskPosts[0].data};
  assert.equal(privateChannel.receive({...event, origin:'https://evil.example'}), false);
  assert.equal(privateChannel.receive({...event, source:{}}), false);
  assert.equal(privateChannel.receive({...event, data:{...event.data, camera:{cx:Infinity, cy:0, zoom:1}}}), false);
  assert.equal(privateChannel.receive(event), true);
  assert.deepEqual(deskCamera, {cx:99, cy:5, zoom:1});
  frames.shift()();
  assert.equal(cleanChannel.receive({origin, source:desk, data:audiencePosts[0].data}), true);
  assert.deepEqual(audienceCamera, deskCamera);
  assert.equal(frames.length, 0); // Receiving a camera never publishes one.
  privateChannel.publish({cx:-50, cy:20, zoom:2});
  frames.shift()();
  cleanChannel.receive({origin, source:desk, data:audiencePosts[1].data});
  assert.deepEqual(audienceCamera, {cx:-50, cy:20, zoom:2});
  cleanChannel.publish({cx:900, cy:0, zoom:1});
  cleanChannel.clear(); // A subsequent authoritative Focus/full state wins.
  frames.shift()();
  assert.equal(deskPosts.length, 1);
});

// A tiny DOM stub fails immediately if a renderer attempts innerHTML. This is
// a structural/security check, not a substitute for browser visual review.
class Node {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.dataset = {}; this.style = {}; this.attributes = {};
    Object.defineProperty(this.attributes, Symbol.iterator, {value:function* () {
      for (const [name, value] of Object.entries(this)) yield {name, value};
    }});
    this._text = ''; this.classList = {add:() => {}, remove:() => {}}; this.listeners = {};
  }
  set textContent(value) { this._text = String(value); this.children = []; this.scrollTop = 0; this.scrollLeft = 0; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set innerHTML(_) { throw Error('Payload HTML must never be interpreted'); }
  append(...children) { for (const child of children) this.insertBefore(child, null); }
  insertBefore(child, before) {
    if (child.parentNode) child.parentNode.removeChild(child);
    const index = before ? this.children.indexOf(before) : this.children.length;
    this.children.splice(index, 0, child); child.parentNode = this;
  }
  removeChild(child) {
    assert.ok(this.children.includes(child)); this.children.splice(this.children.indexOf(child), 1); child.parentNode = null;
  }
  replaceChildren(...children) { this._text = ''; for (const child of [...this.children]) this.removeChild(child); this.append(...children); }
  setAttribute(key, value) {
    this.attributes[key] = value;
    if (key.startsWith('data-')) this.dataset[key.slice(5)] = value;
  }
  hasAttribute(key) { return key in this.attributes; }
  removeAttribute(key) { delete this.attributes[key]; }
  contains(child) { return walk(this).includes(child); }
  focus() { document.activeElement = this; }
  querySelectorAll() { return []; }
  addEventListener(type, handler) { this.listeners[type] = handler; }
  removeEventListener(type) { delete this.listeners[type]; }
  getBoundingClientRect() { return {left:0, top:0, width:1600, height:900}; }
}
const walk = root => [root, ...root.children.flatMap(walk)];

test('native renderer escapes table/SQL/metadata, wires select downstream, keyboard reveals metadata', async () => {
  const previous = globalThis.document;
  const previousObserver = globalThis.ResizeObserver;
  globalThis.ResizeObserver = class {observe() {} disconnect() {}};
  globalThis.document = {createElement:tag => new Node(tag), createElementNS:(_, tag) => new Node(tag)};
  try {
    const {mountDashboard} = await import('./dashboard-view.mjs');
    const root = new Node('main'), actions = [], evil = '<img src=x onerror=alert(1)>';
    const state = {page:'Explore', selected:'purchase', branch:'purchase', sqlTab:'source', pinnedColumn:null,
      graph, observations:{purchase:{row_count:1, columns:[{name:'amount',type:'DECIMAL'}], rows:[[evil]],
        row_limit:50, order:'unspecified', observed_at:'time', snapshot_label:'saved'}},
      model:{id:'purchase', description:evil, owner:'not documented', classification:'not documented',
        columns:[{name:'amount', description:evil}], tests:[],
        source_sql:{text:evil, status:'current_worktree_source'}, manifest_sql:{compiled:'SELECT 1'},
      }, services:{}, status:'done'};
    const update = mountDashboard(root, action => actions.push(action));
    update(state);
    const shells = walk(root).filter(node => node.dataset.card);
    const table = walk(root).find(node => node.tagName === 'table');
    update.camera.set({cx:50, cy:70, zoom:0.5});
    update({...state, busy:true});
    assert.deepEqual(walk(root).filter(node => node.dataset.card), shells);
    assert.equal(walk(root).find(node => node.tagName === 'table'), table);
    assert.deepEqual(update.camera.get(), {cx:50, cy:70, zoom:0.5});
    assert.ok(root.textContent.includes(evil));
    assert.equal(walk(root).some(node => node.tagName === 'img'), false);
    const header = walk(root).find(node => node.dataset.focus === 'column:amount');
    header.onfocus();
    assert.ok(walk(root).find(node => node.id === 'column-governance').textContent.includes(evil));
    header.onclick();
    assert.deepEqual(actions.pop(), {type:'column', value:'amount'});
    const wire = walk(root).find(node => node.attributes.class === 'edge');
    let prevented = false;
    wire.onkeydown({key:'Enter', preventDefault:() => { prevented = true; }});
    assert.equal(prevented, true);
    assert.deepEqual(actions.pop(), {type:'inspect', value:{model:'base', card:'sql'}});
    assert.ok(root.textContent.includes('Snapshot build provenance: unknown'));
    const world = walk(root).find(node => node.className === 'board-world');
    const wrapper = walk(root).find(node => node.className === 'table-scroll');
    const sqlSlot = walk(root).find(node => node.dataset.card === 'sql').children[1];
    const governanceSlot = walk(root).find(node => node.dataset.card === 'governance').children[1];
    const sqlPre = walk(sqlSlot).find(node => node.tagName === 'pre');
    const sqlTab = walk(sqlSlot).find(node => node.dataset.focus === 'sql:source');
    header.focus(); wrapper.scrollTop = 120; wrapper.scrollLeft = 55;
    sqlSlot.scrollTop = 70; sqlPre.scrollTop = 30; governanceSlot.scrollTop = 42;
    const changed = {...state, pinnedColumn:'amount', observations:{purchase:{
      ...state.observations.purchase, row_count:2, observed_at:'later', rows:[['fresh'], ['rows']],
    }}, model:{...state.model, description:'Changed description', source_sql:{...state.model.source_sql, text:'SELECT fresh'}}};
    update(changed);
    assert.equal(walk(root).find(node => node.className === 'board-world'), world);
    assert.equal(walk(root).find(node => node.tagName === 'table'), table);
    assert.equal(walk(root).find(node => node.className === 'table-scroll'), wrapper);
    assert.equal(walk(root).find(node => node.dataset.focus === 'column:amount'), header);
    assert.equal(document.activeElement, header);
    assert.equal(wrapper.scrollTop, 120); assert.equal(wrapper.scrollLeft, 55);
    assert.equal(sqlSlot.scrollTop, 70); assert.equal(sqlPre.scrollTop, 30);
    assert.equal(governanceSlot.scrollTop, 42);
    assert.equal(walk(sqlSlot).find(node => node.dataset.focus === 'sql:source'), sqlTab);
    assert.match(table.textContent, /freshrows/);
    header.onclick(); assert.deepEqual(actions.pop(), {type:'column', value:null});
    update({...changed, pinnedColumn:null});
    assert.match(governanceSlot.textContent, /Observed type/); // Still focused/hovered after refresh.
    assert.equal(document.activeElement, header);
    const branch = walk(root).find(node => node.dataset.focus === 'branch');
    branch.value = 'all'; branch.onchange({target:branch});
    assert.deepEqual(actions.pop(), {type:'branch', value:'all'});
    let cameraDispatches = 0;
    const audienceRoot = new Node('main');
    const audienceUpdate = mountDashboard(audienceRoot, () => cameraDispatches++);
    audienceUpdate({...changed, camera:{cx:300, cy:200, zoom:0.5}, activeCard:'table',
      lesson:{scenes:[{title:evil, notes:'PRIVATE', evidence:'PRIVATE'}]}});
    audienceUpdate.setCamera({cx:400, cy:200, zoom:0.5});
    assert.equal(cameraDispatches, 0);
    assert.deepEqual(audienceUpdate.camera.get(), {cx:400, cy:200, zoom:0.5});
    assert.equal(audienceRoot.textContent.includes('PRIVATE'), false);
    assert.equal(audienceRoot.textContent.includes(evil), true);
    update.destroy(); audienceUpdate.destroy();
  } finally { globalThis.document = previous; globalThis.ResizeObserver = previousObserver; }
});

test('offline controller clears previous evidence; one coordinator serializes and queues observations', async () => {
  const originals = {document:globalThis.document, window:globalThis.window, fetch:globalThis.fetch, location:globalThis.location,
    requestAnimationFrame:globalThis.requestAnimationFrame};
  globalThis.location = {origin:'http://127.0.0.1:4173'};
  const frames = [], posts = []; let receive, fetches = 0;
  globalThis.requestAnimationFrame = callback => frames.push(callback);
  const elements = new Map();
  globalThis.document = {
    createElement:tag => new Node(tag),
    querySelector:selector => {
      if (!elements.has(selector)) elements.set(selector, new Node('div'));
      return elements.get(selector);
    },
  };
  const audience = {postMessage:(data, target) => posts.push({data, target})};
  globalThis.window = {addEventListener:(_, listener) => { receive = listener; }, open:() => audience};
  globalThis.fetch = async () => { fetches++; throw Error('offline'); };
  // Import the actual controller with only its DOM renderer replaced. No
  // browser, subject service, snapshot, token, or network target is opened.
  let source = await readFile(new URL('./dashboard.mjs', import.meta.url), 'utf8');
  source = source.replace("'./dashboard-view.mjs'", JSON.stringify('data:text/javascript,export function mountDashboard(root,dispatch){root.send=dispatch;const update=()=>{};update.setCamera=()=>{};return update}'))
    .replace(/from '(\.\/[^']+)'/g, (_, path) => `from ${JSON.stringify(new URL(path, import.meta.url).href)}`);
  try {
    const controller = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(controller.state.busy, false);
    assert.deepEqual(controller.state.graph.nodes, []);
    assert.match(controller.state.status, /Companion unavailable/);
    elements.get('#audience-open').onclick();
    const beforeCamera = fetches;
    const camera = {cx:150, cy:350, zoom:0.7};
    receive({origin:location.origin, source:{}, data:{type:'evidence-camera-v1', camera}});
    assert.notDeepEqual(controller.state.camera, camera);
    receive({origin:location.origin, source:audience, data:{type:'evidence-camera-v1', camera}});
    assert.deepEqual(controller.state.camera, camera);
    assert.equal(fetches, beforeCamera);
    assert.equal(posts.length, 0); // No full evidence projection for a gesture.
    assert.equal(frames.length, 0);
    assert.equal(posts.length, 0); // Accepted audience input is not echoed.
    const localCamera = {cx:500, cy:600, zoom:1.2};
    elements.get('#dashboard').send({type:'camera', value:localCamera});
    assert.deepEqual(controller.state.camera, localCamera);
    assert.equal(fetches, beforeCamera);
    assert.equal(frames.length, 1);
    frames.shift()();
    assert.deepEqual(posts[0].data, {type:'evidence-camera-v1', camera:localCamera});
    elements.get('#dashboard').send({type:'camera', value:camera});
    elements.get('#dashboard').send({type:'focus', value:'sql'});
    assert.equal(posts[1].data.type, 'evidence-view-v1');
    frames.shift()();
    assert.equal(posts.length, 2); // No stale gesture after a discrete Focus.
    assert.equal(fetches, beforeCamera);
    receive({origin:location.origin, source:audience, data:{type:'evidence-ready-v1'}});
    assert.equal(posts[2].data.type, 'evidence-view-v1');
    assert.deepEqual(posts[2].data.state.camera, controller.state.camera); // Audience reload.
    controller.state.observations = {old:{row_count:999}};
    await controller.refresh();
    assert.deepEqual(controller.state.observations, {});
    const paths = []; let active = 0, peak = 0, release;
    let held = false;
    globalThis.fetch = async url => {
      const path = new URL(url).pathname;
      paths.push(path);
      assert.equal(path.includes('/api/session'), false);
      const envelope = {api_version:1, observed_at:'observed'};
      if (path === '/api/provenance') return Response.json({...envelope, provenance:{label:'actual'}});
      if (path === '/api/services') return Response.json({...envelope, services:{}});
      if (path === '/api/lineage') return Response.json({...envelope, ...graph});
      if (path.endsWith('/observation')) {
        active++; peak = Math.max(peak, active);
        if (!held) { held = true; await new Promise(resolve => { release = resolve; }); }
        active--;
        return Response.json({...envelope, observation:{row_count:7}});
      }
      return Response.json({...envelope, model:{id:'purchase'}});
    };
    const pass = controller.refresh();
    while (!release) await new Promise(resolve => setImmediate(resolve));
    await controller.refresh(); // Queued; must not create a second observation loop.
    assert.equal(peak, 1);
    release(); await pass;
    while (controller.state.busy) await new Promise(resolve => setImmediate(resolve));
    assert.equal(peak, 1);
    assert.equal(paths.filter(path => path === '/api/provenance').length, 2);
    assert.equal(controller.state.observations.purchase.row_count, 7);
    assert.equal(JSON.stringify(audienceState(controller.state)).includes('X-Evidence-Token'), false);
    // Service start is only possible through the private, confirmed handler.
    globalThis.window.confirm = () => false;
    // Re-render controls using service payloads without starting a real process.
    globalThis.fetch = async (url, options) => {
      const path = new URL(url).pathname, envelope = {api_version:1, observed_at:'observed'};
      paths.push(path);
      if (path === '/api/services') return Response.json({...envelope, services:{docs:{state:'not_started', missing_prerequisites:[]}}});
      if (path === '/api/session') return Response.json({...envelope, token:'PRIVATE_START_TOKEN'});
      if (path === '/api/services/docs/start') {
        assert.equal(options.method, 'POST');
        assert.equal(options.body, '{}');
        assert.equal(options.headers['Content-Type'], 'application/json');
        assert.equal(options.headers['X-Evidence-Token'], 'PRIVATE_START_TOKEN');
        assert.equal(JSON.stringify(audienceState(controller.state)).includes('PRIVATE_START_TOKEN'), false);
        return Response.json({...envelope, service:{state:'running'}});
      }
      if (path === '/api/provenance') return Response.json({...envelope, provenance:{label:'actual'}});
      if (path === '/api/lineage') return Response.json({...envelope, ...graph});
      if (path.endsWith('/observation')) return Response.json({...envelope, observation:{row_count:7}});
      return Response.json({...envelope, model:{id:'purchase'}});
    };
    await controller.refresh();
    const docsButton = elements.get('#service-controls').children[1].children[1];
    const before = paths.length;
    await docsButton.onclick();
    assert.equal(paths.length, before); // Cancel confirmation: no session/token request.
    globalThis.window.confirm = () => true;
    await docsButton.onclick();
    while (controller.state.busy) await new Promise(resolve => setImmediate(resolve));
    assert.ok(paths.includes('/api/services/docs/start'));
    assert.equal(JSON.stringify(audienceState(controller.state)).includes('PRIVATE_START_TOKEN'), false);
  } finally { Object.assign(globalThis, originals); }
});

test('clean audience module contains no session fetch/start or storage; strict source and origin bridge', async () => {
  const source = await readFile(new URL('./dashboard-audience.mjs', import.meta.url), 'utf8');
  assert.match(source, /event\.origin !== location\.origin/);
  assert.match(source, /event\.source !== owner/);
  assert.doesNotMatch(source, /\/api\/session|\/start|localStorage|fetch\(/);
  const html = await readFile(new URL('./dashboard-audience.html', import.meta.url), 'utf8');
  assert.doesNotMatch(html, /operator|Start docs|Start dagster|dashboard\.mjs/);
  assert.match(errorMessage('query_busy'), /busy/);
  assert.match(errorMessage('snapshot_query_unavailable'), /lock/);
  let receive, renders = 0, posts = 0, cameras = 0;
  const owner = {postMessage:() => { posts++; }}, foreign = {};
  runInNewContext(source.replace(/^import .*;\n/gm, ''), {
    cameraChannel,
    window:{opener:owner, addEventListener:(_, listener) => { receive = listener; }},
    location:{origin:'http://127.0.0.1:4173'},
    document:{querySelector:() => ({})},
    mountDashboard:(_, send) => {
      const update = () => { renders++; send({type:'page', value:'Answer'}); };
      update.setCamera = () => { cameras++; }; return update;
    },
  });
  const message = {type:'evidence-view-v1', state:{}};
  receive({origin:'https://evil.example', source:owner, data:message});
  receive({origin:'http://127.0.0.1:4173', source:foreign, data:message});
  assert.equal(renders, 0);
  receive({origin:'http://127.0.0.1:4173', source:owner, data:message});
  assert.equal(renders, 1);
  assert.equal(posts, 2); // Ready, then the validated-origin view's selection.
  receive({origin:'http://127.0.0.1:4173', source:owner,
    data:{type:'evidence-camera-v1', camera:{cx:10, cy:20, zoom:1}}});
  assert.equal(cameras, 1);
  assert.equal(renders, 1);
  assert.equal(posts, 2); // Camera reception has no echo or full render.
  runInNewContext(source.replace(/^import .*;\n/gm, ''), {
    cameraChannel,
    window:{opener:null, addEventListener:(_, listener) => { receive = listener; }},
    location:{origin:'http://127.0.0.1:4173'},
    document:{querySelector:() => ({})},
    mountDashboard:() => { throw Error('Direct audience must remain waiting'); },
  });
  receive({origin:'http://127.0.0.1:4173', source:null, data:message});
});
