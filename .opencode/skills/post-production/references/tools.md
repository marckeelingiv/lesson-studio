# Tool capabilities and limits

Read `video_pipeline/README.md`, current command help and relevant source. Reuse tools instead of installing another framework from a research checklist.

`backend=pipeline` is the default. The Existing pipeline restrictions below are pipeline-specific. For `backend=artcraft`, read the separately supplied native handoff/API references and verified capability evidence; missing support is a blocker, not an automatic pipeline fallback. Authorized `ffprobe` probing or FFmpeg measurement does not authorize switching editing, assembly or rendering backends. Analysis helpers and backend fallbacks require explicit approval.

## Existing pipeline

- `ingest` probes/extracts analysis audio, not automatic sync, OBS remux or proxies. Inventory original streams first: speech may be on a non-default track. The current extraction uses FFmpeg automatic audio selection while assembly uses `[0:a]`; neither CLI exposes track selection. For multitrack inputs, create an explicitly mapped editing derivative containing the intended video and exactly one chosen speech/mix track. Bind both transcription and EDL assembly to that derivative, documenting its original-source identity/time mapping. Do not assume extraction and assembly select the same stream.
- `transcribe` supplies word timestamps and silence/filler/retake candidates, not applied editorial decisions.
- `plan --model opencode` uses transcript evidence, not frames. Specialist-authored EDLs can avoid another model call. Heuristic cuts still need audiovisual safeguards.
- `assemble` handles one source's kept segments, optional synchronized camera, micro-fades and normalization. Use explicit `--out-dir` and `--transcript` to preserve shared source analysis and prior revisions. Always assemble from a stage-local EDL copy: a camera override can rewrite the input EDL even when `--out-dir` points elsewhere.
- `export-nle` produces FCPXML for a Resolve handoff. Actual import/reopen needs testing; it does not establish Kdenlive/FilmCraft compatibility.
- `render` uses Remotion's supported captions/graphic cues. Inspect `schema.py` and remapping code for source vs edited units.
- Existing EDLs do not describe arbitrary multitrack edits, independent J/L cuts, B-roll, camera color tracks or vertical reframing. Use explicit reviewable FFmpeg compositions or a verified editor; unsupported fields are not implementations.
- Remotion temporarily stages media in `video_pipeline/renderer/public/` and deletes it afterward. Before use, obtain producer approval for this out-of-workspace staging, ensure destinations do not already exist and serialize renders. For workspace-only generation, use a workspace-local route or report the bridge blocked. Deliverables stay in the run.

## Processing choices

- Remux/proxy only when needed. Avoid unnecessary lossy generations; preserve original references and sync offsets.
- Diagnose before denoise/EQ/compression. Early repair may precede transcription; final normalization follows the composed mix.
- Choose loudness targets (e.g. −14 LUFS / maximum −1 dBTP) as delivery presets, not universal platform mandates. Measure encoded results and codec overshoot; existing assembly targets may differ.
- Music/SFX require licenses and a purpose. Duck to intelligible balance, not a universal offset. Screen captures rarely need creative grading.
- Dense UI may need an enlarged detail-panel layout, not an automatic 9:16 center crop.
- Verify current platform constraints from official sources before export. Codec/bitrate/aspect ratio/clip length defaults are choices, not universal acceptance limits.

## Optional FilmCraft evaluation

Checked 2026-11-18: the official [app page](https://getartcraft.com/apps/filmcraft) marks FilmCraft “in development,” links [storytold/filmcraft](https://github.com/storytold/filmcraft) and lists Linux builds. The [catalog](https://getartcraft.com/apps) advertises CLI/JSON-control/MCP automation. These are published claims, not local integration tests.

Keep FilmCraft optional. With install authorization, inspect the actual version/help/API; test a disposable project: import, make two frame-exact cuts, save/reopen, export, inspect sync/frames and measure audio. Test intended interchange separately. Record results before production adoption; never infer MCP schemas or readiness from the talk summary.
