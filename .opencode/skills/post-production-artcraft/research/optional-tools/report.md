# Optional ArtCraft branches — Scout D

## Evidence and scope

Research only; no application, plugin, renderer or test was run. “Supported” below means **published documentation or inspected source**, not runtime-verified behavior. No installation, build, configuration change, model/executable download, media edit, commit or delegation occurred.

Base requested: Lesson Studio `9e53d1b`. Owned directory: `.opencode/skills/post-production-artcraft/research/optional-tools/` only. Read root `AGENTS.md`, mission and post-production experiment; this research does not change the experiment or make these apps requirements.

Retrieved 2026-11-19 UTC (machine timestamp; task context calls this 2026-11-18). Resolved HEAD once, then downloaded from immutable SHAs:

| Repository | Pinned SHA |
|---|---|
| https://github.com/storytold/effectcraft | `665bfac0b33904b1dcda6de889f43f43a94ad3f8` |
| https://github.com/storytold/soundcraft | `a02d892f831f0a4e1220e0357c7b941030b9cd6f` |
| https://github.com/storytold/filmcraft (narrow interoperability/zoom corroboration) | `f67d38b35cc5af6853ef5a6921ccba014512694b` |

`sources.tsv` records each downloaded file, original URL, retrieval date and SHA-256. Files retain upstream paths beneath each repository directory; `tree.json` records the pinned path inventory. Upstream “tested”, fidelity percentages and issue status remain **upstream claims**. Their parity documents contain stale/conflicting entries; source contracts are stronger evidence for the particular operations inspected.

## Recommendation: keep FilmCraft as the default

Do not create an EffectCraft or SoundCraft session just because those siblings exist.

1. **FilmCraft first:** ordinary trims, motion/scale keyframes, captions, titles, clip gain/fades and simple audio processing stay in the picture editor.
2. **EffectCraft only for a specific missing compositing result:** author an isolated title/overlay/shot, save its project, render a bounded intermediate, import it into FilmCraft and inspect alpha, timing and readability. Prefer this over converting the whole timeline.
3. **SoundCraft only for a specific missing audio result:** after picture lock, process a full-length aligned PCM stem, save the session, bounce an explicitly bounded WAV and replace/mute the original audio in FilmCraft. Preserve the original picture duration and leading silence; do not duplicate the processed and original voice.
4. If the branch adds more review and correction than benefit, skip it. Approve any later install/configuration/plugin work separately.

## EffectCraft: automation, persistence and handoff

