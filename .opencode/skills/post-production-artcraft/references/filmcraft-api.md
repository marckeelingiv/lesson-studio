# FilmCraft automation reference

**Source-inspected, not locally runtime-tested.** Contracts below come from official FilmCraft revision **`f67d38b35cc5af6853ef5a6921ccba014512694b`**. No executable, MCP connection, model, edit, save/reopen or export was tested for this reference. Verify the installed build on the disposable sample before production.

Read the [shared handoff](../../post-production/references/handoff.md) and [native handoff extension](handoff.md) for ownership, capability acceptance, workspace, revision and review rules. Only the producer mutates native projects or exports; specialists deliver proposals. This reference supplies API evidence, not a substitute acceptance gate.

## 1. Discover the actual session

Executable names are `filmcraft` and `filmcraft-cli`. Resolve an approved existing binary; missing software is a blocker, not installation permission. The following are source-backed command forms, not a run log. Replace `/absolute/work/...` with authorized run paths.

```sh
filmcraft-cli --version
filmcraft-cli --help
filmcraft-cli --project /absolute/work/sample.fcproj commands --json
filmcraft-cli --project /absolute/work/sample.fcproj describe file.exportMedia
filmcraft-cli --project /absolute/work/sample.fcproj inspect

# Persistent headless MCP over stdio:
filmcraft-cli mcp --project /absolute/work/sample.fcproj
# Or persistent bridge to an already authenticated desktop:
filmcraft-cli mcp --bridge 127.0.0.1:9876
```

Use one mode, not both as concurrent project writers. For ordinary live-desktop CLI calls, replace `--project ...` with `--bridge 127.0.0.1:9876`; bridge rejects `--project`/`--demo`. MCP accepts only `--bridge`, `--project`, `--demo`, `--data-dir`; it has no `--save` flag.

After the client's MCP initialization, these are actual JSON-RPC request envelopes:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"command_list","arguments":{"filter":"transcript","enabled_only":false}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"doc_inspect","arguments":{}}}
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"command_run","arguments":{"id":"transcript.inspect","params":{}}}}
```

- Discover with disabled commands visible; distinguish absent capability from selection/build/project preconditions. Obtain real media, clip, track and sequence IDs from inspection.
- `command_list` accepts `filter` (case-insensitive id/label substring), `enabled_only`. Its engine `params` entries are **documentation strings, not strict JSON Schemas**. MCP rejects unknown wrapper arguments, but passes arbitrary `command_run.params` through; that validation does not prove engine arguments correct.
- `command_run` takes `{"id":"command.id","params":{...}}`. `command_batch` takes `{"steps":[{"id":"command.id","params":{...}}],"stop_on_error":true}`. Batches are ordered, **not transactional**: failures leave earlier successful steps applied, with separate undo steps; there is no partial-batch rollback.
- `doc_inspect` combines project and active sequence inspection. `render_preview`/`render_frame` accept `seconds` and `max_side`; actually inspect the returned image. Bridge UI tools require the desktop. Resources `filmcraft://commands` and `filmcraft://document` expose equivalent discovery.
- Explicit documented targets can satisfy some selection-based command preconditions even when catalog enablement is false; verify command-specific requirements rather than inventing targets.

Sources: [agent/CLI/MCP guide][agents], [MCP implementation][mcp], [command registry][commands].

## 2. Security, persistence and checkpoints

**Desktop control is authenticated loopback newline JSON, not HTTP or MCP.** `filmcraft --control 9876` binds `127.0.0.1`; desktop and bridge must inherit the same fresh private 64-hex-character `FILMCRAFT_CONTROL_TOKEN`. Invalid/missing desktop token leaves the listener closed. Every raw request needs the token. Keep secrets out of argv, committed configuration, shared files and evidence logs. Loopback is not account isolation.

Raw request shape (placeholder only; redact real tokens):

```json
{"id":1,"token":"<private inherited token>","method":"engine.execute","params":{"command":"file.saveAs","params":{"path":"/absolute/work/rev-001.fcproj"}}}
```

Replies are `{"id":1,"ok":true,"result":...}` or `{"id":1,"ok":false,"error":"..."}`. Raw discovery is `engine.commands`. Bridge retries some transport failures; after an ambiguous mutation inspect state before replaying it, because a lost reply can hide a successful edit.

**No filesystem sandbox:** MCP has the OS user's read/write authority. `--data-dir` selects preset storage, not allowed roots. Constrain paths through the workflow and obtain authorization for external writes/destructive operations.

| Session | Persistence rule |
| --- | --- |
| Headless MCP | One in-memory session for process lifetime. Explicitly save before shutdown; do not assume desktop autosave/recovery. |
| Desktop bridge | Uses the desktop's current session. Explicit checkpointing still required. |
| Ordinary CLI `exec`/`run`/`import` | Fresh session per invocation. Use `--save` back to input or `--save-as` to a new path, or explicit `file.save*`. `run` shares state across its JSONL lines only. |

