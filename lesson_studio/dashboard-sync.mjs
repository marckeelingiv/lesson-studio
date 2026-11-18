import {cameraState} from './dashboard-core.mjs';

// Camera-only, latest-value delivery. The trailing frame is never cancelled:
// releasing a gesture still delivers its final position, without evidence work.
export function cameraChannel({peer, origin, apply, frame = callback => requestAnimationFrame(callback)}) {
  let pending, scheduled = false;
  return {
    clear() { pending = undefined; },
    publish(value) {
      const camera = cameraState(value);
      if (!camera) return;
      pending = camera;
      if (scheduled) return;
      scheduled = true;
      frame(() => {
        scheduled = false;
        const target = peer(), camera = pending; pending = undefined;
        if (camera && target && !target.closed) target.postMessage({type:'evidence-camera-v1', camera}, origin);
      });
    },
    receive(event) {
      if (!peer() || event.source !== peer() || event.origin !== origin ||
          event.data?.type !== 'evidence-camera-v1') return false;
      const camera = cameraState(event.data.camera);
      if (!camera) return false;
      apply(camera);
      return true;
    },
  };
}
