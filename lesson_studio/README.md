# Lesson Studio

Read [the overall mission](../LESSON_FRAMEWORK_MISSION.md) for purpose and principles, and the [presenter experiment](../experiments/presenter-assisted-delivery.md) for its hypothesis and evaluation. This guide describes one experimental implementation, not a required presentation format.
Read [repository and asset ownership](../CONTENT_ASSETS.md) when locating plans, templates, recordings, publication records, or external repositories. The [lesson library](../lessons/README.md) owns content independently of this tool; the [DE series](../lessons/de-for-fun/README.md) links to the subject's technical evidence.

A local recording desk: one private presenter console, one clean audience window, and portable JSON lessons. Plain HTML/CSS/JavaScript with a Node standard-library server. No installation, external fonts, hosted services, or data-stack dependencies.

## Start

From the repository root:

```bash
node lesson_studio/serve.mjs
```

Open **http://127.0.0.1:4173** in desktop Chrome/Chromium. An optional port argument changes the port (`node lesson_studio/serve.mjs 4174`). Use the same origin for both windows. HTTP on loopback is required for browser media permissions; opening the HTML as `file://` is unsupported.

1. Click **Open audience**. Allow the popup if blocked. Move the audience window to the display you will record. Double-click its stage for fullscreen.
2. Enable your camera from the console. Its audience position is bottom-right, **above** the bottom 15% reserved for pipeline captions. The console preview includes optional guides; these never appear in the audience window.
3. Select scenes, read your private notes, and use Previous/Next or the arrow keys outside form controls. Each scene has a suggested duration; the timer is advisory.
4. For a native editor, assistant, or browser tab, click **Choose screen / window / tab**, then select it in the browser's permission picker. The current scene becomes a shared-source scene. Switch sources with the same button. Manipulate VS Code or the website in its **original window**; the shared video is a read-only view.
5. For a localhost page or embeddable site, enter its absolute HTTP(S) URL and choose **Show website**. It replaces the current scene's content type. The audience iframe is interactive. The console's preview is a separate instance, so its scroll/navigation are not synchronized with the audience. Prefer tab capture when presenting interactions.

Sites may refuse iframes through CSP or X-Frame-Options, authentication, or browser restrictions. This app cannot reliably detect every refusal. Use **Open site to interact**, then share that tab. HTTPS pages can also block HTTP embeds: use this loopback HTTP server. Sharing a whole display that contains the stage can create a mirror effect; share the specific source window/tab instead.

The console must remain open to own the camera, source streams, and recordings. Audience reloads reconnect to it. Only one presenter console should control the named audience window at a time. Refreshing/closing the console releases streams. Your browser may require a click in the audience to resume media playback.

## Rehearse → record → edit → publish

### Prepare and rehearse

