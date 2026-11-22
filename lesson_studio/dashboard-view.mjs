import {cards, routeNext, boardBounds} from './dashboard-board.mjs';
import {fit, zoomAt, mountCamera, validCamera} from './dashboard-camera.mjs';
import {mountEvidence} from './dashboard-evidence.mjs';
import {publicLesson} from './dashboard-core.mjs';

function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (cls) node.className = cls;
  return node;
}
function button(text, click) {
  const node = el('button', text); node.type = 'button'; node.onclick = click; return node;
}

// Board/camera lifetime is independent of evidence content and observation passes.
export function mountDashboard(root, dispatch) {
  const mast = el('div', undefined, 'mast');
  mast.append(el('p', 'PROJECT SANDBOX / EVIDENCE NOTEBOOK', 'eyebrow'),
    el('span', 'LOCAL · SYNTHETIC · SAVED SNAPSHOT', 'badge'));
  const toolbar = el('nav', undefined, 'camera-tools');
  toolbar.setAttribute('aria-label', 'Canvas camera and story route');
  const surface = el('div', undefined, 'board-viewport'), world = el('div', undefined, 'board-world');
  surface.tabIndex = 0;
  surface.setAttribute('aria-label', 'Evidence canvas. Drag empty background to pan. Arrow keys pan; Home fits board; plus and minus zoom.');
  surface.append(world);
  const status = el('p', undefined, 'board-status'); status.setAttribute('role', 'status');
  root.replaceChildren(mast, toolbar, surface, status);
  const slots = {}, cardNodes = {};
  let active = 'question', applying = false;
  const zoomLabel = el('output');
  const camera = mountCamera(surface, world, fit(boardBounds()), value => {
    zoomLabel.textContent = `${Math.round(value.zoom * 100)}%`;
    if (!applying) dispatch({type:'camera', value});
  });
  zoomLabel.textContent = `${Math.round(camera.get().zoom * 100)}%`;
  function highlight(id) {
    active = id;
    for (const [key, node] of Object.entries(cardNodes)) node.setAttribute('data-active', String(key === id));
  }
  const focusCard = id => dispatch({type:'focus', value:id});
  const zoomOut = button('−', () => camera.set(zoomAt(camera.get(), 1 / 1.2)));
  zoomOut.setAttribute('aria-label', 'Zoom out');
  const zoomIn = button('+', () => camera.set(zoomAt(camera.get(), 1.2)));
  zoomIn.setAttribute('aria-label', 'Zoom in');
  toolbar.append(button('← Previous', () => dispatch({type:'route', value:routeNext(active, -1)})),
    button('Next →', () => dispatch({type:'route', value:routeNext(active, 1)})),
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
  const evidence = mountEvidence(Object.fromEntries(
    ['lineage', 'table', 'sql', 'governance', 'provenance', 'tools'].map(id => [id, slots[id]])), dispatch);
  let lessonKey;
  function updateCamera(value, card) {
    if (validCamera(value)) {
      applying = true;
      try { camera.set(value); } finally { applying = false; }
    }
    if (cards.some(item => item.id === card)) highlight(card);
  }
  function update(state) {
    status.textContent = state.busy ? 'Observing saved evidence sequentially…' : state.status;
    updateCamera(state.camera, state.activeCard);
    const lesson = publicLesson(state.lesson), key = JSON.stringify(lesson);
    if (key !== lessonKey) {
      lessonKey = key;
      cards.filter(card => card.page).forEach((card, index) => {
        const scene = lesson.scenes[index], slot = slots[card.id];
        slot.replaceChildren();
        if (scene) {
          slot.append(el('p', scene.kicker, 'eyebrow'), el('h1', scene.title), el('p', scene.body, 'lead'));
          const list = el('ul'); for (const point of scene.points) list.append(el('li', point));
          slot.append(list, el('p', lesson.disclosure, 'provenance'));
        } else slot.append(el('p', 'Portable lesson unavailable. No substitute story content.', 'empty'));
      });
    }
    evidence(state);
  }
  update.camera = camera;
  update.setCamera = updateCamera;
  update.focus = focusCard;
  update.destroy = () => camera.destroy();
  return update;
}
