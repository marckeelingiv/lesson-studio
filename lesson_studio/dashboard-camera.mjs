// Camera units are normalized to a 1600 × 900 logical viewport, independent of
// CSS pixels. A resize changes the letterbox/scale, never the logical camera.
export const viewport = {width:1600, height:900};
export const minZoom = 0.08, maxZoom = 4;
export const maxPosition = 100000;
export function validCamera(camera) {
  return Boolean(camera && Number.isFinite(camera.cx) && Number.isFinite(camera.cy) &&
    Math.abs(camera.cx) <= maxPosition && Math.abs(camera.cy) <= maxPosition &&
    Number.isFinite(camera.zoom) && camera.zoom >= minZoom && camera.zoom <= maxZoom);
}
const clamp = zoom => Math.max(minZoom, Math.min(maxZoom, zoom));
const position = value => Math.max(-maxPosition, Math.min(maxPosition, value));
export function fit(rect, padding = 60) {
  if (![rect?.x, rect?.y, rect?.width, rect?.height, padding].every(Number.isFinite) ||
      rect.width <= 0 || rect.height <= 0 || padding < 0 || padding >= viewport.height / 2) throw Error('Invalid camera fit rectangle');
  return {cx:rect.x + rect.width / 2, cy:rect.y + rect.height / 2,
    zoom:clamp(Math.min((viewport.width - padding * 2) / rect.width, (viewport.height - padding * 2) / rect.height))};
}
export function pan(camera, dx, dy) {
  if (!validCamera(camera) || ![dx, dy].every(Number.isFinite)) throw Error('Invalid camera pan');
  return {zoom:camera.zoom, cx:position(camera.cx - dx / camera.zoom), cy:position(camera.cy - dy / camera.zoom)};
}
export function zoomAt(camera, factor, point = {x:800, y:450}) {
  if (!validCamera(camera) || !Number.isFinite(factor) || factor <= 0 ||
      ![point?.x, point?.y].every(Number.isFinite)) throw Error('Invalid camera zoom');
  const zoom = clamp(camera.zoom * factor);
  return {zoom, cx:position(camera.cx + (point.x - 800) * (1 / camera.zoom - 1 / zoom)),
    cy:position(camera.cy + (point.y - 450) * (1 / camera.zoom - 1 / zoom))};
}

// Mounted once. This module owns input and transforms only: no evidence state,
// dispatch, network requests, or content reconciliation.
export function mountCamera(surface, world, initial, onChange = () => {}) {
  if (!validCamera(initial)) throw Error('Invalid initial camera');
  let camera = initial, drag = null, suppressClick = false;
  const excluded = 'button,a,input,select,textarea,label,[role="button"],[data-camera-ignore],.card-content';
  const scale = () => {
    const rect = surface.getBoundingClientRect();
    return Math.max(0.001, Math.min(rect.width / viewport.width, rect.height / viewport.height));
  };
  function paint() {
    const rect = surface.getBoundingClientRect(), unit = scale();
    world.style.transform = `translate(${rect.width / 2}px, ${rect.height / 2}px) scale(${unit * camera.zoom}) translate(${-camera.cx}px, ${-camera.cy}px)`;
  }
  function set(next) {
    if (!validCamera(next)) throw Error('Invalid camera');
    camera = {cx:next.cx, cy:next.cy, zoom:next.zoom}; paint(); onChange({...camera});
  }
  const handlers = {
    pointerdown(event) {
      if (event.button !== 0 || event.target.closest(excluded)) return;
      suppressClick = false;
      surface.focus({preventScroll:true});
      drag = {id:event.pointerId, x:event.clientX, y:event.clientY, start:camera, moved:false};
      surface.setPointerCapture(event.pointerId);
    },
    pointermove(event) {
      if (!drag || drag.id !== event.pointerId) return;
      const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
      if (!drag.moved && Math.hypot(dx, dy) < 5) return;
      drag.moved = true; surface.classList.add('panning');
      set(pan(drag.start, dx / scale(), dy / scale()));
    },
    pointerup(event) {
      if (!drag || drag.id !== event.pointerId) return;
      suppressClick = drag.moved;
      drag = null; surface.classList.remove('panning');
      if (surface.hasPointerCapture(event.pointerId)) surface.releasePointerCapture(event.pointerId);
    },
    pointercancel(event) { handlers.pointerup(event); },
    lostpointercapture() { drag = null; surface.classList.remove('panning'); },
    click(event) {
      if (suppressClick) { event.preventDefault(); event.stopImmediatePropagation(); suppressClick = false; }
    },
    wheel(event) {
      // Never steal native table/SQL/selection scrolling, even at its edges.
      if (event.target.closest(excluded)) return;
      event.preventDefault();
      const rect = surface.getBoundingClientRect(), unit = scale();
      const delta = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? rect.height : 1;
      if (event.ctrlKey || event.metaKey) {
        set(zoomAt(camera, Math.exp(Math.max(-10, Math.min(10, -event.deltaY * delta * 0.002))),
          {x:(event.clientX - rect.left - rect.width / 2) / unit + 800,
            y:(event.clientY - rect.top - rect.height / 2) / unit + 450}));
      } else set(pan(camera, -event.deltaX * delta / unit, -event.deltaY * delta / unit));
    },
    keydown(event) {
      if (event.target !== surface || event.ctrlKey || event.metaKey || event.altKey) return;
      const arrows = {ArrowLeft:[100,0], ArrowRight:[-100,0], ArrowUp:[0,100], ArrowDown:[0,-100]};
      if (arrows[event.key]) set(pan(camera, ...arrows[event.key]));
      else if (['+', '=','-'].includes(event.key)) set(zoomAt(camera, event.key === '-' ? 1 / 1.2 : 1.2));
      else if (event.key === 'Home') set(initial);
      else return;
      event.preventDefault();
    },
  };
  for (const [type, handler] of Object.entries(handlers)) surface.addEventListener(type, handler, {passive:false, capture:type === 'click'});
  const resize = new ResizeObserver(paint); resize.observe(surface); paint();
  return {set, get:() => ({...camera}), destroy() {
    resize.disconnect();
    for (const [type, handler] of Object.entries(handlers)) surface.removeEventListener(type, handler, {capture:type === 'click'});
  }};
}