Start with the [first lesson's brief](../lessons/de-for-fun/event-to-answer/brief.md). Its `presenter.json` contains the six scenes of the 115-second Project Sandbox walkthrough, including narration and evidence prompts. It intentionally includes no invented results: capture the real event, metric definition, and MCP answer. Rehearse these before recording. The live data platform is separate; this studio neither starts its services nor runs shell commands. The server exposes the sibling library's JSON under `/lessons/`; it does not expose the repository root.

Use **Lesson editor & files** to edit and apply JSON or import a lesson. Save exported JSON as `lessons/<subject>/<lesson-id>/presenter.json` to version it. Changes persist only in this browser origin's local storage until exported; changing ports changes browser storage. **Load starter lesson** replaces local edits; export first if needed. Replacing a lesson while recording is blocked.

Supported scene types:

| Type | Content | Private fields |
| --- | --- | --- |
| `slide` | `title`, `body`, `points` (strings) | `notes`, `evidence`, `seconds` |
| `code` | `title`, `code`, optional `body` caption | Same |
| `screen` | Live browser-selected window/tab/screen | Same |
| `website` | Absolute `url` in an iframe | Same |

Top-level fields: `version: 1`, `title`, optional `disclosure`, and `scenes`. `kicker` is optional on all scenes. Lesson content is plain text, never arbitrary lesson-supplied HTML. A shared source is session state and must be selected again next session.

### Record

**Browser recording:** open the audience, configure sources and camera, then click **Record audience + microphone**. In the picker select the **Lesson Studio · Audience tab**, not the console or source window. The browser controls selection; the app cannot guarantee you selected the intended surface. Allow microphone access. Capture starts after both permissions succeed. Confirm the actual captured surface before narrating. The recorder includes microphone audio, not system/tab audio. Its camera is already composited into the audience page.

Use **Mark retake / edit point** to annotate raw recording time. Pause one second between sections and restart the whole sentence after mistakes. Click **Stop recording**, then download **both the raw video and its take-specific notes**. Multiple takes have separate download links and notes. Source-ended or microphone-ended events also stop recording.

The recorder keeps chunks in browser memory until download (ponytail: suitable for short lessons; use OBS for long sessions or durable recording). Do not close/refresh the console before downloading. Browser screen capture and camera behavior depends on your OS/browser; on Linux/Wayland it also requires a functioning desktop capture portal. Capture failures show in the console. No camera/microphone permissions are requested automatically.

**OBS alternative:** capture only the audience window at 1920×1080, 30 fps with microphone audio. Use the audience's built-in camera overlay or OBS's camera layer, not both. Keep the private console on another display or outside the selected window. OBS can also handle source audio and long recordings. Record MKV for recovery if preferred, then remux to MP4. Take-note timestamps are available only with the built-in recorder; rehearsal markers have `sourceSeconds: null`.

### Process with video_pipeline

Preserve the original download outside Git. The existing pipeline probes WebM and other FFmpeg-supported formats; a downloaded WebM can be passed directly as input. From the **repository root**, once the pipeline is set up:

```bash
make video-setup
make video-run VIDEO_INPUT=/absolute/path/lesson-take.webm VIDEO_MODEL=opencode
```

Or, without the root Makefile (useful when moving these directories):

```bash
uv run --project video_pipeline python video_pipeline/src/cli.py run /absolute/path/lesson-take.webm --model opencode
```

See [the recording and editing guide](../video_pipeline/README.md) for authentication, setup, stage commands, and output artifacts. Processing is an explicit terminal step; the browser does not execute local commands or upload your footage.

Take-note JSON records lesson content and raw recording offsets. It is **not** the pipeline's `edl.json` and is not automatically consumed. Use it to review cuts and scene changes. The planner receives transcript and edit candidates, **not screen frames**, so inspect visual continuity after cuts. Review the FCPXML in Resolve or preview the render before publishing.

The camera clears the caption band; content also clears the reserved camera area. Pipeline callouts may still overlap meaningful screen content: review `graphic_cues` in `edl.json`, reposition/omit conflicting graphics, then reassemble/render. Check the final output for readable code, captions, face framing, and clean transitions. Rendering success alone is insufficient.

### Publish and log

Preserve and link each lesson's script, source recording, take notes, pipeline workspace, reviewed output, and publication record according to [repository and asset ownership](../CONTENT_ASSETS.md). Choose subsequent DE lessons from the subject's content plan.

## Move to a separate repository

Copy `lesson_studio/`, `lessons/`, and `video_pipeline/` together as sibling directories. The studio resolves its assets and the lesson library from its own file location. It has no imports from the data project and no baked-in worktree path. Lessons, media, and pipeline are independent. Use the direct pipeline command above or include `video_pipeline/Makefile.mk` in the new root Makefile. Carry over the pipeline's ignore rules for `.venv`, `node_modules`, workspace output, and media. Never move a dependency environment as source.

## Verification limits

Automated checks can validate lesson JSON and serving behavior. Camera hardware, Linux capture permissions, the selected recording surface, microphone levels, third-party embedding, and final edit quality require a real recording rehearsal on your machine.

## Interactive evidence desk

Launch the same static server with `node lesson_studio/serve.mjs`. Open
**http://127.0.0.1:4173/dashboard.html** (also linked as **Evidence desk** from the
studio). No install/build step or subject checkout is required. The default
landing is a persistent pan/zoom canvas: five portable story slides (**Question →
Evidence → Definition → Answer → Trust / limits**) above actual lineage,
table, SQL, governance, provenance and external-tool cards. There are no page
tabs. Drag empty background or scroll it to pan; Ctrl/⌘-scroll zooms around the
pointer. **Focus** fits a card, **Home / fit board** fits everything, and
**Previous / Next** follows the ordered story/evidence route. With the viewport
focused, arrows pan and Home / + / − control the camera. Table and SQL scrolling
never pans the board. The desk loads the existing portable
[purchase-evidence script](../lessons/de-for-fun/purchase-evidence/presenter.json)
at startup; only `kicker`, `title`, `body`, `points` and `disclosure` survive
the public projection. Notes, evidence prompts and scene timing never enter the
board or audience messages. Missing lesson content is labeled unavailable.
The script can also be imported into the original presenter; its starter lesson
is unchanged.

