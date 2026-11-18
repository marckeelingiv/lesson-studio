import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
import {audienceState, branchGraph, columnMetadata, companionURL, errorMessage,
  layer, purchaseBranch, safeLink, validAction} from './dashboard-core.mjs';

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
    services:{dagster:{url:'http://127.0.0.1:3000', runtime_database:'/private/runtime', owned:true, state:'running'},
      lightdash:{dashboard_url:'http://127.0.0.1:8080/?secret=abc'}},
  }));
  for (const word of ['private-token','private-origin','private-notes','private-header','private/runtime','owned']) assert.equal(serialized.includes(word), false);
  assert.equal(JSON.parse(serialized).services.lightdash.dashboard_url, null);
});

// A tiny DOM stub fails immediately if a renderer attempts innerHTML. This is
// a structural/security check, not a substitute for browser visual review.
class Node {
  constructor(tag) { this.tagName = tag; this.children = []; this.dataset = {}; this.attributes = {}; this._text = ''; this.classList = {add:() => {}}; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
  set innerHTML(_) { throw Error('Payload HTML must never be interpreted'); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ''; this.children = children; }
  setAttribute(key, value) { this.attributes[key] = value; }
  contains() { return false; }
  querySelectorAll() { return []; }
}
const walk = root => [root, ...root.children.flatMap(walk)];

test('native renderer escapes table/SQL/metadata, wires select downstream, keyboard reveals metadata', async () => {
  const previous = globalThis.document;
  globalThis.document = {createElement:tag => new Node(tag), createElementNS:(_, tag) => new Node(tag)};
  try {
    const {renderDashboard} = await import('./dashboard-view.mjs');
    const root = new Node('main'), actions = [], evil = '<img src=x onerror=alert(1)>';
    const state = {page:'Explore', selected:'purchase', branch:'purchase', sqlTab:'source', pinnedColumn:null,
      graph, observations:{purchase:{row_count:1, columns:[{name:'amount',type:'DECIMAL'}], rows:[[evil]],
        row_limit:50, order:'unspecified', observed_at:'time', snapshot_label:'saved'}},
      model:{id:'purchase', description:evil, owner:'not documented', classification:'not documented',
        columns:[{name:'amount', description:evil}], tests:[],
        source_sql:{text:evil, status:'current_worktree_source'}, manifest_sql:{compiled:'SELECT 1'},
      }, services:{}, status:'done'};
    renderDashboard(root, state, action => actions.push(action));
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
    assert.deepEqual(actions.slice(-2), [{type:'select', value:'base'}, {type:'page', value:'Definition'}]);
    assert.ok(root.textContent.includes('Snapshot build provenance: unknown'));
  } finally { globalThis.document = previous; }
});

test('offline controller clears previous evidence; one coordinator serializes and queues observations', async () => {
  const originals = {document:globalThis.document, window:globalThis.window, fetch:globalThis.fetch};
  const elements = new Map();
  globalThis.document = {
    createElement:tag => new Node(tag),
    querySelector:selector => {
      if (!elements.has(selector)) elements.set(selector, new Node('div'));
      return elements.get(selector);
    },
  };
  globalThis.window = {addEventListener:() => {}};
  globalThis.fetch = async () => { throw Error('offline'); };
  // Import the actual controller with only its DOM renderer replaced. No
  // browser, subject service, snapshot, token, or network target is opened.
  let source = await readFile(new URL('./dashboard.mjs', import.meta.url), 'utf8');
  source = source.replace("'./dashboard-core.mjs'", JSON.stringify(new URL('./dashboard-core.mjs', import.meta.url).href))
    .replace("'./dashboard-view.mjs'", JSON.stringify('data:text/javascript,export function renderDashboard(){}'));
  try {
    const controller = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(controller.state.busy, false);
    assert.deepEqual(controller.state.graph.nodes, []);
    assert.match(controller.state.status, /Companion unavailable/);
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
  let receive, renders = 0, posts = 0;
  const owner = {postMessage:() => { posts++; }}, foreign = {};
  runInNewContext(source.replace(/^import .*;\n/, ''), {
    window:{opener:owner, addEventListener:(_, listener) => { receive = listener; }},
    location:{origin:'http://127.0.0.1:4173'},
    document:{querySelector:() => ({})},
    renderDashboard:(_, state, send) => { renders++; send({type:'page', value:'Answer'}); },
  });
  const message = {type:'evidence-view-v1', state:{}};
  receive({origin:'https://evil.example', source:owner, data:message});
  receive({origin:'http://127.0.0.1:4173', source:foreign, data:message});
  assert.equal(renders, 0);
  receive({origin:'http://127.0.0.1:4173', source:owner, data:message});
  assert.equal(renders, 1);
  assert.equal(posts, 2); // Ready, then the validated-origin view's selection.
});
