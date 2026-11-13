import {renderStage, validateLesson} from './stage.js';
const $ = id => document.getElementById(id);
const storageKey = 'lesson-studio-v1';
let lesson, index = 0, audience, camera, screen, recorder, recordingStream;
let started = 0, sceneStarted = performance.now(), markers = [], chunks = [], takes = [];
let pendingRecording = false;
const report = message => { $('status').textContent = message; };
const time = seconds => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
const streams = () => ({camera, screen});
const stop = stream => stream?.getTracks().forEach(track => track.stop());

function download(data, name, type = 'application/json') {
  const blob = data instanceof Blob ? data : new Blob([JSON.stringify(data, null, 2)], {type});
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

function sync() {
  renderStage($('preview'), lesson, index, streams());
  if (audience && !audience.closed && audience.lessonStudio) {
    audience.lessonStudio.update({lesson, index});
    audience.lessonStudio.sources(streams());
  }
}

function render() {
  const scene = lesson.scenes[index];
  $('lesson-title').textContent = lesson.title;
  $('scene-title').textContent = scene.title;
  $('notes').textContent = scene.notes || 'No presenter notes for this scene.';
  $('evidence').textContent = scene.evidence ? `Show: ${scene.evidence}` : '';
  $('website').value = scene.type === 'website' ? scene.url : '';
  $('website-link').hidden = scene.type !== 'website';
  if (scene.type === 'website') $('website-link').href = scene.url;
  $('previous').disabled = index === 0; $('next').disabled = index === lesson.scenes.length - 1;
  $('scenes').replaceChildren();
  lesson.scenes.forEach((item, position) => {
    const button = document.createElement('button');
    button.className = `scene-button ${position === index ? 'active' : ''}`;
    button.setAttribute('aria-current', position === index ? 'step' : 'false');
    const number = document.createElement('span'); number.textContent = String(position + 1).padStart(2, '0');
    const text = document.createElement('span'); text.textContent = item.title;
    const meta = document.createElement('small'); meta.textContent = `${item.type} / ${item.seconds || '—'} sec`;
    text.append(meta); button.append(number, text); button.onclick = () => select(position);
    $('scenes').append(button);
  });
  sync();
}

function saveLesson() {
  $('editor').value = JSON.stringify(lesson, null, 2);
  try { localStorage.setItem(storageKey, JSON.stringify(lesson)); }
  catch { report('Browser storage unavailable. Export the lesson to preserve edits.'); }
}

function mark(kind) {
  const entry = {kind, sourceSeconds: recorder?.state === 'recording' ? +((performance.now() - started) / 1000).toFixed(3) : null, scene: index + 1, title: lesson.scenes[index].title, at: new Date().toISOString()};
  markers.push(entry); return entry;
}
function select(next) {
  if (next < 0 || next >= lesson.scenes.length) return;
  index = next; sceneStarted = performance.now();
  if (recorder?.state === 'recording') mark('scene');
  render();
}

function openAudience() {
  audience = window.open('./audience.html', 'lesson-studio-audience', 'popup,width=1280,height=720');
  if (!audience) report('Popup blocked. Allow this local page to open the audience window, then retry.');
  else report('Audience opened. Move it to your recording display; double-click its stage for fullscreen.');
}
$('open').onclick = openAudience;
window.addEventListener('message', event => {
  if (event.origin === location.origin && event.source === audience && event.data?.type === 'lesson-studio-ready') sync();
});
$('previous').onclick = () => select(index - 1);
$('next').onclick = () => select(index + 1);
document.addEventListener('keydown', event => {
  if (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'SUMMARY', 'A'].includes(document.activeElement.tagName) || event.altKey || event.metaKey || event.ctrlKey) return;
  if (event.key === 'ArrowRight') { event.preventDefault(); select(index + 1); }
  if (event.key === 'ArrowLeft') { event.preventDefault(); select(index - 1); }
});
$('guides').onchange = () => $('preview').classList.toggle('show-guides', $('guides').checked);
$('preview').classList.add('show-guides');

$('camera').onclick = async () => {
  if (camera) { stop(camera); camera = null; $('camera').textContent = 'Enable camera'; sync(); return; }
  try {
    camera = await navigator.mediaDevices.getUserMedia({video:{width:{ideal:640},height:{ideal:480}},audio:false});
    camera.getVideoTracks()[0].onended = () => { camera = null; $('camera').textContent = 'Enable camera'; sync(); };
    $('camera').textContent = 'Disable camera'; sync(); report('Camera live on the audience stage.');
  } catch (error) { report(`Camera unavailable: ${error.message}`); }
};
$('share').onclick = async () => {
  try {
    const next = await navigator.mediaDevices.getDisplayMedia({video:true, audio:false});
    stop(screen); screen = next;
    screen.getVideoTracks()[0].onended = () => { screen = null; sync(); report('Shared source ended. Choose another source when ready.'); };
    lesson.scenes[index].type = 'screen'; saveLesson(); render();
    report('Shared source live. Use its original window to scroll, type, or interact.');
  } catch (error) { report(`Source selection cancelled or unavailable: ${error.message}`); }
};
$('stop-share').onclick = () => { stop(screen); screen = null; sync(); };
$('show-website').onclick = () => {
  try {
    const next = structuredClone(lesson); next.scenes[index].type = 'website'; next.scenes[index].url = $('website').value;
    lesson = validateLesson(next); saveLesson(); render();
    report('Website selected. If it refuses to load, open the site and use tab capture instead.');
  } catch (error) { report(error.message); }
};