### Private desk and clean capture

1. At the private evidence desk, click **Open clean audience**. The destination
   is `/dashboard-audience.html`, opened from the desk—not an independently
   configured iframe. Keep the desk open.
2. Either window can change branch, selected node, SQL tab and
    pinned column. A node selects its model and focuses the bounded table card;
    a wire selects its downstream model and focuses the SQL card in one action.
    Hover/focus column headers for
   documented metadata; click to pin/release the card. When observation fails,
   documented column buttons remain inspectable without pretending to know
   the saved schema. Temporary hover is local; pinning is synchronized.
    Camera gestures synchronize in both directions using camera-only messages,
    coalesced to at most one per animation frame, including the trailing position.
    They do not fetch evidence or send table payloads. Focus and Previous/Next
    use validated board card IDs; the private desk owns authoritative state.
    Reloading the audience receives the current camera and sanitized evidence.
3. **Capture the evidence audience window**, not the private desk. Use OBS window
   capture, or select the evidence audience tab through the original presenter's
   **Choose screen / window / tab** and record the original studio audience as
   usual. Interact in the evidence desk or its clean source window; shared video
   is read-only. The dashboard does not add another recorder/camera system.
4. The bridge accepts messages only from the exact expected window and exact
   same origin. Only allowlisted display state and validated selections cross.
   Service-start controls, session tokens, operator config and notes do not.
   Provenance is projected onto rendered evidence fields only; absolute snapshot
   and manifest paths (and future unrecognized provenance fields) stay private.
   Clean audience code has no fetch/session/start API. It requires its opener;
   opening it directly shows an honest waiting page.

Do not embed separate dashboard instances in the console and audience and
expect interaction to synchronize. Do not capture the private desk. External
Dagster/docs/Lightdash tabs are real separate apps; their interactions are not
bridged. Share/capture the actual external tab separately when needed. Existing
generic website scenes retain their original independent-iframe behavior.

### Optional companion and observation limits

The private desk defaults to `http://127.0.0.1:4174`; its runtime origin field
accepts literal loopback HTTP(S) origins only, without credentials, paths, query
strings or fragments. It is not persisted. Use exactly
**http://127.0.0.1:4173** for the studio browser origin—the subject API does not
allow `localhost:4173`, other ports, or `file://`.

