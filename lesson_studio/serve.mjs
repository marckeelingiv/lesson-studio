// Dependency-free, loopback-only static server. No pipeline or shell execution API.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve, sep, extname} from 'node:path';

const root = fileURLToPath(new URL('.', import.meta.url));
const port = Number(process.argv[2] || 4173);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw Error('Use a port between 1 and 65535.');
const types = {'.html':'text/html', '.css':'text/css', '.js':'text/javascript', '.json':'application/json'};
const server = createServer(async (request, response) => {
  try {
    if (request.method !== 'GET' && request.method !== 'HEAD') { response.writeHead(405); response.end(); return; }
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const file = resolve(root, `.${pathname === '/' ? '/index.html' : pathname}`);
    const type = types[extname(file)];
    if (!file.startsWith(root.endsWith(sep) ? root : root + sep) || !type) { response.writeHead(404); response.end('Not found'); return; }
    const body = await readFile(file);
    response.writeHead(200, {'Content-Type':`${type}; charset=utf-8`, 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff'});
    response.end(request.method === 'HEAD' ? undefined : body);
  } catch { response.writeHead(404); response.end('Not found'); }
});
server.on('error', error => { console.error(error.message); process.exitCode = 1; });
server.listen(port, '127.0.0.1', () => console.log(`Lesson Studio: http://127.0.0.1:${port}\nOpen audience from the presenter console. Ctrl+C to stop.`));
