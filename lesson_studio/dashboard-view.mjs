import {layer, branchGraph, columnMetadata, safeLink, errorMessage} from './dashboard-core.mjs';
import {cards, routeNext, boardBounds} from './dashboard-board.mjs';
import {fit, zoomAt, mountCamera} from './dashboard-camera.mjs';

// All companion/lesson text is assigned through textContent, including SQL,
// table cells, SVG labels, metadata and errors. No payload HTML is interpreted.
function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (cls) node.className = cls;
  return node;
}
function button(text, click, current = false) {
  const node = el('button', text);
  node.type = 'button'; node.onclick = click;
  node.setAttribute('aria-pressed', String(current));
  return node;
}
function panel(title) {
  const node = el('section', undefined, 'panel');
  node.append(el('h2', title)); return node;
}
function link(text, url) {
  const node = el('a', text);
  const safe = safeLink(url);
  if (safe) { node.href = safe; node.target = '_blank'; node.rel = 'noopener noreferrer'; }
  return node;
}
function json(value) { return JSON.stringify(value, null, 2); }

export function mountDashboard(root, dispatch) {
  const act = (type, value) => dispatch({type, value});
  const mast = el('div', undefined, 'mast');
  mast.append(el('p', 'PROJECT SANDBOX / EVIDENCE NOTEBOOK', 'eyebrow'),
    el('span', 'LOCAL · SYNTHETIC · SAVED SNAPSHOT', 'badge'));
  const toolbar = el('nav', undefined, 'camera-tools');
  toolbar.setAttribute('aria-label', 'Canvas camera and story route');
  const surface = el('div', undefined, 'board-viewport'), world = el('div', undefined, 'board-world');
  surface.tabIndex = 0; surface.setAttribute('aria-label', 'Evidence canvas. Drag empty background to pan. Arrow keys pan; Home fits board; plus and minus zoom.');
  surface.append(world);
  const status = el('p', undefined, 'board-status'); status.setAttribute('role', 'status');
  root.replaceChildren(mast, toolbar, surface, status);
  const slots = {}, cardNodes = {};
  let active = 'question';
  const camera = mountCamera(surface, world, fit(boardBounds()), value => {
    zoomLabel.textContent = `${Math.round(value.zoom * 100)}%`;
  });
  const zoomLabel = el('output', `${Math.round(camera.get().zoom * 100)}%`);
  function focusCard(id) {
    const card = cards.find(item => item.id === id);
    if (!card) return;
    active = id; camera.set(fit(card));
    for (const [key, node] of Object.entries(cardNodes)) node.setAttribute('data-active', String(key === id));
  }
  const zoomOut = button('−', () => camera.set(zoomAt(camera.get(), 1 / 1.2)));
  zoomOut.setAttribute('aria-label', 'Zoom out');
  const zoomIn = button('+', () => camera.set(zoomAt(camera.get(), 1.2)));
  zoomIn.setAttribute('aria-label', 'Zoom in');
  toolbar.append(button('← Previous', () => focusCard(routeNext(active, -1))),
    button('Next →', () => focusCard(routeNext(active, 1))),
    zoomOut, zoomLabel, zoomIn,
    button('Home / fit board', () => camera.set(fit(boardBounds()))),
    el('small', 'Drag background · scroll to pan · Ctrl/⌘ scroll to zoom · Focus a card to read'));
  for (const card of cards) {
    const node = el('section', undefined, `board-card ${card.page ? 'slide-card' : ''}`);
    node.dataset.card = card.id;
    Object.assign(node.style, {left:`${card.x}px`, top:`${card.y}px`, width:`${card.width}px`, height:`${card.height}px`});
    const head = el('header', undefined, 'card-head');
    head.append(el('h2', card.title), button('Focus', () => focusCard(card.id)));
    const content = el('div', undefined, 'card-content'); content.tabIndex = 0;
    content.setAttribute('aria-label', `${card.title} content`);
    node.append(head, content); world.append(node); slots[card.id] = content; cardNodes[card.id] = node;
  }
  const titles = {
    Question: ['Evidence, before the answer.', 'Which purchase patterns deserve a closer look?'],
    Evidence: ['Follow the purchase evidence.', 'A declared dependency is not proof of a running pipeline. Inspect the saved tables behind the question.'],
    Definition: ['Define the number before trusting it.', 'Read the transformation, inspect its grain, and compare documented columns with the observed snapshot.'],
    Answer: ['Turn a question into a defensible insight.', 'Inspect a configured Lightdash dashboard only after its metric definition and warehouse connection are verified.'],
    'Trust / limits': ['Make the limits part of the answer.', 'This is a local portfolio sandbox with synthetic data, not a claim of production adoption or customer impact.'],
  };
  for (const card of cards.filter(item => item.page)) {
    const [title, body] = titles[card.page], slot = slots[card.id];
    slot.append(el('p', 'THE BUSINESS STORY / SLIDE PLACEHOLDER', 'eyebrow'), el('h1', title), el('p', body, 'lead'));
  }
  slots.question.append(el('p', 'Proposed question: how do arena purchase patterns vary across the dimensions actually documented in the purchase mart? Verify the model grain and measures before choosing a chart.', 'big-question'),
    el('p', 'Start with a business decision, trace its dependencies, inspect the SQL and column contract, then open the real analytical surface. If the evidence or setup is missing, stop at the prerequisite—not a simulated answer.'));
  slots.evidence.append(button('Inspect lineage →', () => focusCard('lineage')));
  slots.definition.append(button('Inspect transformation →', () => focusCard('sql')));
  slots.answer.append(button('Inspect Lightdash prerequisites →', () => focusCard('tools')));
  slots.trust.append(button('Read provenance and limits →', () => focusCard('provenance')));
  let lastPage, lastContent;
  function update(state) {
    status.textContent = state.busy ? 'Observing saved evidence sequentially…' : state.status;
    if (state.page !== lastPage) {
      focusCard(state.page === 'Explore' ? 'lineage' : cards.find(card => card.page === state.page)?.id);
      lastPage = state.page;
    }
    // ponytail: stable cards, transitional slot rendering. Deep keyed evidence
    // reconciliation (including inner scroll/focus) is the next content wave.
    const content = JSON.stringify([state.graph, state.branch, state.selected, state.model, state.observations,
      state.sqlTab, state.pinnedColumn, state.provenance, state.services]);
    if (content === lastContent) return;
    lastContent = content;
    const focus = root.contains(document.activeElement) ? document.activeElement?.dataset.focus : null;
    for (const id of ['lineage', 'table', 'sql', 'governance', 'provenance', 'tools']) slots[id].replaceChildren();
    renderGraph(slots.lineage, state, act);
    renderDetail(slots.table, state, act, slots);
    if (!slots.sql.children.length) slots.sql.append(el('p', 'Select a queryable manifest model to inspect its actual SQL. No substitute transformation.', 'empty'));
    if (!slots.governance.children.length) slots.governance.append(el('p', 'Select a queryable manifest model, then hover or focus a column to inspect its documented contract. No inferred metadata.', 'empty'));
    renderProvenance(slots.provenance, state, true);
    renderAnswer(slots.tools, state);
    renderServices(slots.tools, state);
    slots.tools.append(el('p', 'Open ≠ Start. TCP availability is not authenticated readiness. Dagster can perform real work.', 'warning'));
    if (focus) [...root.querySelectorAll('[data-focus]')].find(node => node.dataset.focus === focus)?.focus({preventScroll:true});
  }
  update.camera = camera;
  update.focus = focusCard;
  update.destroy = () => camera.destroy();
  return update;
}