Executable one-shot forms:

```sh
filmcraft-cli --project /absolute/work/sample.fcproj exec file.saveAs '{"path":"/absolute/work/rev-001.fcproj"}'
filmcraft-cli --project /absolute/work/rev-001.fcproj --save-as /absolute/work/rev-002.fcproj run /absolute/work/approved-steps.jsonl
filmcraft-cli --project /absolute/work/rev-002.fcproj inspect
```

JSONL lines use `{"id":"...","params":{...}}`; `run` stops on failure unless `--keep-going`. Failure can exit before flag-based saving; `--keep-going` can save partial successes and still exit 1. Exit status alone does not establish unchanged files.

In persistent MCP, checkpoint explicitly:

```json
{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"command_run","arguments":{"id":"file.saveAs","params":{"path":"/absolute/work/rev-003.fcproj"}}}}
```

- `file.saveAs {"path":...}` saves and adopts a new path. `file.save {"path":...}` saves/adopts explicit or existing path. Both return `{path,bytes,ms,backup}`.
- `file.saveCopy {"path":...}` writes a copy without adopting its path or clearing unsaved state.
- `file.open {"path":...}` returns `{path,schemaVersion,migrated,missingMedia}` and replaces session/history state. Prefer fresh-session reopen checks after saving; compare actual sequences/tracks/cuts/transcripts/captions and media resolution, not merely file existence.
- `.fcproj` is versioned JSON referencing media paths, not embedded media. Migration can occur in memory; saving can change schema. Preserve originals and inspect compatibility/missing-media results.
- CLI flag-based in-place locking is best effort; desktop/MCP and explicit save commands do not provide equivalent locking. Atomic saving prevents torn files, not competing-writer overwrites. Maintain one producer writer.

Sources: [control/security protocol][control], [CLI behavior][cli], [project format][projects], [save handlers][commands].

## 3. Reuse transcripts with exact media time

Prefer existing source-matched external transcripts over new recognition. Verify source hash, speech stream, excerpt/derivative offsets, language, timing granularity and bounds first. `transcript.set` replaces the underlying media transcript; it is a mutation, not a merge. `item` is a numeric project media/subclip ID, not a placement/sequence ID; subclip storage resolves to parent media.

Source-valid MCP example only: **replace item `42` with an inspected ID and replace the illustrative word with real evidence**. This encodes “Hello” at media seconds `[1,1.5)`, not an observed recording:

```json
{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"command_run","arguments":{"id":"transcript.set","params":{"item":42,"transcript":{"language":"en","source":"manual","speakers":[{"name":"Presenter"}],"words":[{"text":"Hello","start":254016000000,"end":381024000000,"speaker":0,"confidence":1.0}]}}}}}
```

Timing contract:

- `start`/`end` are bare JSON **signed int64 ticks**, media-relative, half-open `[start,end)`. **254016000000 ticks/second.** Inspection/search instead return derived **sequence-time ticks**.
- Convert a rational source time `n/d` seconds as `n × 254016000000 / d` using exact integer/rational arithmetic; document rounding when division is not exact. Milliseconds multiply by `254016000`; 48 kHz sample indices by `5292000`; 16 kHz indices by `15876000`. Add excerpt offsets in media time before import.
- Frame duration uses actual rate `num/den`: `254016000000 × den / num`; 30000/1001 is not 30. Preserve PTS/VFR and derivative mappings rather than guessing frame arithmetic.
- Native floating conversion rounds seconds × tick rate. Preserve exact integer serialization: JavaScript `Number` loses some integers above `2^53−1` (about 9.85 hours here). Check int64 and media bounds.
- Supply only genuine word timings. Segment-only transcripts remain segment-only evidence until an approved verified alignment route supplies words; evenly distributing segment text invents timing. Unknown units block import.
- `set` normalizes sorting, whitespace, overlaps, confidence and speaker labels; inspect serialized results. Its checks do not enforce all source bounds. Optional speaker is zero-based; confidence defaults to 1.

### Derived transcript limitations

Sequence words map source-in, placement start and positive speed; disabled clip items, reverse/frame-hold/nonpositive-speed placements are skipped. Audio tracks are read top-first; upper transcribed coverage can suppress different lower dialogue by midpoint. The mapper does **not** consult track mute/solo/enabled flags, so text is not proof of the monitored mix. Parent transcript lookup through subclip placements is also limited. Inspect against the chosen actual speech stream and listen.

Native word confidence **1.0 is a default, not calibrated recognition probability**. Whisper/Candle CPU inference is optional and build-dependent; word alignment is roughly 20 ms and can remain late inside continuous speech. Exact ticks do not establish accurate word boundaries. Speaker clustering is not verified speaker identity.

