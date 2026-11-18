import {renderDashboard} from './dashboard-view.mjs';
const owner = window.opener;
window.addEventListener('message', event => {
  if (event.origin !== location.origin || event.source !== owner ||
      event.data?.type !== 'evidence-view-v1') return;
  renderDashboard(document.querySelector('#dashboard'), event.data.state, action => {
    owner?.postMessage({type: 'evidence-action-v1', action}, location.origin);
  });
});
owner?.postMessage({type: 'evidence-ready-v1'}, location.origin);
