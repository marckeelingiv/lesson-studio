import {steps, companionURL, branchGraph, purchaseBranch, audienceState, validAction, errorMessage} from './dashboard-core.mjs';
import {renderDashboard} from './dashboard-view.mjs';

const $ = selector => document.querySelector(selector);
export const state = {
  page: steps[0], selected: null, branch: 'all', sqlTab: 'source', pinnedColumn: null,
  graph: {nodes:[], edges:[]}, model: null, observations: {}, provenance: null,
  services: {}, status:'Companion not observed yet. No results substituted.', observedAt:null, busy:false,
};
let base = 'http://127.0.0.1:4174', audience = null, pending = false, timer;
const starts = {};

function paint() {
  renderDashboard($('#dashboard'), audienceState(state), action);
  if (audience && !audience.closed) audience.postMessage({type:'evidence-view-v1', state:audienceState(state)}, location.origin);
}
function action(message) {
  if (!validAction(message, state)) return;
  const {type, value} = message;
  if (type === 'page') state.page = value;
  if (type === 'sqlTab') state.sqlTab = value;
  if (type === 'column') state.pinnedColumn = value;
  if (type === 'select') { state.selected = value; state.pinnedColumn = null; }
  if (type === 'branch') {
    state.branch = value; state.selected = value === 'all' ? state.selected : value; state.pinnedColumn = null;
  }
  paint();
  if (['select', 'branch'].includes(type)) refresh();
}
window.addEventListener('message', event => {
  if (event.origin !== location.origin || event.source !== audience) return;
  if (event.data?.type === 'evidence-ready-v1') paint();
  if (event.data?.type === 'evidence-action-v1') action(event.data.action);
});
$('#audience-open').onclick = () => {
  audience = window.open('dashboard-audience.html', 'lesson-evidence-audience');
  if (!audience) $('#operator-status').textContent = 'Audience popup blocked. Allow this explicit popup and retry.';
};

async function request(path, options = {}, origin = base) {
  let response;
  try { response = await fetch(`${origin}${path}`, {...options, cache:'no-store', signal:AbortSignal.timeout(10000)}); }
  catch { throw Error('offline'); }
  let payload;
  try { payload = await response.json(); } catch { throw Error('invalid_response'); }
  if (origin !== base) throw Error('connection_changed');
  if (!response.ok) throw Error(payload.error?.code || `http_${response.status}`);
  if (payload.api_version !== 1) throw Error('unsupported_api_version');
  return payload;
}