function renderGraph(root, state, act) {
  const section = panel('Declared lineage / observed counts');
  const head = el('div', undefined, 'panel-head');
  const label = el('label', 'Spotlight ');
  const select = el('select'); select.setAttribute('aria-label', 'Lineage branch');
  for (const node of [{id:'all', name:'Full graph'}, ...state.graph.nodes.filter(node => layer(node) === 3)]) {
    const option = el('option', node.name); option.value = node.id; select.append(option);
  }
  select.value = state.branch; select.onchange = () => act('branch', select.value); select.dataset.focus = 'branch';
  label.append(select); head.append(label, el('small', 'SOURCE → BASE → STAGING → MART · static lineage, not execution'));
  section.append(head);
  const graph = branchGraph(state.graph, state.branch);
  if (!graph.nodes.length) { section.append(el('p', 'Manifest unavailable. Connect the companion to inspect actual lineage.', 'empty')); root.append(section); return; }
  const positions = new Map(), columns = [0, 1, 2, 3].map(index => graph.nodes.filter(node => layer(node) === index));
  const height = Math.max(...columns.map(nodes => nodes.length), 1) * 96 + 55;
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg'); svg.setAttribute('viewBox', `0 0 1080 ${height}`); svg.classList.add('lineage');
  svg.setAttribute('role', 'group'); svg.setAttribute('aria-label', 'Manifest lineage. Nodes select tables; edges select downstream SQL.');
  const shape = (tag, attrs, text) => {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const defs = shape('defs', {}), marker = shape('marker', {
    id:'lineage-arrow', viewBox:'0 0 10 10', refX:9, refY:5,
    markerWidth:6, markerHeight:6, orient:'auto-start-reverse',
  });
  marker.append(shape('path', {d:'M 0 0 L 10 5 L 0 10 z', fill:'#79e4bc'}));
  defs.append(marker); svg.append(defs);
  columns.forEach((nodes, x) => {
    svg.append(shape('text', {x:x * 270 + 12, y:22, class:'layer'}, ['SOURCE', 'BASE', 'STAGING', 'MART'][x]));
    nodes.forEach((node, y) => positions.set(node.id, {x:x * 270 + 8, y:y * 96 + 45}));
  });
  for (const edge of graph.edges) {
    const from = positions.get(edge.source), to = positions.get(edge.target);
    if (!from || !to) continue;
    const x1 = from.x + 230, y1 = from.y + 30, x2 = to.x, y2 = to.y + 30;
    const d = from.x === to.x ?
      `M${x1},${y1} C${x1 + 32},${y1} ${x1 + 32},${y2} ${x1},${y2}` :
      `M${x1},${y1} C${x1 + 35},${y1} ${x2 - 35},${y2} ${x2},${y2}`;
    const group = shape('g', {class:'edge', tabindex:0, role:'button', 'aria-label':`Inspect downstream SQL: ${edge.source} to ${edge.target}`});
    const choose = () => { act('select', edge.target); act('page', 'Definition'); };
    group.onclick = choose; group.onkeydown = event => { if (['Enter', ' '].includes(event.key)) { event.preventDefault(); choose(); } };
    group.append(shape('path', {d, class:'wire', 'marker-end':'url(#lineage-arrow)'}), shape('path', {d, class:'wire-hit'})); svg.append(group);
  }
  for (const node of graph.nodes) {
    const {x, y} = positions.get(node.id), observation = state.observations[node.id];
    const group = shape('g', {class:`node ${node.id === state.selected ? 'selected' : ''}`, tabindex:0, role:'button', 'aria-label':`Inspect ${node.name}`, 'data-focus':node.id});
    group.onclick = () => act('select', node.id);
    group.onkeydown = event => { if (['Enter', ' '].includes(event.key)) { event.preventDefault(); act('select', node.id); } };
    const count = !node.queryable ? 'Lineage only · not queried' : observation?.error ? 'Observation unavailable' :
      observation?.row_count !== undefined ? `${observation.row_count.toLocaleString()} rows · observed` : 'Not observed';
    group.append(shape('rect', {x,y,width:230,height:64,rx:8}),
      shape('text', {x:x+10,y:y+24}, node.name), shape('text', {x:x+10,y:y+47,class:'count'}, count));
    const title = shape('title', {}, node.id); group.append(title); svg.append(group);
  }
  const scroll = el('div', undefined, 'graph-wrap'); scroll.append(svg); section.append(scroll,
    el('small', 'Counts may be from separate requests; they are not an atomic cross-table snapshot. Refresh is controlled privately. Sources are never queried.'));
  root.append(section);
}

function renderDetail(root, state, act, slots) {
  const node = state.graph.nodes.find(node => node.id === state.selected);
  const model = state.model?.id === state.selected ? state.model : null;
  const observation = state.observations[state.selected];
  const section = panel(node ? node.name : 'Choose an evidence node');
  if (!node) { section.append(el('p', 'No manifest model selected.', 'empty')); root.append(section); return; }
  if (!node.queryable) {
    section.append(el('p', 'Source node: lineage only. Raw external source tables are not queried. Select a downstream model or a wire to inspect its SQL.', 'warning'));
    root.append(section); return;
  }
  section.append(el('p', `${node.id} · relation ${node.schema}.${node.identifier}`, 'provenance'));
  if (!model) section.append(el('p', 'Model metadata / SQL unavailable or being observed. No inferred documentation.', 'warning'));
  if (model) section.append(el('p', model.description || 'Model description: not documented'));
  const grid = el('div', undefined, 'grid');
  const tablePanel = el('div');
  if (observation?.error) tablePanel.append(el('p', errorMessage(observation.error), 'warning'));
  else if (!observation) tablePanel.append(el('p', 'No completed observation for this model.', 'empty'));
  else {
    tablePanel.append(el('div', `${observation.row_count.toLocaleString()} rows`, 'count-number'),
      el('p', `Completed observation: ${observation.observed_at} · ${observation.snapshot_label}`, 'provenance'),
      el('p', `Preview: ${observation.rows.length} of ${observation.row_count} rows · maximum ${observation.row_limit} · order ${observation.order}. No sorting or pagination.`, 'muted'));
    const scroll = el('div', undefined, 'table-scroll'); scroll.tabIndex = 0; scroll.setAttribute('aria-label', 'Scrollable bounded table preview');
    const table = el('table'), head = el('thead'), row = el('tr'), body = el('tbody');
    for (const column of observation.columns) {
      const th = el('th'); th.scope = 'col';
      const control = button(`${column.name} ⓘ`, () => act('column', state.pinnedColumn === column.name ? null : column.name), state.pinnedColumn === column.name);
      control.dataset.focus = `column:${column.name}`;
      control.setAttribute('aria-describedby', 'column-governance');
      control.onmouseenter = control.onfocus = () => { if (!state.pinnedColumn) showColumn(column); };
      control.onmouseleave = control.onblur = () => { if (!state.pinnedColumn) showColumn(null); };
      th.append(control); row.append(th);
    }
    head.append(row);
    for (const values of observation.rows) {
      const tr = el('tr');
      for (const value of values) tr.append(el('td', value === null ? 'NULL' : typeof value === 'object' ? json(value) : value));
      body.append(tr);
    }
    table.append(head, body); scroll.append(table); tablePanel.append(scroll);
    const comparison = observation.schema_comparison;
    if (comparison) {
      tablePanel.append(el('p', `Schema check — documented columns missing: ${comparison.documented_columns_missing.join(', ') || 'none detected'}; undocumented snapshot columns: ${comparison.undocumented_snapshot_columns.join(', ') || 'none detected'}; SQL freshness references absent in snapshot: ${comparison.freshness_sql_references_missing.join(', ') || 'none detected'}.`, 'warning'),
        el('small', `Scope: ${comparison.scope}. This is not freshness measurement or full SQL validation.`));
    }
  }
  const governance = el('aside', undefined, 'governance'); governance.id = 'column-governance';
  if (model && !observation?.columns?.length) {
    const declarations = el('div', undefined, 'sql-tabs');
    tablePanel.append(el('h3', 'Documented columns / no observed schema'));
    for (const column of model.columns) {
      const choose = button(`${column.name} ⓘ`, () => act('column', state.pinnedColumn === column.name ? null : column.name), state.pinnedColumn === column.name);
      choose.dataset.focus = `column:${column.name}`;
      choose.setAttribute('aria-describedby', 'column-governance');
      choose.onmouseenter = choose.onfocus = () => { if (!state.pinnedColumn) showColumn({name:column.name, type:'unavailable'}); };
      choose.onmouseleave = choose.onblur = () => { if (!state.pinnedColumn) showColumn(null); };
      declarations.append(choose);
    }
    tablePanel.append(declarations);
  }
  function showColumn(column) {
    governance.replaceChildren(el('h3', 'Column contract / parsed dbt YAML'));
    governance.append(el('p', 'Hover or focus a column header. Click to pin; click again to release. Test declarations below are not test results.', 'muted'));
    if (!column) { governance.append(el('p', 'No column selected. Undocumented fields are never inferred.', 'empty')); return; }
    const meta = columnMetadata(model, column), dl = el('dl');
    for (const [label, value] of [['Column', meta.name], ['Observed type', meta.type], ['Declared type', meta.data_type],
      ['Description', meta.description], ['Owner', meta.owner], ['Classification', meta.classification]]) {
      dl.append(el('dt', label), el('dd', value));
    }
    governance.append(dl, el('h3', 'Additional documented metadata'), el('pre', Object.keys(meta.meta).length ? json(meta.meta) : 'not documented'),
      el('h3', 'Declared column tests (not results)'), el('pre', meta.tests.length ? json(meta.tests) : 'not documented'));
    if (model?.metadata_provenance) governance.append(el('p', `Metadata: ${model.metadata_provenance.kind}; ${model.metadata_provenance.patch_path || 'patch path not documented'}; manifest ${model.metadata_provenance.manifest_sha256}. ${model.metadata_provenance.note}`, 'provenance'));
  }
  showColumn(observation?.columns?.find(column => column.name === state.pinnedColumn) ||
    (model?.columns.find(column => column.name === state.pinnedColumn) ? {name:state.pinnedColumn, type:'unavailable'} : null));
  if (slots) { section.append(tablePanel); slots.governance.append(governance); }
  else { grid.append(tablePanel, governance); section.append(grid); }
  if (model) {
    const sql = panel('Transformation / inspect, never execute');
    const tabs = el('div', undefined, 'sql-tabs');
    for (const [value, name] of [['source','Current source SQL'], ['compiled','Compiled manifest SQL'], ['raw','Raw manifest SQL']]) {
      const tab = button(name, () => act('sqlTab', value), state.sqlTab === value);
      tab.dataset.focus = `sql:${value}`; tabs.append(tab);
    }
    const source = state.sqlTab === 'source';
    sql.append(tabs, el('p', source ?
      `Current worktree source · ${model.source_sql.status} · ${model.source_sql.path || 'path unavailable'} · observed ${model.source_sql.observed_at || 'unavailable'} · SHA-256 ${model.source_sql.sha256 || 'unavailable'}` :
      `Loaded manifest SQL · SHA-256 ${model.manifest_sql.manifest_sha256}`, 'provenance'),
    el('p', 'Current SQL and loaded manifest SQL may differ. Neither proves which code built this saved database. Snapshot build provenance: unknown.', 'warning'),
    el('pre', (source ? model.source_sql.text : model.manifest_sql[state.sqlTab]) ?? 'SQL unavailable — no substitute text.'),
    el('p', `Model owner: ${model.owner} · classification: ${model.classification}`, 'provenance'),
    el('h3', 'All model test declarations (not execution results)'), el('pre', model.tests.length ? json(model.tests) : 'not documented'));
    (slots?.sql || section).append(sql);
  }
  root.append(section);
}

function renderAnswer(root, state) {
  const lightdash = state.services.lightdash;
  const section = panel('Business insight / Lightdash handoff');
  section.append(el('p', 'Proposed analysis: compare purchase patterns at the verified mart grain. Confirm available dimensions, aggregation, units, time boundaries, and snapshot scope before naming a measure or claiming a trend.'));
  if (safeLink(lightdash?.dashboard_url)) {
    section.append(link('Open configured Lightdash dashboard ↗', lightdash.dashboard_url),
      el('p', 'Configured destination, not a verified result. TCP reachability does not verify login, project existence, dashboard content, or warehouse connectivity.', 'warning'));
  } else {
    section.append(el('h3', 'Prerequisite: connect a real business dashboard'),
      el('p', 'No configured dashboard is available. No chart or metric result is substituted.', 'warning'),
      el('p', `Missing: ${lightdash?.missing_prerequisites?.join(', ') || 'companion availability and a verified Lightdash project/dashboard'}.`),
      el('p', 'Operator handoff: follow the subject evidence-dashboard prerequisite guide; verify the existing Lightdash project and warehouse connection, then configure EVIDENCE_LIGHTDASH_URL, EVIDENCE_LIGHTDASH_PROJECT, and EVIDENCE_LIGHTDASH_DASHBOARD in the companion environment. Never place credentials in lesson content or links.'));
  }
  root.append(section);
}

function renderProvenance(root, state, expanded) {
  const section = panel(expanded ? 'What this evidence can—and cannot—establish' : 'Evidence provenance / always visible');
  const p = state.provenance;
  section.append(el('p', p?.warning || 'Companion evidence unavailable. No fallback dataset, sample counts, or simulated results are shown.', 'warning'));
  if (p) section.append(el('p', `${p.label} · mode ${p.mode} · snapshot ${p.snapshot_exists ? 'exists' : 'missing'} · snapshot file modified ${p.snapshot_modified_at || 'unknown'} (not a build timestamp)`, 'provenance'),
    el('p', `Snapshot build provenance: ${p.snapshot_build_provenance}. Built from loaded manifest: ${p.snapshot_built_from_manifest}. Manifest generated: ${p.manifest_generated_at || 'unknown'}; loaded: ${p.manifest_loaded_at}; SHA-256 ${p.manifest_sha256}.`, 'provenance'));
  section.append(el('p', 'Current source SQL, session-loaded manifest / parsed YAML, and the saved read-only database are different evidence surfaces. They are not guaranteed to be the same build. Observation time is response time, not data generation time. Docs can describe a separate artifact set.', 'warning'));
  if (expanded) {
    const list = el('ul');
    for (const text of ['No production impact, real customer data, end-to-end event tracing, or pipeline freshness is demonstrated.',
      'Counts are exact for each completed relation observation; up to 50 unordered rows are shown. Separate requests need not be mutually consistent.',
      'Manifest dependencies and test declarations are not successful execution or test results.',
      'Schema checks cover documented columns and literal generated_at/latest_timestamp references, not full SQL or type validation.',
      'Service availability is a TCP probe, not authenticated identity or application readiness. Dagster can perform real work against a separate runtime database.']) list.append(el('li', text));
    section.append(list);
  }
  root.append(section);
}

function renderServices(root, state) {
  const grid = el('section', undefined, 'services'); grid.setAttribute('aria-label', 'External evidence surfaces');
  for (const name of ['dagster', 'docs', 'lightdash']) {
    const service = state.services[name], section = panel(name === 'docs' ? 'dbt Docs' : name === 'dagster' ? 'Dagster' : 'Lightdash');
    section.append(el('p', !service ? 'Unavailable / companion offline' : service.reachable ? 'Available TCP port · application not authenticated' :
      service.state === 'exited' ? 'Failed / owned process exited' : service.missing_prerequisites?.length ? 'Missing prerequisites / artifacts' :
      service.state === 'running' ? 'Starting / port not reachable' : 'Unavailable / not started', service?.reachable ? 'muted' : 'unavailable'));
    const url = name === 'lightdash' ? service?.dashboard_url : service?.url;
    if (safeLink(url)) section.append(link(`Open ${name === 'lightdash' ? 'configured dashboard' : name} ↗`, url));
    if (service?.missing_prerequisites?.length) section.append(el('p', `Missing: ${service.missing_prerequisites.join(', ')}`));
    if (name === 'dagster') section.append(el('p', 'Real control UI. Its separate runtime database is NOT this evidence snapshot. Builds require the normal MinIO/data prerequisites.', 'warning'));
    if (name === 'docs') section.append(el('p', 'Existing docs artifacts only. They may differ from this session’s evidence manifest.', 'muted'));
    if (name === 'lightdash') section.append(el('p', 'External service; no automatic start or setup. Login, project, dashboard, and warehouse connection remain unverified.', 'muted'));
    grid.append(section);
  }
  root.append(grid);
}
