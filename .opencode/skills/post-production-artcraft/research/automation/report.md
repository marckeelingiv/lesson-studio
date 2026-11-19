# FilmCraft automation research

## Evidence and limits

- Research date: **2026-11-19 UTC** (machine clock; task context said Nov 18).
- Local task base: `9e53d1b3b0acfc26ab7feeff93b4c6748a3f362c`.
- Official repository: https://github.com/storytold/filmcraft
- Pinned upstream: **`f67d38b35cc5af6853ef5a6921ccba014512694b`**, returned by https://api.github.com/repos/storytold/filmcraft/commits/HEAD during this research. Commit date: `2026-11-19T02:59:34Z`.
- Immutable commit metadata: https://api.github.com/repos/storytold/filmcraft/commits/f67d38b35cc5af6853ef5a6921ccba014512694b
- Immutable tree: https://api.github.com/repos/storytold/filmcraft/git/trees/f67d38b35cc5af6853ef5a6921ccba014512694b?recursive=1
- **Source review only. No FilmCraft executable, installation, build, MCP connection, command invocation, render, save/reopen, or export was locally tested.** Downloading reference text and inspecting it is the only local verification.

Downloaded originals are under `upstream/`, with upstream paths retained except the two primary docs (`agents.md`, `control-protocol.md`). `commit.json` and `tree.json` retain API evidence. Every source URL below is pinned to the same revision:

| Local source under `upstream/` | Exact download URL |
|---|---|
| `agents.md` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/agents.md |
| `control-protocol.md` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/control-protocol.md |
| `docs/project-files.md` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/project-files.md |
| `apps/filmcraft-cli/src/main.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/apps/filmcraft-cli/src/main.rs |
| `apps/filmcraft-cli/src/args.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/apps/filmcraft-cli/src/args.rs |
| `apps/filmcraft-cli/src/project_lock.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/apps/filmcraft-cli/src/project_lock.rs |
| `apps/filmcraft/src/control_server.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/apps/filmcraft/src/control_server.rs |
| `crates/automation/src/lib.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/automation/src/lib.rs |
| `crates/automation/src/server.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/automation/src/server.rs |
| `crates/automation/src/bridge.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/automation/src/bridge.rs |
| `crates/automation/src/long_job.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/automation/src/long_job.rs |
| `crates/engine/src/lib.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/lib.rs |
| `crates/engine/src/commands.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/commands.rs |
| `crates/engine/src/export_tools.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/export_tools.rs |
| `crates/engine/src/clip_ops/file.rs` | https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/clip_ops/file.rs |

## Invocation and capability discovery

Official executable names remain **`filmcraft` and `filmcraft-cli`**, not inferred `artcraft` commands. Installed Linux deb/rpm CLI path is documented as `/usr/bin/filmcraft-cli`; this does not establish an installed binary on this machine. macOS CLI is a separate release zip, not inside the desktop `.app` (`agents.md:57–72`).

Three supported entry points:

```sh
# Persistent headless MCP session; neither --project nor --demo means empty project
/absolute/path/filmcraft-cli mcp --project /absolute/work/project.fcproj
# Persistent desktop-backed MCP; desktop must already have the authenticated listener
/absolute/path/filmcraft-cli mcp --bridge 127.0.0.1:9876
# Fresh headless session for this invocation only
filmcraft-cli --project /absolute/work/project.fcproj --save run /absolute/work/steps.jsonl
```

MCP options are strictly limited to `--bridge`, `--project`, `--demo`, `--data-dir`; unknown options exit 2. In particular, **no `--save` or `--save-as` on `mcp`** and no automation root-confinement flags. Ordinary CLI bridge rejects `--project`/`--demo`; open a desktop project through its command instead (`main.rs:173–193,553–567`).

Discovery should happen against the actual backend/project, not a bare fresh CLI that cannot see current selection:

```sh
filmcraft-cli --version
filmcraft-cli --project /absolute/work/project.fcproj commands --json
filmcraft-cli --project /absolute/work/project.fcproj describe file.exportMedia
filmcraft-cli --project /absolute/work/project.fcproj inspect
# For the live app, replace --project ... with --bridge 127.0.0.1:9876.
```

- MCP `tools/list` gives formal wrapper input schemas. Core tools: `command_list`, `command_run`, `command_batch`, `doc_inspect`, `render_preview`; additional project/sequence/import/render and bridge UI tools are documented in `agents.md:74–120`.
- MCP `command_list {"filter":"export","enabled_only":false}` returns commands whose id/label contains the case-insensitive filter. `enabled_only:true` hides currently disabled commands; leave false initially to distinguish absent capability from disabled capability.
- Underlying engine `command.list {}` returns `id`, `label`, `menu`, `shortcut`, `shortcuts`, `defaultShortcut`, **`params` as a JSON-ish documentation string**, and `enabled` boolean (`commands.rs:4179–4185`). CLI `describe <id>` selects one such entry. There is no strict per-engine-command JSON Schema in this catalog.
- MCP rejects unknown **top-level tool arguments** (`-32602`), but `command_run.params` is passed through as arbitrary JSON. Wrapper schema validation does not prove command-specific argument correctness (`server.rs:54–61,570–624`).
- MCP resources `filmcraft://commands` and `filmcraft://document` mirror command catalog and document inspection.
- Raw desktop `engine.commands` discovers its command/menu registry; `engine.execute` invokes `{command,params}`. Desktop can include UI-only commands absent headlessly.
- Always obtain item/clip/sequence IDs from `doc_inspect` or project/sequence inspection. Command enablement is dynamic. Explicit documented `clip(s)`/`item(s)` targets can satisfy selection-based enablement even when catalog `enabled` is false; other preconditions still apply. Catalog enablement remains selection-based (`control-protocol.md:74–78`).
- `command_batch` is **ordered, not transactional**: each successful edit gets its own undo step; default `stop_on_error:true` stops without rolling earlier steps back (`server.rs:325–349`).