// One coordinator owns ALL preview queries. A selection during work queues one
// subsequent pass; polling is scheduled only after completion, never setInterval.
export async function refresh() {
  clearTimeout(timer);
  if (state.busy) { pending = true; return; }
  state.busy = true; paint();
  const origin = base;
  try {
    state.provenance = (await request('/api/provenance', {}, origin)).provenance;
    state.services = (await request('/api/services', {}, origin)).services;
    for (const name of ['dagster', 'docs']) if (state.services[name]?.reachable) delete starts[name];
    const lineage = await request('/api/lineage', {}, origin);
    state.graph = {nodes:lineage.nodes, edges:lineage.edges};
    if (state.branch !== 'all' && !lineage.nodes.some(node => node.id === state.branch)) state.branch = 'all';
    if (!state.selected || !lineage.nodes.some(node => node.id === state.selected)) {
      state.branch = purchaseBranch(state.graph);
      state.selected = state.branch === 'all' ? lineage.nodes.find(node => node.queryable)?.id : state.branch;
    }
    const selected = state.selected;
    const node = lineage.nodes.find(node => node.id === selected);
    state.model = null;
    if (node?.queryable) {
      try { state.model = (await request(`/api/models/${encodeURIComponent(selected)}`, {}, origin)).model; }
      catch (error) { $('#operator-status').textContent = `Model detail: ${errorMessage(error.message)}`; }
    }
    const visible = branchGraph(state.graph, state.branch).nodes.filter(node => node.queryable);
    // Selected model first, but all visible counts still use the same sequential queue.
    visible.sort((a, b) => Number(b.id === selected) - Number(a.id === selected));
    for (const item of visible) {
      if (pending || origin !== base) break;
      try {
        const payload = await request(`/api/models/${encodeURIComponent(item.id)}/observation`, {}, origin);
        state.observations[item.id] = {...payload.observation, observed_at:payload.observed_at};
      } catch (error) { state.observations[item.id] = {error:error.message}; }
    }
    state.observedAt = lineage.observed_at;
    state.status = pending ? 'Selection changed; a new sequential observation pass is queued.' :
      `Observation pass completed. Manifest response ${lineage.observed_at}. Per-table observation times are shown with each preview; unavailable queries have no replacement counts.`;
  } catch (error) {
    state.status = errorMessage(error.message);
    // Clear previous evidence on connection failure, rather than silently
    // presenting old observations as fresh or borrowing another origin's data.
    state.provenance = null; state.services = {}; state.model = null;
    state.graph = {nodes:[], edges:[]}; state.observations = {};
  } finally {
    state.busy = false; paint(); renderControls();
    if (pending || origin !== base) { pending = false; refresh(); }
    else if ($('#poll').checked) timer = setTimeout(refresh, 15000);
  }
}
$('#connection-form').onsubmit = event => {
  event.preventDefault();
  try {
    const next = companionURL($('#companion').value);
    if (next !== base) {
      base = next;
      state.graph = {nodes:[], edges:[]}; state.model = null; state.provenance = null;
      state.observations = {}; state.services = {}; state.selected = null; state.branch = 'all';
      for (const name of Object.keys(starts)) delete starts[name];
    }
    $('#operator-status').textContent = 'Read-only observation requested. No services will be started.';
    refresh();
  } catch (error) { $('#operator-status').textContent = error.message; }
};
$('#refresh').onclick = refresh;
$('#poll').onchange = () => { clearTimeout(timer); if ($('#poll').checked) refresh(); };

function renderControls() {
  const root = $('#service-controls'); root.replaceChildren();
  for (const name of ['dagster', 'docs']) {
    const section = document.createElement('section'), label = document.createElement('p'), control = document.createElement('button');
    const service = state.services[name];
    label.textContent = `${name}: ${starts[name] || (service?.state === 'exited' ? 'failed / process exited' :
      service?.missing_prerequisites?.length ? `missing: ${service.missing_prerequisites.join(', ')}` :
      service?.reachable ? 'available TCP port (not authenticated)' :
      service?.state === 'running' ? 'starting' : 'not started')}`;
    control.textContent = `Start ${name}…`;
    control.disabled = !service || starts[name] === 'starting' || service.reachable || Boolean(service.missing_prerequisites?.length);
    control.onclick = async () => {
      const warning = name === 'dagster' ?
        'Start the real Dagster control UI? It uses a SEPARATE runtime database, not the evidence snapshot. It does not copy the snapshot or run builds. Real builds need normal MinIO/data prerequisites.' :
        'Start the dbt docs UI through the guarded artifact server? Only existing docs artifacts are served, not databases or Dagster storage. No generation or rebuild will run. Docs may describe a different artifact set.';
      if (!window.confirm(warning)) return;
      const origin = base;
      starts[name] = 'starting'; renderControls();
      try {
        // Deliberately lexical, private, and short-lived. Never stored on state,
        // persisted, posted to the audience, logged, or attached to a URL.
        const {token} = await request('/api/session', {}, origin);
        await request(`/api/services/${name}/start`, {
          method:'POST', headers:{'Content-Type':'application/json', 'X-Evidence-Token':token}, body:'{}',
        }, origin);
        delete starts[name];
        $('#operator-status').textContent = `${name}: process creation requested, not application readiness. Refresh checks TCP reachability.`;
      } catch (error) {
        starts[name] = `failed / ${errorMessage(error.message)}`;
        $('#operator-status').textContent = starts[name];
      }
      renderControls(); refresh();
    };
    section.append(label, control); root.append(section);
  }
}
paint(); renderControls(); refresh();
