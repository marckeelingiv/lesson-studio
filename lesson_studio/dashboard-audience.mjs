import {mountDashboard} from './dashboard-view.mjs';
const owner = window.opener;
let updateDashboard;
window.addEventListener('message', event => {
  if (event.origin !== location.origin || event.source !== owner ||
      event.data?.type !== 'evidence-view-v1') return;
  updateDashboard ||= mountDashboard(document.querySelector('#dashboard'), action => {
    owner?.postMessage({type: 'evidence-action-v1', action}, location.origin);
  });
  updateDashboard(event.data.state);
});
owner?.postMessage({type: 'evidence-ready-v1'}, location.origin);