CLI parameters accept one quoted JSON object or `key=value`; JSON-looking values become JSON, otherwise strings; dotted keys nest. Options can appear anywhere. `run` consumes JSONL `{"id":"...","params":{...}}`, skips blank/comment lines, prints one JSON result per command, and stops on failure unless `--keep-going`. Exit codes: 0 success, 1 command failure, 2 usage (`args.rs`; `main.rs:64–125,406–434`).

## Transport, security, persistence

**MCP:** stdio, not an HTTP endpoint. Headless owns one in-memory `Session` behind a mutex for its process lifetime; bridge points to the desktop's existing session. Restarting headless MCP loses unsaved edits. Explicit `file.saveAs`/`file.save` checkpoints are necessary; do not assume headless autosave/recovery because the desktop supports it (`server.rs:17–20,201–249`; `main.rs:173–193`).

**Desktop raw control:** `filmcraft --control 9876` or `FILMCRAFT_CONTROL_PORT=9876`; binds `127.0.0.1` only. Requires a fresh private **64-hex-character `FILMCRAFT_CONTROL_TOKEN` per desktop session**, inherited by CLI/MCP bridge. Missing/invalid desktop token leaves listener closed. Every raw request includes the top-level token; missing/wrong credentials reject then disconnect before dispatch. Never put the secret in argv, logs, committed MCP config, or shared files. Loopback alone is not account isolation (`control-protocol.md:3–38`).

```json
{"id":1,"token":"<private inherited token>","method":"engine.execute","params":{"command":"file.saveAs","params":{"path":"/absolute/work/checkpoint.fcproj"}}}
```

One JSON object per line, one `{"id":1,"ok":true,"result":...}` or `{"id":1,"ok":false,"error":"..."}` reply per line. Not HTTP and not the MCP wire protocol. Invalid JSON/object/method, invalid UTF-8, or >4 MiB input closes the connection; maximum 16 simultaneous connections. Socket idle I/O timeout is two minutes; UI response limit 60 seconds; screenshot may fail after 10 seconds without a presented frame. Reconnect after transport errors.