If existing evidence cannot be reused, discover `transcript.models {}` for backend availability, model size/license/source and installation status. Native IDs include `whisper-tiny`, `whisper-base`, `whisper-small`. Build support, downloader support and installed weights are separate checks. **Ask before model download/build/install or writes outside the authorized workspace.** Only after consent, installed-command verification and checkpointing use `transcript.downloadModel {"model":"whisper-base"}` and/or `transcript.generate {"items":[42],"model":"whisper-base","language":"en","diarize":true,"maxSpeakers":2}` with real IDs. Generation reads full media audio, downmixed to mono 16 kHz, runs synchronously and overwrites existing transcripts; it does not automatically download missing models.

Sources: [transcript guide][transcripts], [handlers][transcript-engine], [data normalization][transcript-model], [sequence mapping/cuts][transcript-edit], [actual tick implementation][ticks], [native recognizer][whisper].

## 4. Review-first pacing; bulk cleanup is destructive

**Create a proposal ledger before editing.** Record candidate word/gap, surrounding speech, media/sequence ticks, revision/map, reason, protected holds and keep/remove decision. Use `transcript.inspect {}` and `transcript.search {"query":"you know"}` as queries; search's final word may match a prefix, so verify exact text. Gaps between transcript words are not proven silence.

| Command and parameter object | Effect / scope |
| --- | --- |
| `transcript.select {"from":3,"to":4}` | Mutates In/Out and playhead; inclusive word indices, outward frame snapping. Not read-only. |
| `transcript.extract {"from":3,"to":4}` | Immediate ripple cut on unlocked A/V tracks **targeted OR sync-locked**; unlocked sync-locked captions follow. |
| `transcript.lift {"from":3,"to":4}` | Immediate gap-preserving edit on **targeted AND unlocked** A/V; this lift does not edit caption tracks. |
| `transcript.removeFillers {"fillers":["um","uh","you know"]}` | Immediate bulk ripple deletion on **ALL unlocked A/V**, regardless of targeting or sync lock. Explicit list replaces defaults. |
| `transcript.removePauses {"minSeconds":1.0,"keepSeconds":0.15}` | Same all-unlocked A/V scope; consecutive-word gaps at least the threshold, keeping air at **each** edge. Not leading/trailing silence detection. |

Bulk commands have **no dry-run/preview/per-hit approval flag**; ignored `dryRun`/`preview` keys provide no protection. There is **no registered `transcript.findFillers` or `transcript.findPauses` API**. Inspect/query and construct proposals separately.

Turning targeting or sync lock off does **not** protect unlocked B-roll/music/screen tracks from bulk cleanup. Locked tracks can remain behind and lose sync; unlocked sync-locked captions follow ripple edits. Audit every track. Supported settings include `timeline.setTrack {"track":"V1","locked":true}`, `timeline.setTrack {"track":"A1","syncLock":true}` and `timeline.setTargeting {"track":"A1","targeted":true}`; setting one does not clear others.

Producer procedure:

1. Save a recoverable checkpoint; inspect all track policies and the exact candidate context.
2. Watch/listen before approving removal. Protect semantic fillers (“hmm” as an answer, qualifications), demonstrations, screen-reading/thinking holds and evidence. Transcript gaps can contain omitted speech or useful activity.
3. Apply one accepted word cut with current indices and checked scope. Word extract snaps outward, unlike nearest/constrained bulk filler boundaries. For pauses, review a precise timeline interval and discover ordinary sequence edit parameters; word-index extract does not mean “cut silence.”
4. **Reinspect after every edit**, including indices, times, map, tracks, captions and joins; refresh the ledger against the new revision. Check speech onsets/tails and A/V sync. Text-driven extraction need not ripple sequence markers identically to ordinary `sequence.extract`.
5. Use bulk cleanup only when the entire resulting cut set and every affected track are explicitly approved and sample-tested. Returned `removed` is a pre-merge range count, not necessarily actual cut count; touching/overlapping ranges merge. Keep proposed, applied and measured counts distinct.

Sources: [immediate engine handlers][transcript-engine], [range algorithms and all-track deletion][transcript-edit], [extract/lift track policy][edit], [track/sequence commands][commands].

## 5. Captions after structural approval

`transcript.createCaptions {"maxChars":42,"lines":2,"minSeconds":1.0,"maxSeconds":7.0,"gapFrames":0,"name":"Transcript","format":"Subtitle"}` creates a **new caption track** from current sequence words and returns `{track,captions}`. Repeating it duplicates tracks; it neither updates an existing track nor exports a subtitle file.

