import {mountDashboard} from './dashboard-view.mjs';
import {cameraChannel} from './dashboard-sync.mjs';
const owner = window.opener;
let updateDashboard;
const cameraSync = cameraChannel({
  peer:() => owner, origin:location.origin,
  apply:camera => { cameraSync.clear(); updateDashboard?.setCamera(camera); },
});
window.addEventListener('message', event => {
  if (!owner || event.origin !== location.origin || event.source !== owner) return;
  if (cameraSync.receive(event)) return;
  if (event.data?.type !== 'evidence-view-v1') return;
  cameraSync.clear();
  updateDashboard ||= mountDashboard(document.querySelector('#dashboard'), action => {
    if (action.type === 'camera') cameraSync.publish(action.value);
    else owner.postMessage({type: 'evidence-action-v1', action}, location.origin);
  });
  updateDashboard(event.data.state);
});
owner?.postMessage({type: 'evidence-ready-v1'}, location.origin);