- **Automation:** `effectcraft/docs/agents.md:11–15,104–155` documents CLI, headless MCP and live-app control. Headless `effectcraft-cli mcp`; bridge `mcp --bridge 9877` to `effectcraft --control 9877`. Discover commands/schema before mutation. `batch` is atomic with one undo step; `command_batch` is ordered, non-atomic and has per-edit undo. Inspect individual render/item failures, not just transport success (`docs/mcp.md:23–47`).
- **Save/reopen:** `save_project {path}` / `open_project {path}` and versioned `.ecproj` JSON. Headless work is otherwise memory-only; optional `mcp --autosave` checkpoints on dirty tool calls, but warning replies can mean the checkpoint failed. Explicitly save before replacing a dirty project. `docs/agents.md:75–100`; `docs/file-format-parity.md:35` warns about absolute footage paths. The latter's “no relinking” statement is stale relative to the missing-media commands in `docs/agents.md:192–196`; do not promise portable reopen without a media check.
- **Render/export:** `renderQueue.add` then `renderQueue.render {wait:true}`; PNG/contact sheets for inspection. Alpha-capable ProRes 4444 or PNG sequence is a plausible overlay interchange, not a verified FilmCraft round trip. Explicit format, size, frame rate, duration and alpha interpretation are required. H.264 is not the transparent-overlay route. See `docs/agents.md:353–381`, `docs/user/guides/render-a-video.md`, FilmCraft `docs/file-format-parity.md`.
- **Actually implemented file interchange:** `crates/interchange/src/lib.rs:1–30` and `crates/engine/src/cmd/timeline.rs:290–307` expose `file.importTimeline` / `file.exportTimeline` with FCP7 XML, FCPXML, OTIO, EDL, AAF, OMF. Compositions/layers are mapped to timeline tracks; motion/opacity and timing have explicit mappings. Text, shapes, effects, masks and 3D cannot simply become native NLE effects: export omits them or pre-renders them (`prerender: none|unsupported|all`, `precomps: nest|prerender`). Read warnings/errors and validate converted sequences independently.
- **Not established:** seamless live “Dynamic Link”, shared native project editing, or editable lossless cross-app compositing. Shared crates and MCP conventions are **not** a live link. `crates/engine/src/cmd/link.rs` is a property pick-whip, not an app link.
- **Templates:** upstream `docs/file-format-parity.md:28` explicitly says FilmCraft rejects EffectCraft `.fcgt` export (#611). Do not recommend that as a ready-made handoff just because both products advertise graphics templates.
- **Timing risk:** EffectCraft keyframe writes default to **layer seconds**, queries/renders use **composition seconds**. Pass `timeBase:"comp"` where appropriate, inspect returned timing/warnings, and account for layer offsets/stretch/reverse. Writes snap to composition frames. `docs/agents.md:134–161,198–209`.
- **Audio in a compositing branch:** `crates/export/tests/it/audio_sample_positions.rs:48–55` explicitly documents floor-to-sample conversion of the selected export span and tests impulse preservation through tick conversions. That is a narrow upstream test, not proof of sample-identical timing across every codec, a complete composition mix or a FilmCraft round trip. Prefer a silent overlay plus unchanged FilmCraft program audio; if replacing a whole shot with audio, check sample count, head/tail transients, sync and codec delay independently.
- **Safety:** output guards protect source footage/proxies/project from renders, not every unrelated pre-existing file. Use unique output paths. Root-confined MCP blocks scripts and bridge UI tools; without root flags that confinement is absent (`docs/mcp.md:6–21`). Bridge mutation transport failures may have unknown outcomes: inspect before retrying (`docs/agents.md:50–53`).

## Manual zoom is not automatic click zoom

FilmCraft source `filmcraft/crates/engine/src/commands.rs:3798–3893,3970–4020` exposes effect-parameter animation and keyframe operations: an agent or human can choose a focus point/time and keyframe Motion position/scale. EffectCraft also exposes position/scale keys (`docs/agents.md:116–117,184`). This supports **deliberately authored zooms**, not automatic discovery of recorded mouse clicks.

No automatic click-event extraction, click metadata importer, or click-driven zoom planner was established in the inspected docs/command catalog. UI `ui_click` and `ui.zoom`/viewer zoom refer to controlling the editor, not detecting clicks in a recording or generating camera moves. Motion tracking follows image features, not semantic click events.

Minimal branch: identify a small number of editorially useful moments, author zoom-in/hold/zoom-out motion in FilmCraft, verify text remains legible and focus does not hide relevant state. Do not claim automatic click zoom or introduce EffectCraft merely for scale animation. No replacement recorders were researched.

## SoundCraft: automation, save/reopen and exchange

- **Automation:** `soundcraft/docs/cli.md:11–34` documents `run`, command scripts, `describe`, audio `convert`, MCP and live-app `app` calls. `docs/control-protocol.md:10–14` distinguishes headless MCP from `soundcraft-cli mcp --connect <port>`. Headless commands do not operate on an existing desktop session unless bridged.
- **Persistence:** native `.scraft` JSON with sibling `Audio Files/` and embedded plugin state (`docs/file-format-parity.md:26`). `open_session` reports missing media; inspect `session.inspect {detail:"full"}` and source `loaded` flags after reopen (`docs/mcp.md:103`, `docs/control-protocol.md:45`). Save the complete bundle, not JSON alone. `crates/engine/src/cmd/plugin_state.rs:1–3,10–21` shows explicit plugin-state capture/storage; do not assume headless edits can capture a separately running GUI plugin.
- **Bounce:** `file.bounce_mix` / `file.bounce_stems` support WAV/AIFF/FLAC, explicit start/end, bit depth and dither; source bus and normalize options apply to the mix (`crates/engine/src/cmd/file.rs:92–111,314–337`). Prefer PCM WAV for picture handoff; SoundCraft cannot export video and currently cannot write MP3/AAC/Opus (`docs/file-format-parity.md:36–45,61–70`).
- **No native FilmCraft session exchange established:** `.scraft` is not a FilmCraft project. SoundCraft explicitly lacks **AAF and OMF import/export**, even though FilmCraft writes them (`docs/file-format-parity.md:20–27`, `docs/gaps.md:G-03`). No live SoundCraft↔FilmCraft link was established. Use rendered audio media, not a promised timeline round trip.
- **Alignment metadata:** WAV bounces write BWF `bext` TimeReference = session timecode start + bounce start (`crates/engine/src/io.rs:378–394`, `docs/file-format-parity.md:36`). FilmCraft advertises BWF reading, but automatic placement of this particular SoundCraft bounce was not exercised. Carry explicit start offset/sample rate/sample count in the handoff and verify placement manually.
- **Safety:** CLI prevents outputs aliasing explicit inputs without `--in-place`, but replaces unrelated existing outputs without asking (`docs/cli.md:63–75`). MCP has separate read/write roots and protects nested media paths; bridge/roots combinations differ from EffectCraft. Preserve raw sources and choose fresh output locations.

## Audio timing, tails and plugin risks

1. **Range is a contract.** `soundcraft/crates/mix/src/offline.rs:56–102` renders exactly the requested range length after skipping calculated PDC latency. This is not an automatic audible-tail extender. Set the end long enough to include wanted decay; if picture duration must stay fixed, fade the ending deliberately rather than silently appending time.
2. **Nonzero-start state risk (source inference):** `RangeRender` constructs a fresh engine at the requested start, not a full preceding-program preroll. A short bounce beginning halfway through a reverb/delay or instrument can omit history. Prefer full-program bounce from timeline zero or a documented preroll/trim strategy; compare the seam by listening.
3. **Different rendering paths differ:** clip-effects consolidation has a 10-second tail cap and a -180 dBFS tail termination floor (`offline.rs:135–147`); do not generalize this into unlimited tails on mix bounce or hosted effects.
4. **PDC is implemented, not a blanket guarantee.** Offline source explicitly skips main/bus compensation; upstream plugin parity still lists changing aux latency as partial (#103), while `gaps.md` records some later latency fixes. Test impulse/transient alignment for the actual chain in a later approved trial; no such test was run here. Send and plugin automation are still sampled once per block according to `docs/gaps.md:G-04`.
5. **Plugin capability ≠ interchange:** CLAP/VST3/AU state is SoundCraft session state, not a transferable FilmCraft insert chain. In-process hosting means a third-party plugin is not crash-isolated. AU is macOS-only; editor availability and signed-macOS VST3 restrictions are platform-specific. Hosted plugins are not currently AudioSuite processors; no sidechain input (`docs/plugin-parity.md:27–55`). Prefer built-in offline processing unless a specific unmet need justifies third-party plugin approval.
6. **Normalization is peak, not delivery loudness.** Bounce normalize renders twice and targets -0.1 dBFS peak (`io.rs:357–360,449–454`); the returned LUFS/true peak are measurements, not proof of a desired loudness target or absence of clipping downstream.
7. **Stems include processing context.** `io.rs:588–615` solos each audio/instrument track, including sends/auxes. Shared or nonlinear processing need not sum identically to the full mix. Prefer a single approved voice/mix replacement when that is all the picture edit needs.

## Strip Silence: precise contract, not transcript editing

Sources: `soundcraft/crates/engine/src/cmd/strip_silence.rs:9–48`, `cmd/edit.rs:120–126,818–836`, `io/strip.rs:22–40,93–164`.

- Preview `edit.strip_silence_preview` is read-only and returns track ranges using the same settings as apply.
- Defaults: threshold **-48 dB**, minimum length **50 ms**, pad before **5 ms**, pad after **20 ms**. Threshold clamps to [-96,0]; millisecond settings clamp to [0,10000]. Times/ranges must follow the command/time schema, not guessed units.
- Modes: `strip` keeps nonsilent regions; `extract` keeps silent regions; `separate` splits without removing anything. The implementation splits at detected boundaries and removes pieces, **without ripple-closing the gaps**.
- This is audio-level segmentation, not ASR, filler-word detection, retake reasoning or an approved pacing decision. Quiet consonants/breaths and meaningful pauses need listening; preview and padding do not guarantee natural edits.
- For synchronized picture, preserve positions. If the actual goal is removing pauses from the finished video, make the approved synchronized cuts in FilmCraft (with picture/audio continuity review), not an independently shortened DAW voice track.

## Later trial acceptance gate (not performed)

Save → close/reopen → confirm no missing media/plugin warnings → render/bounce to a fresh path → independently inspect actual frames/listen → reimport in FilmCraft → verify first/last sample/frame, duration, offset, sync, color/alpha, tails and final mix → human approval. Record elapsed and hands-on correction time. Until this is observed, describe these as candidate optional paths, not tested integrations.