Inspect `captions.list`, then discover/use `captions.setText`, `captions.setTimes`, `captions.setStyle` for corrections. Export an explicit inspected track with `captions.export {"path":"/absolute/work/final.srt","track":"C1","format":"srt"}` (or WebVTT). For media export discover `burnCaptions`/`captionSidecar`; choose burn-in versus sidecar deliberately. Inspect returned warnings/paths, actual text/timing and rendered legibility/occlusion; layout heuristics are not reading-quality approval. Nested captions can already be part of the nested picture.

Sources: [caption commands/export][captions], [caption generation handler][transcript-engine].

## 6. Resolve, export, wait, inspect

Discover installed `export.presets.list`, `export.resolve`, `file.exportMedia`, `media.status`/`media.findMissing`, `jobs.list` and `jobs.cancel`. Resolve the intended inspected sequence ID, explicit range, dimensions, rate, codec, audio and caption policy before encoding.

Illustrative envelopes use sequence `7`; replace it with the inspected target and verify/narrow settings for the actual deliverable:

```json
{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"command_run","arguments":{"id":"export.resolve","params":{"sequence":7,"path":"/absolute/work/review.mp4","format":"h264","range":"entire","audio":true,"burnCaptions":false}}}}
{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"command_run","arguments":{"id":"file.exportMedia","params":{"sequence":7,"path":"/absolute/work/review.mp4","format":"h264","range":"entire","audio":true,"burnCaptions":false,"wait":true}}}}
```

- `export.resolve` does not encode: inspect returned `settings`, `range` (`start,duration,seconds`), `frames`, `warnings`, `output`, `summary`, `source` and selected preset.
- Set `range:"entire"` for the whole sequence; stale In/Out can silently produce a one-frame export with only a warning. Custom ranges use `startSeconds`/`endSeconds`.
- Engine/MCP export defaults to `wait:false`, returning job/path rather than completion. Prefer direct `command_run` with `wait:true` for completion/progress/cancellation behavior; do not assume batch has the same progress handling.
- If asynchronous in a **persistent** session, poll the matching ID in `jobs.list`, not `export.queue.list`. Check `finished`, `result`, `progress`, `etaSeconds`, `offlineMedia`; `jobs.cancel {"job":...}` cancels the actual ID. Keep the owning process alive.
- **Never request background export in a short-lived headless CLI process.** CLI `export` waits; local `exec`/`run` inject wait for `file.exportMedia` unless explicitly false.

Executable CLI equivalent for an already verified active sequence:

```sh
filmcraft-cli --project /absolute/work/rev-003.fcproj export /absolute/work/review.mp4 --range entire
```

Capture raw responses, matching terminal job result, warnings, `offlineMedia` and exact returned paths. Offline media can render placeholders **and still report success** over engine/MCP; reject required offline inputs. CLI `export` writes then exits 1 for offline media unless `--allow-offline`; generic `exec` is not that offline gate.

Inspect `result.encoder` and warnings: hardware `"auto"` may fall back to software. Extensions may change; image sequences return first-still `path`, `lastPath`, `basePath`, not necessarily the requested filename. Use returned artifacts, verify existence/decode and expected encoded duration/frame count, then inspect rendered boundaries/treatments and listen. Save/reopen, export success and visual/audio approval are separate checks.

Sources: [export lifecycle/progress/offline behavior][agents], [registered export parameters][commands], [export implementation][exports], [CLI waiting/offline policy][cli].

## 7. Discover before claiming timeline, visual or audio capability

For media placement, streams, cuts/reorders, zooms/keyframes, highlights, camera color, audio DSP and interchange, read the disclosed [timeline and treatment API reference](timeline-api.md). Its source-inspected payloads still require installed discovery and disposable verification; they are not a locally tested complete editing API. Inspect IDs, units, target/lock behavior, enablement and undo/save implications. Do not infer command syntax from UI labels or another Craft app.

On the disposable sample, verify two known-boundary cuts, ordered source mapping, requested visual/audio treatments, native save/reopen/relink and a matching completed export with frame/listening evidence under the [native acceptance gate](handoff.md#capability-gate-disposable-sample). Unverified requested work remains blocked; optional EffectCraft/SoundCraft routes require their own evidence and authorization, not silent fallback to pipeline assembly/rendering.

[agents]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/agents.md
[control]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/control-protocol.md
[mcp]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/automation/src/server.rs
[cli]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/apps/filmcraft-cli/src/main.rs
[commands]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/commands.rs
[projects]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/project-files.md
[exports]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/export_tools.rs
[transcripts]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/transcripts.md
[transcript-engine]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/transcript.rs
[transcript-model]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/project/src/transcript.rs
[transcript-edit]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/edit/src/transcript.rs
[edit]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/edit/src/lib.rs
[ticks]: https://github.com/storytold/craft-libs/blob/3b8e426a260695af840a2cd79a064d40778f939e/crates/time/src/lib.rs
[whisper]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/speech/src/whisper.rs
[captions]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/captions.md