Subject prerequisites, API v1 routes/payloads, service ownership and explicit
launch commands are owned by [DE for Fun's evidence contract at 14ce47d](https://github.com/marckeelingiv/de-for-fun/blob/14ce47d4f59c18c9cc29be8899ea53ca0d6255bc/docs/evidence-dashboard.md).
Prepare/start that companion explicitly in the subject repository; this static
server has no shell imports, subject paths, API proxy, service execution or
snapshot fallback.

The desk makes sequential read-only GETs to `/api/provenance`, `/api/services`,
`/api/lineage`, `/api/models/{encoded-manifest-id}`, and
`/api/models/{encoded-manifest-id}/observation`. It observes the selected model
and visible branch models; full graph observes all returned queryable models.
Sources are lineage-only. **Refresh observations** is manual; optional 15-second
polling starts its next delay only after the previous pass completes. Selection
changes during work queue one later pass. There is only one observation queue;
no parallel preview loop or continuous row-flow animation.

Counts are relation observations, not throughput. Previews contain at most 50
unordered rows, without pagination/sorting/query parameters. Different requests
are not an atomic cross-model snapshot. `429 query_busy`, missing/locked snapshot,
unavailable relations, external-IO blocks and resource/time limits show honest
unavailable states without fabricated counts. A failed observation clears that
model's previous result; a companion connection failure clears evidence entirely.
No automatic restart or retry storm runs when polling is off.

The manifest is session-loaded; current SQL is read on demand; the saved database
has unknown build provenance. Source and manifest SQL tabs show their own
hash/time provenance, **not** “the SQL that built this snapshot.” Always-readable
warnings preserve the snapshot label, unknown build relationship, schema mismatch
lists and limited SQL-reference checks. dbt metadata comes from manifest-parsed
YAML; absent fields say **not documented**, and tests are **declarations, not
results**. No metric answer is computed or fabricated by this frontend.

### Open versus Start; Lightdash setup handoff

- **Open** follows a validated, secret-free loopback URL in a new tab. A reachable
  TCP port is labeled **not authenticated**; it does not verify identity,
  login, application readiness or warehouse connectivity.
- **Start Dagster / Start docs** appear only on the private desk. Each requires a
  confirmation, then fetches `/api/session` and POSTs exactly `{}` to
  `/api/services/{dagster|docs}/start` with `Content-Type: application/json` and
  `X-Evidence-Token`. The token exists only in that handler's private runtime
  memory, never lesson content, localStorage, URLs, logs or audience messages.
  Starting/failed/missing-prerequisite/available states are distinct. Refresh
  checks later process state/reachability; process creation is not readiness.
- Dagster is a real control UI using a **separate runtime database**, not a copy
  of the evidence snapshot. Builds need normal MinIO/data prerequisites. The
  frontend never materializes data or activates schedules.
- The dbt docs UI is served by the companion's guarded artifact server, not
  raw `dbt docs serve`. It only serves existing `manifest.json`, `catalog.json`
  and `index.html` on loopback with strict Host checks, no directory listings,
  and no symlinks. Databases and Dagster storage are never served.
  Missing artifacts require separate subject-side preparation. It never runs
  generation, and docs can differ from the selected evidence manifest.
- Lightdash is external and is **not started or configured here**. The current
  rehearsal has no configured project/dashboard and an offline service; do not
  present it as a working analytical result. The Answer step proposes a business
  question and shows missing prerequisites instead of a fake chart.
  Complete the subject contract's **Services and explicit starts → Lightdash**
  prerequisites: verify an existing project, warehouse connection and dashboard,
  then provide `EVIDENCE_LIGHTDASH_URL`, `EVIDENCE_LIGHTDASH_PROJECT`, and
  `EVIDENCE_LIGHTDASH_DASHBOARD` privately to the companion. No Lightdash token is
  read or sent by this frontend. Once configured, **Open configured dashboard**
  opens the actual returned dashboard URL; its content still requires review.

### Native checks

```sh
node --test lesson_studio/serve.test.mjs lesson_studio/dashboard.test.mjs lesson_studio/dashboard-camera.test.mjs
```

These cover static routes, branch/action/camera rules, portable-field sanitation,
URL boundaries, metadata joins, text-only rendering, audience serialization,
camera-only message ordering and origin/source checks, retained table/header
identity and scroll/focus, offline clearing, and sequential
observation coordination with fake responses. No subject services or browser
targets are started. Actual layout, clean-window interaction/capture, popup
behavior, keyboard usability in a browser and external app readiness remain
separate verification work. No visual quality is established by these checks.

### Canvas implementation seams

- `dashboard-board.mjs`: plain stable card rectangles and ordered route.
- `dashboard-camera.mjs`: pure fit/pan/anchored-zoom rules and mounted native
  input/transform controller. Camera units use a 1600×900 logical viewport;
  resize preserves `{cx, cy, zoom}`. This module never observes evidence.
- `dashboard-view.mjs`: `mountDashboard(root, dispatch)` returns `update(state)`.
  Mount once per window. The viewport, world, cards and content slots persist;
  `update.camera`, `update.setCamera(camera, activeCard?)`, `update.focus(id)` and
  `update.destroy()` expose framing and cleanup. Applying authoritative camera
  state does not dispatch it again. Evidence refresh never auto-fits the camera.
- `dashboard-evidence.mjs`: `mountEvidence(slots, dispatch)` returns
  `update(state)`, owning lineage/table/SQL/governance/provenance/tools content,
  with no camera or network knowledge. Native reconciliation retains table
  wrappers and header controls when schema/selection are unchanged; rows,
  counts, status and handlers update in place. SQL/governance scroll is retained
  for the same model selection; changing models can replace detail content.
- `dashboard-core.mjs`: `publicLesson`, `cameraState`, `validAction`,
  `applyAction` and `audienceState` centralize sanitizing and validated actions.
  Camera centers are finite and bounded to ±100,000 logical units; zoom is
  0.08–4. Only known card/route IDs and actual manifest model IDs are accepted.
- `dashboard-sync.mjs`: `cameraChannel({peer, origin, apply, frame?})` returns
  `publish`, `receive`, `clear`. Exact-window/same-origin camera delivery is
  latest-value per animation frame. Full authoritative views supersede pending
  gestures; audience gestures are accepted without an echo. Background windows
  may have animation-frame delivery throttled by the browser.

No browser/visual acceptance is established by the integration checks. Review
real framing, readability, clean-window gestures, keyboard use, scrolling and
capture separately. Subject data realism/exposure investigation is separate work;
this integration does not change the subject application or its evidence.