Bridge source adds loopback address validation, 5-second connect/90-second reply timeouts, connection reuse and one retry on transport/parse failure (`bridge.rs:32–127`). **Inferred operational risk:** no documented deduplication guarantee; a reply-lost retry may repeat a non-idempotent edit. Inspect state before manually replaying an ambiguous mutation.

**Filesystem authority:** MCP can read/write anywhere its OS user can; there are no sandbox/read-root flags. `--data-dir` chooses user preset storage, not filesystem confinement. Restrict paths in the calling workflow and require authorization for destructive commands. Tool annotations are hints, not a security boundary.

**One-shot CLI persistence:** `exec`, `run`, `import` create fresh sessions, then save only with `--save` (back to `--project`) or `--save-as path`; explicit `file.save*` commands also work. Independent CLI invocations do not preserve selection/history/unsaved state. `run` shares one session across its lines. A failed `exec`, or first failed `run` line without `--keep-going`, exits before final flag-based save; `--keep-going` can save partial successes and still exit 1 (`main.rs:394–434`). Do not mistake exit 1 for “no files changed”.

CLI in-place flag-based saving takes `.<filename>.lock` from before load through save/exit. `--save-as` to the same input also qualifies. Desktop, MCP, and script-level `file.save` without save flags do **not** take that lock. Lock failure warns and proceeds; network/synced-folder locks may be unreliable. Atomic save prevents torn files, not last-writer-wins overwrites. Use one project writer.

## Project save/reopen contracts

Source: `commands.rs:1981–2005,5327–5414`; `docs/project-files.md`.

| Command | Parameters | Result / consequence |
|---|---|---|
| `file.save` | `{"path":str?}` | Uses explicit or adopted path; missing both is error. Saves and adopts path, clean revision. |
| `file.saveAs` | `{"path":str}` | Saves and adopts new path; names project after filename. |
| `file.saveCopy` | `{"path":str}` | Writes copy, retaining current path and unsaved state. |
| All three saves | as above | `{path,bytes,ms,backup}`; `backup` may be null. |
| `file.open` | `{"path":str}` | `{path,schemaVersion,migrated,missingMedia}`; installs project with fresh history/editor state; restores permitted saved view. |
| `file.revert` | `{}` | Reloads adopted path, discarding edits; requires saved path. |

`.fcproj` is versioned UTF-8 JSON, media referenced by path, never embedded. This revision documents schema 17; query the installed build rather than assuming compatibility. Older versions migrate in memory; original remains unchanged until save; first same-path save can create `(schema vN backup).fcproj`. Newer-than-supported schemas are refused. Save is documented atomic (same-directory temp, fsync, replace, directory fsync).

Engine invocation avoids parameter dialogs: pass required paths explicitly. `engine.execute` does not open file pickers; `ui.menu.invoke` may. Destructive confirmation commands can still ask. Desktop/UI open with unsaved changes may ask first; checkpoint before replacing project. Reopen validation should happen only after saving, preferably in a separate read-only headless invocation so the live edit/undo session is not reset. Check returned missing media and compare inspection, not just file existence.

## Export contracts and gotchas

Source: `commands.rs:2095–2110`; `export_tools.rs:612–647,1014–1039`; `agents.md:122–172,274–281`; CLI `main.rs:463–531`.

