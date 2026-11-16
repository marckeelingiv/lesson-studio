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