function apply(value) {
  if (recorder?.state === 'recording' || pendingRecording) throw Error('Stop recording before replacing the lesson.');
  lesson = validateLesson(value); index = 0; sceneStarted = performance.now(); saveLesson(); render();
}
$('apply').onclick = () => { try { apply(JSON.parse($('editor').value)); report('Lesson applied and saved in this browser.'); } catch (error) { report(error.message); } };
$('import').onchange = async event => {
  try { const file = event.target.files[0]; if (file) { apply(JSON.parse(await file.text())); report(`Imported ${file.name}.`); } }
  catch (error) { report(`Import failed: ${error.message}`); }
  event.target.value = '';
};
$('export').onclick = () => download(lesson, 'lesson.json');
async function starter() {
  const response = await fetch('./lessons/event-to-answer.json');
  if (!response.ok) throw Error(`Starter lesson failed to load (${response.status}).`);
  apply(await response.json());
}
$('reset').onclick = async () => { try { await starter(); report('Starter loaded.'); } catch (error) { report(error.message); } };

$('record').onclick = async () => {
  if (!audience || audience.closed) { report('Open the audience window before recording.'); return; }
  if (!window.MediaRecorder || !navigator.mediaDevices?.getDisplayMedia) { report('Recording requires a desktop browser with screen capture on localhost. Use OBS instead.'); return; }
  pendingRecording = true; $('record').disabled = true;
  let capture, microphone;
  try {
    // The browser owns source selection; never silently capture this console.
    capture = await navigator.mediaDevices.getDisplayMedia({video:{frameRate:{ideal:30}},audio:false,preferCurrentTab:false,selfBrowserSurface:'exclude'});
    microphone = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true}, video:false});
    recordingStream = new MediaStream([...capture.getVideoTracks(), ...microphone.getAudioTracks()]);
    const mimeType = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm'].find(type => MediaRecorder.isTypeSupported(type));
    recorder = new MediaRecorder(recordingStream, mimeType ? {mimeType,videoBitsPerSecond:6000000} : undefined);
    chunks = []; markers = []; started = performance.now();
    const take = {version:1, lesson:structuredClone(lesson), startedAt:new Date().toISOString(), recordingName:`lesson-take-${new Date().toISOString().replaceAll(':','-').replaceAll('.','-')}`, markers};
    recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
    recorder.onerror = event => report(`Recording error: ${event.error?.message || 'unknown'}. Stop and check the resulting file.`);
    recorder.onstop = () => {
      const blob = new Blob(chunks, {type:recorder.mimeType || 'video/webm'});
      stop(capture); stop(microphone); recordingStream = null;
      take.durationSeconds = +((performance.now() - started) / 1000).toFixed(3);
      take.markers = structuredClone(markers);
      take.sourceFile = `${take.recordingName}.${blob.type.includes('mp4') ? 'mp4' : 'webm'}`;
      const url = URL.createObjectURL(blob); takes.push({url, take});
      const link = document.createElement('a'); link.href = url; link.download = take.sourceFile; link.textContent = `↓ Download raw take ${takes.length} (${(blob.size / 1024 / 1024).toFixed(1)} MB)`;
      const notes = document.createElement('button'); notes.textContent = `Download notes for take ${takes.length}`; notes.onclick = () => download(take, `${take.recordingName}.json`);
      $('downloads').append(link, notes);
      $('stop-record').disabled = true; $('record').disabled = false; $('record').classList.remove('recording'); $('record').textContent = '● Record audience + microphone';
      report('Take ready. Download the raw video and take notes before closing this page. Keep the original for the editing pipeline.');
    };
    capture.getVideoTracks()[0].onended = () => { if (recorder.state !== 'inactive') recorder.stop(); };
    microphone.getAudioTracks()[0].onended = () => { if (recorder.state !== 'inactive') recorder.stop(); };
    recorder.start(1000); mark('scene');
    $('record').classList.add('recording'); $('record').textContent = '● Recording'; $('stop-record').disabled = false;
    report('Recording started. Confirm the audience tab is selected. Pause one second between sections; restart full sentences on mistakes.');
  } catch (error) {
    stop(capture); stop(microphone); recordingStream = null; $('record').disabled = false;
    report(`Recording did not start: ${error.message}`);
  } finally { pendingRecording = false; }
};
$('stop-record').onclick = () => { if (recorder?.state === 'recording') recorder.stop(); };
$('marker').onclick = () => { const entry = mark('retake'); report(entry.sourceSeconds === null ? 'Marked rehearsal note (no recording timestamp).' : `Edit point marked at ${time(entry.sourceSeconds)}. Restart the full sentence after a short pause.`); };
$('export-take').onclick = () => download({version:1,lesson,markers,exportedAt:new Date().toISOString(),timing: 'sourceSeconds are raw recording offsets; null means rehearsal. These notes are not a pipeline EDL.'}, 'take-notes.json');
setInterval(() => {
  const recording = recorder?.state === 'recording';
  $('timing').textContent = `${recording ? 'REC ' : 'SCENE '}${time((performance.now() - (recording ? started : sceneStarted)) / 1000)}${!recording && lesson ? ` / ${lesson.scenes[index].seconds || '—'}s` : ''}`;
  $('connection').textContent = audience && !audience.closed ? '● Audience connected' : 'Audience closed';
}, 500);
window.addEventListener('beforeunload', event => {
  if (recorder?.state === 'recording' || takes.length) { event.preventDefault(); event.returnValue = ''; }
});
window.addEventListener('pagehide', () => { stop(camera); stop(screen); stop(recordingStream); takes.forEach(take => URL.revokeObjectURL(take.url)); });
try {
  const saved = localStorage.getItem(storageKey);
  if (saved) { try { apply(JSON.parse(saved)); } catch { await starter(); report('Invalid saved lesson; starter restored.'); } }
  else await starter();
} catch (error) { report(`Unable to load lesson: ${error.message}. Serve this folder over localhost HTTP.`); }
