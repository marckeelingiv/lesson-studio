// Shared DOM renderer; lesson text is never interpreted as HTML.
export function renderStage(root, lesson, index, streams = {}) {
  const scene = lesson.scenes[index];
  // Keep media and iframe elements alive while changing notes or camera settings.
  if (root.dataset.scene !== JSON.stringify([lesson.title, index, scene])) {
    root.replaceChildren();
    const el = (tag, cls, text) => {
      const node = document.createElement(tag);
      if (cls) node.className = cls;
      if (text !== undefined) node.textContent = text;
      return node;
    };
    const mast = el('div', 'stage-mast');
    mast.append(el('span', '', lesson.title), el('span', '', `${String(index + 1).padStart(2, '0')} / ${String(lesson.scenes.length).padStart(2, '0')}`));
    const content = el('section', 'stage-content');
    content.append(el('div', 'stage-kicker', scene.kicker || 'PROJECT SANDBOX'), el('h1', '', scene.title));
    if (scene.type === 'slide') {
      content.append(el('p', 'stage-body', scene.body || ''));
      const list = el('ul', 'stage-points');
      for (const point of scene.points || []) list.append(el('li', '', point));
      content.append(list);
    } else if (scene.type === 'code') {
      const code = el('code', '', scene.code || '');
      const pre = el('pre'); pre.append(code); content.append(pre);
      content.append(el('p', 'source-caption', scene.body || ''));
    } else if (scene.type === 'screen') {
      const video = el('video', 'source-video'); video.autoplay = true; video.muted = true; video.playsInline = true;
      content.append(video, el('p', 'source-placeholder', 'Shared source is not connected. Choose a window or tab in the presenter console.'));
    } else if (scene.type === 'website') {
      const frame = el('iframe'); frame.src = scene.url; frame.title = scene.title;
      frame.referrerPolicy = 'no-referrer';
      // Local sites may need scripts and origin storage; popups/top navigation are excluded.
      frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms');
      content.append(frame);
    }
    const camera = el('video', 'camera-video'); camera.autoplay = true; camera.muted = true; camera.playsInline = true;
    const reserve = el('div', 'camera-reserve', 'CAMERA');
    const footer = el('div', 'stage-footer', lesson.disclosure || '');
    root.append(mast, content, reserve, camera, footer, el('div', 'caption-guide', 'CAPTION SAFE ZONE'));
    root.dataset.scene = JSON.stringify([lesson.title, index, scene]);
  }
  for (const [selector, stream] of [['.camera-video', streams.camera], ['.source-video', streams.screen]]) {
    const video = root.querySelector(selector);
    if (!video) continue;
    const active = stream?.getVideoTracks().some(track => track.readyState === 'live');
    video.hidden = !active;
    if (video.srcObject !== (active ? stream : null)) video.srcObject = active ? stream : null;
    if (active) video.play().catch(() => {});
    if (selector === '.camera-video') root.querySelector('.camera-reserve').hidden = active;
    if (selector === '.source-video') root.querySelector('.source-placeholder').hidden = active;
  }
}

export function validateLesson(value) {
  if (!value || value.version !== 1 || typeof value.title !== 'string' || !value.title.trim()) throw Error('Lesson needs version: 1 and a title.');
  if (!Array.isArray(value.scenes) || !value.scenes.length || value.scenes.length > 100) throw Error('Use 1–100 scenes.');
  for (const field of ['disclosure']) if (value[field] !== undefined && typeof value[field] !== 'string') throw Error(`${field} must be text.`);
  for (const scene of value.scenes) {
    if (!scene || !['slide', 'code', 'screen', 'website'].includes(scene.type) || typeof scene.title !== 'string') throw Error('Each scene needs a title and type: slide, code, screen, or website.');
    for (const field of ['body', 'code', 'notes', 'evidence', 'kicker']) if (scene[field] !== undefined && typeof scene[field] !== 'string') throw Error(`${field} must be text.`);
    if (scene.points !== undefined && (!Array.isArray(scene.points) || scene.points.some(p => typeof p !== 'string'))) throw Error('points must be a list of strings.');
    if (scene.seconds !== undefined && (!Number.isFinite(scene.seconds) || scene.seconds <= 0)) throw Error('seconds must be a positive number.');
    if (scene.type === 'website') {
      let url;
      try { url = new URL(scene.url); } catch { throw Error('Website scenes require an absolute HTTP(S) URL.'); }
      if (!['http:', 'https:'].includes(url.protocol)) throw Error('Website scenes require an HTTP(S) URL.');
    }
  }
  return value;
}
