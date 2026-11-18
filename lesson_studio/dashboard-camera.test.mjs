import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fit, pan, zoomAt, validCamera, minZoom, maxZoom, mountCamera} from './dashboard-camera.mjs';
import {cards, route, routeNext, boardBounds} from './dashboard-board.mjs';

test('fit, normalized pan, anchored zoom and camera validation', () => {
  const camera = fit({x:100, y:200, width:1600, height:900}, 0);
  assert.deepEqual(camera, {cx:900, cy:650, zoom:1});
  assert.deepEqual(pan(camera, 100, -50), {cx:800, cy:700, zoom:1});
  const point = {x:1200, y:300}, zoomed = zoomAt(camera, 2, point);
  const worldPoint = c => ({x:c.cx + (point.x - 800) / c.zoom, y:c.cy + (point.y - 450) / c.zoom});
  assert.deepEqual(worldPoint(camera), worldPoint(zoomed));
  assert.equal(zoomAt(camera, 100).zoom, maxZoom);
  assert.equal(zoomAt(camera, 0.0001).zoom, minZoom);
  for (const value of [null, {}, {cx:NaN,cy:0,zoom:1}, {cx:0,cy:Infinity,zoom:1},
    {cx:0,cy:0,zoom:0}, {cx:0,cy:0,zoom:5}]) assert.equal(validCamera(value), false);
  assert.throws(() => fit({x:0,y:0,width:0,height:10}));
  assert.throws(() => pan(camera, Infinity, 0));
  assert.throws(() => zoomAt(camera, -1));
});

test('board geometry and route are stable, complete and bounded', () => {
  assert.equal(new Set(cards.map(card => card.id)).size, cards.length);
  assert.equal(cards.filter(card => card.page).length, 5);
  assert.deepEqual(new Set(route), new Set(cards.map(card => card.id)));
  assert.equal(routeNext(route[0], -1), route[0]);
  assert.equal(routeNext(route.at(-1), 1), route.at(-1));
  for (let index = 0; index < route.length - 1; index++) assert.equal(routeNext(route[index], 1), route[index + 1]);
  assert.equal(validCamera(fit(boardBounds())), true);
  for (const card of cards) assert.equal(validCamera(fit(card)), true);
});

test('mounted camera excludes content, has drag threshold, suppresses clicks, preserves camera on resize', () => {
  const previous = globalThis.ResizeObserver;
  let resize, captured = false;
  globalThis.ResizeObserver = class {constructor(callback) { resize = callback; } observe() {} disconnect() {}};
  const listeners = {}, world = {style:{}};
  let width = 1600, changes = 0, prevented = 0, stopped = 0;
  const surface = {
    getBoundingClientRect:() => ({left:0,top:0,width,height:900}),
    addEventListener:(type, handler) => { listeners[type] = handler; },
    removeEventListener:type => { delete listeners[type]; },
    focus() {}, setPointerCapture() { captured = true; }, hasPointerCapture:() => captured,
    releasePointerCapture() { captured = false; }, classList:{add() {}, remove() {}},
  };
  const event = (overContent = false) => ({
    target:{closest:() => overContent}, button:0, pointerId:1, clientX:800,clientY:450,
    deltaY:100,deltaX:0,deltaMode:0,preventDefault() { prevented++; },
    stopImmediatePropagation() { stopped++; },
  });
  try {
    const controller = mountCamera(surface, world, {cx:0,cy:0,zoom:1}, () => { changes++; });
    listeners.wheel(event(true));
    listeners.pointerdown(event(true));
    assert.equal(changes, 0); assert.equal(captured, false); assert.equal(prevented, 0);
    listeners.pointerdown(event());
    assert.equal(captured, true);
    listeners.pointermove({...event(), clientX:803});
    assert.equal(changes, 0);
    listeners.pointermove({...event(), clientX:820});
    assert.equal(controller.get().cx, -20);
    listeners.pointerup(event());
    listeners.click(event());
    assert.equal(stopped, 1);
    const before = controller.get(), transform = world.style.transform;
    width = 800; resize();
    assert.deepEqual(controller.get(), before);
    assert.notEqual(world.style.transform, transform);
    listeners.wheel(event());
    assert.ok(changes > 1);
    controller.destroy();
    assert.deepEqual(listeners, {});
  } finally { globalThis.ResizeObserver = previous; }
});