1. Discover `export.presets.list`, `export.resolve`, `file.exportMedia`, `jobs.list`, `jobs.cancel`; inspect exact installed parameter docs.
2. `export.resolve` accepts export-setting parameters and optional path; it computes `{preset,settings,range:{start,duration,seconds},frames,warnings,output,summary,source}` without starting export. Review actual settings, duration/frame count and warnings.
3. `file.exportMedia` requires `path`; optional `sequence` identifies target (otherwise active), `preset` and/or `format` and `settings` choose encoding. Common flat overrides include width/height/fps/bitrate, audio, quality, hardware encoding, captions and range. Full pinned contract is in `commands.rs:2100`.
4. Specify `range:"entire"` for whole sequence rather than relying on existing In/Out marks. Custom range uses `startSeconds` and `endSeconds`; CLI `--start/--end` maps to these and sets custom range. CLI `--range` supports entire/inOut/workArea.
5. Engine/MCP export defaults `wait:false`: immediate `{job,path,warnings,poll:"jobs.list",cancel:"jobs.cancel"}` (possibly preset and image-sequence paths). With `wait:true`, response adds `result` and `offlineMedia`, or reports export error.
6. Poll the matching ID in **`jobs.list`**, not `export.queue.list` for direct exports. Inspect `finished`, `result`, `progress`, `etaSeconds`, `offlineMedia`; cancel via `jobs.cancel {"job":id}`. Export queue is separate session state and queued items capture a project snapshot.

CLI `export` always waits, derives format from extension if no preset/format, and prints JSON plus diagnostics. Local CLI `exec`/`run` also inject `wait:true` for `file.exportMedia` unless explicitly false. **Do not request background export in a short-lived headless CLI process:** it exits before work can finish.

MCP `command_run` + `wait:true` supports progress token and cancellation, polls without holding the whole session lock, and cleans the cancelled export's partial files. Use a direct `command_run` for this path, not assume batch has identical progress behavior. Bridge wait starts an app job and polls at 250 ms rather than blocking the UI response deadline.

**Success is not deliverable approval:**

- Offline media renders placeholder frames. MCP/engine export may succeed with nonempty `offlineMedia`; reject it explicitly. CLI `export`/`render` writes output then exits 1 unless `--allow-offline`; generic `exec file.exportMedia` is not that CLI-specific offline gate. Preflight `media.status`/`media.findMissing`.
- A one-frame marked In/Out export warns but still succeeds. Always review resolved duration and warnings.
- `hardwareEncoding:"auto"` can fall back to software. Inspect `result.encoder` and result warnings; request is not proof of GPU encoding.
- Output path can change extension. Image sequences return first still as `path`, plus `lastPath` and `basePath`; requested `a.png` may become `a000.png` etc. Use returned paths, not assumptions.
- Successful export/render proves execution only. Inspect rendered frames and listen/watch the deliverable before claiming visual/audio quality.

## Proposed runtime recipe (source-backed; not executed)

1. **Preflight:** resolve approved existing binary; capture `--version`/help. Keep all project/checkpoints/renders under this repository's `video_pipeline/workspace/<video-filename>/`; leave source recordings intact. Inspect existing project and media status before edits.
2. **Choose one session:** persistent headless MCP for engine edits, authenticated desktop bridge when live UI review is needed, or one JSONL CLI run for deterministic scripts. One writer owns each project.
3. **Discover:** MCP `tools/list`, `command_list` with disabled commands visible, then inspect exact relevant command parameter docs. Inspect document IDs, active sequence, selection and enabled prerequisites; handle explicit target exception deliberately.
4. **Checkpoint:** `command_run {"id":"file.saveAs","params":{"path":"<absolute workspace checkpoint>.fcproj"}}`; confirm returned path. Use a new name rather than overwriting an unapproved existing file.
5. **Edit/review:** issue small command runs with inspected IDs; inspect after edits; render previews and actually view them. Use undo only for undoable edits, not filesystem side effects. Save accepted state explicitly.
6. **Reopen verification:** fresh CLI `--project <saved checkpoint> inspect` plus media checks; compare intended sequences/tracks/clips. This verifies serialized state without resetting the live session. CLI inspection alone is not visual review.
7. **Export preflight:** discover presets; `export.resolve` with explicit target/range/preset/path. Confirm dimensions, frame count, audio/captions and duration. Then direct `command_run file.exportMedia` with `wait:true`, or CLI `export --range entire`; inspect errors, warnings, offline media and returned paths.
8. **Acceptance:** verify output exists and is decodable; inspect representative rendered frames/video and audio against the task. Record binary version, project/checkpoint path, exact export parameters, resulting paths and review evidence. Treat unmet checks as blockers, not inferred success.
