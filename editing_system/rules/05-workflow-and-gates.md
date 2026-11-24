# Rule 05: Workflow Stages, Human Gates, and Revision Protocol (Technical Engine Room)

All post-production runs follow 5 sequential stages and 3 mandatory human approval gates. Never skip gates or combine visual build with audio layering.

## 1. Stage Map & Human Gates

- **Stage 0 — Creative Brief & Ingest**:
  - Load `creative-brief.yaml` (or instantiate from `editing_system/briefs/creative-brief.template.yaml`).
  - Verify source media hashes, streams, VFR status, and selected speech track.
  - Run `faster-whisper` transcription and initialize source `.otio` timeline.
- **Stage 1 — Scientific Sift** *(bypassable when entering with a pre-cut clean A-Roll)*:
  - Execute `01-sifting.md` rules to emit `cut_audit.json`, `rough_cut.otio`, and `rough_cut.mp4`.
  - **Gate 1 — Rough Cut Approval**: Human inspects `cut_audit.json` (duration before/after, removed seconds, protected holds, and uncertain candidates) and watches/listens to `rough_cut.mp4`.
- **Stage 2 — Storyboard & Contact Sheet**:
  - Read Taste Profile (`editing_system/memory/taste_profile.md`), Creative Brief, and `editing_system/assets/catalog.json`.
  - Emit `storyboard.json` following `02-storyboard-and-layouts.md` and render static keyframe PNGs + Contact Sheet grid.
  - **Gate 2 — Contact Sheet Approval**: Human reviews layout, typography, colors, and Safe Zones before any full video render.
- **Stage 3 — Visual Build, QC & Revision Passes**:
  - Render visual-only composition (no music or SFX).
  - Pass all 8 automated QC gates (`04-quality-checks.md`) before delivering V1 to human review.
  - Iterate through focused Revision Passes (`editing_system/prompts/03-revision-pass.md` or HyperFrames Studio) until human confirms **Picture Lock**.
- **Stage 4 — Audio Layer, Final QC & Delivery**:
  - Layer ducked music and rule-governed SFX (`03-audio-and-sfx.md`) locked to Picture Lock timings.
  - Run Final QC (8 gates + 6 delivery checks) and export `final.mp4`, `.otio`, `.fcpxml`/`.kdenlive`, and `.srt`.
  - **Gate 3 — Final Delivery & Taste Log**: Human performs end-to-end watch/listen approval and logs tagged feedback to `editing_system/memory/review_log.jsonl`.

## 2. Revision Pass Protocol

- Send **1–3 specific, timestamped notes** per Revision Pass rather than massive kitchen-sink prompts.
- Re-run automated QC after every pass before presenting the new revision.
- Preserve prior revision artifacts inside the run workspace; never overwrite approved checkpoints silently.

## 3. Stale Dependency Invalidation

- Any upstream timeline cut (`.otio`), transcript correction, or Design Token update invalidates downstream Storyboard timings, Contact Sheets, rendered plates, audio mixes, `.srt` captions, and QC reports (`stale_check`).
- Mark stale artifacts in `run.json` and regenerate only affected downstream stages while reusing verified source transcripts.

## 4. Source Preservation & Publication Boundary

- Never modify or overwrite original raw recordings.
- Keep all generated intermediates inside `video_pipeline/workspace/<source-stem>/`.
- Technical QC pass and export readiness do not authorize publishing or external uploads; release requires explicit Gate 3 approval.
