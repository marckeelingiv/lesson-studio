import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {createServer} from 'node:net';

test('serves the moved starter without exposing files outside static roots', async () => {
  const reservation = createServer();
  reservation.listen(0, '127.0.0.1');
  await once(reservation, 'listening');
  const port = reservation.address().port;
  await new Promise(resolve => reservation.close(resolve));
  const server = spawn(process.execPath, [new URL('./serve.mjs', import.meta.url).pathname, String(port)]);
  try {
    await Promise.race([
      once(server.stdout, 'data'),
      once(server, 'exit').then(() => { throw Error('Server exited before startup'); }),
    ]);
    const base = `http://127.0.0.1:${port}`;
    assert.equal((await fetch(base)).status, 200);
    const response = await fetch(`${base}/lessons/de-for-fun/event-to-answer/presenter.json`);
    assert.equal(response.status, 200);
    const lesson = await response.json();
    assert.equal(lesson.scenes.length, 6);
    assert.equal(lesson.scenes.reduce((sum, scene) => sum + scene.seconds, 0), 115);
    for (const path of ['/dashboard.html', '/dashboard-audience.html', '/dashboard.css',
      '/dashboard.mjs', '/dashboard-audience.mjs', '/dashboard-view.mjs', '/dashboard-core.mjs',
      '/dashboard-board.mjs', '/dashboard-camera.mjs']) {
      const result = await fetch(`${base}${path}`);
      assert.equal(result.status, 200, path);
      if (path.endsWith('.mjs')) assert.match(result.headers.get('content-type'), /text\/javascript/);
    }
    assert.equal((await fetch(`${base}/api/lineage`)).status, 404); // Static server has no companion proxy.
    assert.equal((await fetch(`${base}/api/services/docs/start`, {method:'POST'})).status, 405);
    const story = await (await fetch(`${base}/lessons/de-for-fun/purchase-evidence/presenter.json`)).json();
    assert.equal(story.scenes.length, 5);
    for (const path of ['/lessons/README.md', '/CONTENT_ASSETS.md', '/lessons/%2e%2e%2flesson_studio/serve.mjs', '/%2e%2e%2fCONTENT_ASSETS.md']) {
      assert.equal((await fetch(`${base}${path}`)).status, 404, path);
    }
  } finally {
    server.kill();
    await once(server, 'exit');
  }
});
