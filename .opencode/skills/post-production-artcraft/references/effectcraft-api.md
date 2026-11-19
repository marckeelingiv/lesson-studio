# EffectCraft: optional isolated compositing

**FilmCraft first.** Use this branch only for a demonstrated visual result the picture editor cannot suitably produce. Ordinary titles and authored scale/position zooms do not justify another app. Prefer an isolated, silent rendered overlay/shot over converting the whole timeline.

Evidence: inspected upstream documentation/source at **`665bfac0b33904b1dcda6de889f43f43a94ad3f8`**. No local executable, save/reopen, render or FilmCraft reimport was tested. The workflow below is a candidate; production use is **blocked until the disposable-sample gate passes**. Setup, downloads and configuration changes need separate authorization.

## 1. Connect and discover

- Headless: `effectcraft-cli mcp` owns an in-memory project, not the desktop document.
- Live app: `effectcraft --control <port>` with `effectcraft-cli mcp --bridge <port>`. Choose the actual authorized port; this is EffectCraft's bridge syntax, not SoundCraft's.
- Discover the connected server's MCP `tools/list`, then `get_state`, `get_project`, `get_comp {}`. Use `list_commands {"filter":"renderQueue","schemas":true}` and `describe_command {"command":"renderQueue.add"}` before queue mutation. Obtain actual IDs and property paths from replies.

MCP tools and engine IDs are different layers. These are source-documented **tool-name → arguments** examples, not raw control-channel messages:

```text
describe_command → {"command":"comp.new"}
execute_command → {"command":"comp.new","params":{"name":"Intro","width":1920,"height":1080,"frameRate":30,"duration":4}}
render_frame → {"time":1.0,"transparent":true}
```

The 30 fps/four-second composition is a disposable example, not a delivery default. Use the target's actual rate, dimensions and bounded duration. `command_run` instead takes `{id,params?}`. `batch` takes `steps:[{command,params}]` with atomic rollback/one undo; `command_batch` takes `steps:[{id,params?}]`, is ordered/non-atomic and has per-edit undo. Read per-step/render-item failures and `isError`, not only transport success. [Interfaces and schemas][agents]; [MCP envelopes and failures][mcp].

## 2. Author, checkpoint, reopen

1. Record target FilmCraft revision, intended placement, frame rate, frame count, dimensions, color/alpha interpretation and dependencies in the run's handoff.
2. Author only the bounded asset. Keyframe writes (`set_property`, `add_keyframe`, engine `prop.set`/`prop.addKey`) default to **layer seconds**; queries and frame renders use **composition seconds**. Use `timeBase:"comp"` for comp-time writes. Offsets/stretch/reversal matter; writes snap to comp frames. Inspect returned `compTime`, `layerTime` and warnings. [Timing contract][timing].
3. `save_project {"path":"<absolute unique run path>/overlay.ecproj"}` explicitly checkpoints the native project. Headless work otherwise disappears on restart. Optional `mcp --autosave` is not a substitute: checkpoint warnings require an explicit successful save before disconnecting. Save a dirty project before opening another.
4. Reopen using `open_project {"path":"<saved absolute path>"}`, inspect composition/layers and dependencies, and execute engine `footage.check` with `{"wait":true}` through `execute_command`. Resolve missing assets before rendering. Keep a dependency manifest: native project JSON alone does not make absolute footage paths portable. [Persistence and media checks][agents].

## 3. Render a bounded intermediate

1. Discover `renderQueue.add`, queue inspection/settings and `renderQueue.render` schemas on the selected build. Set an explicit fresh output, composition/range, full resolution, format and channels; inspect the resulting queue before rendering. Use the exact-length composition or verified work-area range; do not guess range parameter names.
2. For transparency, the documented queue settings include `format:"prores"`, `proresProfile:"4444"`, `channels:"rgba"`, and `output`; PNG sequence is another candidate. Execute `renderQueue.render` with `{"wait":true}` via `execute_command`, then inspect every item/status and returned file. H.264 is not an alpha route. [Render settings][renders]; [formats and bounded spans][guide].
3. Inspect actual rendered first/middle/last frames, alpha over light/dark backgrounds, color, readable text, frame count and rate. For PNG sequences, carry numbering, sequence rate and duration explicitly. ProRes 4444 straight-alpha readback is an upstream claim, not proof of FilmCraft's interpretation.
4. Keep FilmCraft program audio unchanged and mute/omit intermediate audio. Any authorized shot-with-audio replacement additionally needs sample-count, codec-delay and transient/sync checks.

**Interchange limit:** no verified Dynamic Link or shared native editing exists here. Upstream explicitly reports FilmCraft rejection of EffectCraft `.fcgt` export; do not promise template compatibility. Timeline conversion is a separate, lossy trial, not the default overlay handoff. [Format limitations][formats].

## Safety and acceptance gate

- Use unique run-local output/project paths; source-protection checks do not protect every unrelated existing file from overwrite.
- When confinement is authorized, `--automation-read-root` and `--automation-write-root` restrict access; EffectCraft permits reads under read **or write** roots and requires absolute in-root paths. Confined mode refuses scripts and bridge UI-driving tools. Without root flags, this confinement is absent. [Confinement][mcp].
- A bridge mutation with a lost/malformed reply may already have applied. Inspect document/queue/files before an explicit retry; never blindly replay an unknown outcome. [Retry behavior][agents].
- **Blocking trial:** save → close/reopen → check dependencies → bounded render to fresh output → inspect actual frames → import/place in a disposable FilmCraft revision → verify alpha/color, first/last frame, duration/rate, offset and unchanged program-audio sync → obtain human review. Record hashes, warnings, timings and corrections. Until observed, report **source-inspected, reimport unvalidated**, not “integrated” or “reviewed.”

[agents]: https://github.com/storytold/effectcraft/blob/665bfac0b33904b1dcda6de889f43f43a94ad3f8/docs/agents.md
[timing]: https://github.com/storytold/effectcraft/blob/665bfac0b33904b1dcda6de889f43f43a94ad3f8/docs/agents.md#L134-L161
[renders]: https://github.com/storytold/effectcraft/blob/665bfac0b33904b1dcda6de889f43f43a94ad3f8/docs/agents.md#L353-L385
[mcp]: https://github.com/storytold/effectcraft/blob/665bfac0b33904b1dcda6de889f43f43a94ad3f8/docs/mcp.md
[guide]: https://github.com/storytold/effectcraft/blob/665bfac0b33904b1dcda6de889f43f43a94ad3f8/docs/user/guides/render-a-video.md
[formats]: https://github.com/storytold/effectcraft/blob/665bfac0b33904b1dcda6de889f43f43a94ad3f8/docs/file-format-parity.md#L21-L35
