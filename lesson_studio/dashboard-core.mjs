// Pure view rules shared by the dashboard and native Node tests.
export const steps = ['Question', 'Evidence', 'Definition', 'Answer', 'Trust / limits'];

export function companionURL(value) {
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol) ||
      !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) ||
      url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw Error('Use a literal loopback HTTP(S) origin without credentials, path, query, or fragment.');
  }
  return url.origin;
}

export function safeLink(value) {
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol) ||
        !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) ||
        url.username || url.password || url.search || url.hash) return null;
    return url.href;
  } catch { return null; }
}

export function layer(node) {
  if (node.kind === 'source') return 0;
  if (/^base_/.test(node.name)) return 1;
  if (/^(stg_|staging_)/.test(node.name)) return 2;
  return 3;
}

export function branchGraph(graph, branch) {
  if (!branch || branch === 'all') return graph;
  const ids = new Set([branch]);
  // ponytail: small manifest DAG; fixed-point ancestry avoids another graph dependency.
  let changed = true;
  while (changed) {
    changed = false;
    for (const edge of graph.edges) if (ids.has(edge.target) && !ids.has(edge.source)) {
      ids.add(edge.source); changed = true;
    }
  }
  return {
    nodes: graph.nodes.filter(node => ids.has(node.id)),
    edges: graph.edges.filter(edge => ids.has(edge.source) && ids.has(edge.target)),
  };
}

export function purchaseBranch(graph) {
  return graph.nodes.find(node => layer(node) === 3 && /pricing|purchase|revenue/i.test(node.name))?.id ||
    graph.nodes.find(node => layer(node) === 3)?.id || 'all';
}

export function columnMetadata(model, column) {
  const documented = model?.columns?.find(item => item.name === column.name);
  return {
    name: column.name, type: column.type,
    description: documented?.description || 'not documented',
    owner: documented?.owner || 'not documented',
    classification: documented?.classification || 'not documented',
    data_type: documented?.data_type || 'not documented',
    meta: documented?.meta || {},
    tests: (model?.tests || []).filter(test => test.column_name === column.name),
    documented: Boolean(documented),
  };
}

// Explicit allowlist. Runtime config, requests, errors with internals, and tokens
// never become audience state, lesson JSON, localStorage, or URL parameters.
export function audienceState(state) {
  const {page, selected, branch, sqlTab, pinnedColumn, graph, model,
    observations, provenance, services, status, observedAt, busy} = state;
  return {page, selected, branch, sqlTab, pinnedColumn, graph, model,
    observations, status, observedAt, busy,
    provenance: provenance ? Object.fromEntries([
      'label', 'mode', 'snapshot_exists', 'snapshot_modified_at',
      'snapshot_build_provenance', 'snapshot_built_from_manifest',
      'manifest_generated_at', 'manifest_loaded_at', 'manifest_sha256',
    ].map(key => [key, provenance[key]])) : provenance,
    services: Object.fromEntries(Object.entries(services || {}).map(([name, service]) => [name, {
      name, url: safeLink(service.url), dashboard_url: safeLink(service.dashboard_url),
      reachable: service.reachable, state: service.state,
      missing_prerequisites: service.missing_prerequisites,
      runtime_differs_from_snapshot: service.runtime_differs_from_snapshot,
    }]))};
}

export function validAction(action, state) {
  if (!action || typeof action !== 'object') return false;
  const {type, value} = action;
  if (type === 'page') return [...steps, 'Explore'].includes(value);
  if (type === 'select') return state.graph.nodes.some(node => node.id === value);
  if (type === 'branch') return value === 'all' || state.graph.nodes.some(node => node.id === value);
  if (type === 'sqlTab') return ['source', 'compiled', 'raw'].includes(value);
  if (type === 'column') return value === null || state.model?.columns?.some(column => column.name === value) ||
    state.observations[state.selected]?.columns?.some(column => column.name === value);
  return false;
}

export function errorMessage(code) {
  return ({
    offline: 'Companion unavailable. Start it explicitly in the subject repository; no saved results are substituted.',
    query_busy: 'Observation unavailable: another snapshot query is busy. Retry with Refresh.',
    missing_snapshot: 'Snapshot missing. The companion does not create or copy it.',
    snapshot_query_unavailable: 'Snapshot query unavailable: relation, lock, external IO, resource limit, or timeout. Check the selected saved artifact.',
    response_too_large: 'Observation exceeds the bounded API response size.',
    origin_denied: 'Origin rejected. Open this UI at exactly http://127.0.0.1:4173.',
    origin_required: 'Origin required. Open this UI at exactly http://127.0.0.1:4173.',
    missing_artifacts: 'Missing docs artifacts. Generate them separately in the subject project, then retry.',
    missing_prerequisites: 'Service prerequisites are missing. Check the subject setup guide.',
    port_in_use_unowned: 'Port occupied by an unowned process. It was not adopted or stopped.',
    service_start_failed: 'Service failed to start. Inspect the subject environment separately.',
    server_closing: 'Companion is shutting down. No new service will be started.',
    token_denied: 'Session expired or denied. Retry the explicit Start action.',
  })[code] || `Unavailable (${code || 'unexpected response'}). No result substituted.`;
}
