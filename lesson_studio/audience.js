import {renderStage} from './stage.js';
const root = document.querySelector('#program');
let state;
let streams = {};
window.lessonStudio = {
  update(next) { state = next; renderStage(root, state.lesson, state.index, streams); },
  sources(next) { streams = next; if (state) renderStage(root, state.lesson, state.index, streams); },
};
document.addEventListener('dblclick', () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(() => {});
});
if (window.opener) window.opener.postMessage({type:'lesson-studio-ready'}, location.origin);
