# Unified Video Editing System Implementation Plan

This plan defines the architecture, subsystems, directory structure, and phased roadmap combining the hybrid video-as-code workflow ([ai_video_editing_playbook.html](../research/ai_video_editing_playbook.html)) and the Two Engine Rooms methodology ([Video_Editor_Notes.md](../research/Video_Editor_Notes.md)), aligned with [LESSON_FRAMEWORK_MISSION.md](../../LESSON_FRAMEWORK_MISSION.md) and [CONTENT_ASSETS.md](../../CONTENT_ASSETS.md).

All terms follow [GLOSSARY.md](../../GLOSSARY.md).

## 1. Architecture Overview

1. **Two Engine Rooms (`editing_system/`)**:
   - **Technical Engine Room (`editing_system/rules/`)**: Static, deterministic rules applied to every video (scientific sifting math, consonant tail preservation, safe zones, max-3 transition cap, SFX attachment rules, and 8 automated QC gates).
   - **Creative Engine Room (`editing_system/briefs/`, `editing_system/memory/`)**: Per-video Creative Brief (1–2 Good vs. Not Good references, intensity dials, starting visual anchors, emphasized moments) plus the compounding Taste Profile (`review_log.jsonl` + `taste_profile.md`).
2. **NLE-Native Timeline & Interchange (`video_pipeline/src/`)**:
   - Canonical `.otio` timeline via OpenTimelineIO (`opentimelineio==0.18.1`) + FFmpeg, supporting bidirectional round-tripping to `.fcpxml` (`otio-fcpx-xml-lite-adapter==0.2.3`) and `.kdenlive` (`otio-kdenlive-adapter==0.0.3`).
   - Supports both raw footage entering Stage 1 (Scientific Sift) and pre-cut A-Roll entering directly at Stage 2 (Storyboard), prioritizing separate screen + camera tracks and pure talking-head takes.
3. **Visual Composition & Bidirectional Editing (`video_pipeline/hyperframes/` + `editing_system/assets/`)**:
   - HyperFrames (`heygen-com/hyperframes`) renders HTML/CSS/GSAP compositions for the 5 Scene Layouts, Motion Plates, Hero Visual templates, fixed captions, and static Contact Sheet PNGs, while HyperFrames Studio provides bidirectional visual and code editing.
   - All reusable assets live in 7 typed classes under `editing_system/assets/` governed by `catalog.schema.json` and `catalog.json`.
   - Legacy Remotion (`video_pipeline/renderer/`) stays untouched until HyperFrames proves parity on one real recording (per [ADR-0001](../adr/0001-otio-and-hyperframes-over-remotion.md)).
4. **Target Format Horizon**:
   - v1 targets **16:9 long-form** engineering lessons exclusively; `catalog.schema.json` and layout metadata carry `aspect_ratios` (`["16:9"]`) so 9:16 short-form expands cleanly in a later phase.

## 2. Repository Directory Layout

```text
/
├── GLOSSARY.md                      # Canonical video editing vocabulary
├── docs/
│   ├── adr/                         # 0001-otio-and-hyperframes-over-remotion, 0002-tool-agnostic-two-engine-rooms
│   └── plans/
│       └── video-editing-system-plan.md
├── editing_system/                  # Tool-agnostic source of truth (referenced by AGENTS.md)
│   ├── rules/                       # Technical Engine Room static rules
│   ├── briefs/                      # Creative Brief template + presets (clean-editorial default)
│   ├── prompts/                     # Reusable prompts (script distill, storyboard, revision pass, reskin)
│   ├── memory/                      # review_log.jsonl + synthesized taste_profile.md
│   └── assets/                      # catalog.schema.json + catalog.json + 7 typed asset classes:
│       ├── tokens/
│       ├── layouts/
│       ├── frameworks/
│       ├── heroes/
│       ├── motion/
│       ├── graphics/
│       └── audio/
├── video_pipeline/
│   ├── src/                         # Python CLI: ingest, transcribe, sift, otio timeline, audio mix, qc
│   ├── hyperframes/                 # HyperFrames runtime, contact-sheet generator, shared HTML/CSS shell
│   ├── renderer/                    # Legacy Remotion renderer (retained until HyperFrames parity)
│   └── workspace/                   # Ignored per-take runs and renders
└── .opencode/                       # Thin harness adapters pointing to editing_system/ (Phase 4)
```

## 3. End-to-End 5-Stage Workflow & 3 Human Gates

1. **Stage 0 — Creative Brief & Ingest**:
   - Author `creative-brief.yaml` from `editing_system/briefs/creative-brief.template.yaml` (defaulting to `clean-editorial` preset). If starting from an overly long take, run `editing_system/prompts/01-script-distill.md` to tighten the script before re-filming.
   - Probe media (`ffprobe`), select the intended speech track, detect VFR, transcribe with `faster-whisper` (word-level timestamps), and initialize the baseline `.otio` timeline.
2. **Stage 1 — Scientific Sift** *(bypassable when entering with a pre-cut A-Roll)*:
   - Execute strict 4-step deterministic sifting: `sync -> dead space -> retakes/mistakes -> filler words` with demo visual-activity protection.
   - Emit `cut_audit.json`, `rough_cut.otio`, and `rough_cut.mp4`.
   - **Gate 1 (Rough Cut Approval):** Human inspects `cut_audit.json` (reviewing proposed `Reopens`, `Replacements`, `Rephrases`, `Exceptions`, and context-sensitive fillers) and watches/listens to `rough_cut.mp4`.
3. **Stage 2 — Storyboard & Contact Sheet**:
   - Map approved Rough Cut beats to Scene Layouts, Motion Plates, Hero Visual variations, and max 3 transitions (`storyboard.json`), requiring an explicit Reason, Purpose, and Intention per visual element.
   - Render static keyframe PNGs and a Contact Sheet grid via HyperFrames.
   - **Gate 2 (Contact Sheet Approval):** Human approves layout, typography, contrast, and framing before full video rendering.
4. **Stage 3 — Visual Build, Automated QC & Revision Passes**:
   - Render HyperFrames compositions and composite visuals without background music or SFX.
   - Run all 8 automated pre-human QC gates (`flash`, `blank_check`, `fit`, `margin_check`, `eyes_mouth_check`, `stale_check`, `hold_sentence`, `stability`); agent fixes failures before human review.
   - Execute focused Revision Passes (`03-revision-pass.md` or HyperFrames Studio visual edits) until **Picture Lock** is reached.
5. **Stage 4 — Audio Layer, Final QC & Delivery**:
   - After Picture Lock, layer local licensed music (ducked under dialogue) and rule-governed SFX timed to exact locked Motion Plate entrances, then normalize to `-14 LUFS / -1.0 dBTP`.
   - Run full Final QC (8 gates + decode, consonant tail audit, freeze check, caption sync, loudness verification, frame/box checks).
   - Export `final.mp4`, `.otio`, `.fcpxml` / `.kdenlive`, and `.srt`.
   - **Gate 3 (Final Delivery & Taste Log):** Human watches and listens end-to-end, approves delivery, and appends timestamped review notes to `review_log.jsonl`.

## 4. Seven Subsystem Specifications

### S1. Two Engine Rooms & Creative Brief (`editing_system/rules/`, `editing_system/briefs/`)
- Technical rules are non-negotiable defaults encoded in `editing_system/rules/01..05`.
- Creative Briefs cap external references at 1–2 videos explicitly labeled `good` vs. `not_good` across `B-Roll`, `Scene Layouts`, and `Sound Design`, declare a concrete starting visual anchor, list emphasized moments, and set `1..5` sliders for `Animation`, `Visuals`, and `Sound Design` (default **Clean Editorial**: `Animation: 2`, `Visuals: 2`, `Sound Design: 1`, `Max Transitions: 3`).

### S2. Scientific Sifting Engine (`video_pipeline/src/sift.py`)
- **Adaptive Room Tone**: Divide audio into 10ms RMS windows and compute the quietest 10% percentile as **Room Tone** per recording (never fixed global dB cutoffs).
- **Dead Space & Breathing Room**: Gaps > 2–3 frames below adaptive speech threshold are cut candidates, preserving 2–3 frames of natural breathing room.
- **Consonant Tail Protection**: Track trailing energy on `S`, `T`, `D`, `K`, `P` word endings down to `-50 dB`; place cut out-point after tail completion and in-point 1 frame before next word onset (+2–3 safety frames when uncertain). Snap all cuts to the source frame grid.
- **5 Retake Categories**: `Repeats` (last take wins, high-confidence auto-cut), `Reopens`, `Replacements`, `Rephrases`, and `Exceptions` (callbacks and intentional rhythm beats are preserved).
- **25-Word Context-Aware Filler List**: Distinguish pure hesitation sounds (`um`, `uh`, etc.) from context-sensitive verbal fillers (`like`, `so`, `actually`, etc.); cut lexical fillers only when sentence grammar and meaning remain intact. Audit transcripts against raw waveform spikes for stutters transcription misses.
- **Demo Protection**: Protect gaps containing screen motion, cursor activity, or explicit reading holds; emit every decision with confidence and neighbor context in `cut_audit.json`.

### S3. OTIO Timeline & NLE Interchange (`video_pipeline/src/timeline_otio.py`)
- Represent video, camera PiP, Motion Plates, music, SFX, and markers as standard `opentimelineio` tracks, clips, gaps, and rational time ranges (`RationalTime` / `TimeRange`), preserving piecewise source-to-edit mappings across every cut.
- Import and export `.otio`, `.fcpxml`, and `.kdenlive` cleanly so edits stay inspectable and editable in external NLEs as well as code.

### S4. HyperFrames Runtime & 7-Class Asset Moat (`video_pipeline/hyperframes/`, `editing_system/assets/`)
- **7 Typed Asset Classes**:
  1. `tokens/` — Design tokens (`tokens.css`, `brand.json`) for single-pass global reskin (`04-global-reskin.md`).
  2. `layouts/` — 5 canonical 16:9 Scene Layouts (`Full Screen`, `Panel`, `Centre`, `Full Graphic`, `Circle`).
  3. `frameworks/` — 5 framework infographic families (`linear`, `non-linear`, `cyclical`, `hierarchical`, `matrix`).
  4. `heroes/` — Signature recurring templates reused 5–15 times per lesson with section variations.
  5. `motion/` — GSAP/CSS behaviors covering the 12 motion mechanics and 4 allowed transitions (`subtle`, `swipe`, `zoom`, `film_burn`).
  6. `graphics/` — Vector icons, logos, SVG marks, and device/browser/terminal mockups (`browser-frame.svg`, `terminal-frame.svg`).
  7. `audio/` — Curated local CC0/royalty-free SFX (`whoosh`, `pop`, `ui_click`, `soft_hit`, `riser`) and ambient music beds paired with attachment rules.
- Every reusable asset registers metadata (`id`, `class`, `subtype`, `aspect_ratios`, `tags`, `license`, `attribution`, `path`, `status`, `usage_rules`) in `catalog.json`, validated against `catalog.schema.json`.
- **Starter Asset Pack v0.1**: 1 Engineering Editorial token kit + 2 SVG mockups (landed in Phase 0), plus 5 Scene Layouts, 5 Framework templates, 1 Engineering Section Card Deck Hero template, core GSAP motion/transition primitives, and `sfx_rules.md` + manifest wiring in Phase 2.

### S5. Audio & SFX Layering (`video_pipeline/src/audio_mix.py`)
- Blocked until **Picture Lock** is confirmed.
- Uses local licensed audio files only (zero paid API integration in v1).
- Sidechain/envelope ducks music under dialogue so speech stays dominant; places subtle SFX strictly per `03-audio-and-sfx.md` (never louder than voiceover); normalizes final mix to `-14 LUFS / -1.0 dBTP` via FFmpeg `loudnorm` and verifies with `ebur128`.

### S6. Automated Pre-Human QC Runner (`video_pipeline/src/qc.py`)
- Runs automatically before any V1/Revision/Final render is surfaced to human review.
- **8 Hard-Blocking Core Gates**:
  1. `flash`: FFmpeg/OpenCV frame-diff check at joins and transitions (0 Flash Frames).
  2. `blank_check`: FFmpeg `blackdetect` + luma variance check (0 unintended black/blank frames).
  3. `fit`: `hyperframes check` + Chromium DOM overflow/clipping audit (0 clipped text nodes).
  4. `margin_check`: Chromium DOM bounding-box verification against 16:9 Safe Zone margins.
  5. `eyes_mouth_check`: MediaPipe/OpenCV face landmark bounding box vs. rendered overlay/caption regions when camera is visible.
  6. `stale_check`: `run.json` SHA-256 dependency verification ensuring `.otio`, `transcript.json`, `storyboard.json`, and `tokens.css` hashes match rendered artifacts.
  7. `hold_sentence`: `.otio` cut timestamps cross-checked against word timings (0 mid-word or mid-sentence cuts).
  8. `stability`: Fixed caption bounding-box anchor invariant across frames + frame-to-frame plate jitter check.
- **Waivers**: Allowed only for `eyes_mouth_check` and `freeze_check` via explicit timestamped entries with rationale in `run.json`.
- **6 Final Delivery Checks**: Full decode integrity, consonant tail decay audit at cut outs, `freeze_check`, subtitle timing sync, `ebur128` loudness/true-peak pass, and final frame/box Safe Zone check.

### S7. Compounding Feedback Memory (`editing_system/memory/`)
- Every human review note is appended to `review_log.jsonl` with `date`, `video_id`, `timestamp`, `category`, `tag` (`DO`, `DON'T`, `PREFERENCE`, `NON-NEGOTIABLE`), `note`, and `promoted_rule_id`.
- `taste_profile.md` summarizes active guidance read before Stage 2 and Stage 3.
- When an issue or preference recurs across >= 3 videos, agents propose promoting it to `editing_system/rules/`; human approval is required before mutating core Technical Engine Room rules.

## 5. Phased Delivery Roadmap & Verification Gates

- **Phase 0 (Foundation — Current Step):**
  - Land `GLOSSARY.md`, `docs/adr/0001..0002`, this plan, `editing_system/` scaffolding, `tokens/engineering-editorial/`, starter mockup SVGs, `catalog.schema.json`, `catalog.json`, and pointer updates in `AGENTS.md` and `experiments/post-production-video-editing.md`.
  - *Verification:* JSON Schema/SVG/glossary checks and existing unit + Remotion TypeScript checks pass with zero regressions.
- **Phase 1 (Dependencies, OTIO Timeline & Scientific Sifting):**
  - Add `opentimelineio==0.18.1`, `otio-fcpx-xml-lite-adapter==0.2.3`, `otio-kdenlive-adapter==0.0.3`, and `numpy` to `video_pipeline/pyproject.toml` (keeping `av<19`).
  - Implement `sift.py` and `timeline_otio.py` with FFmpeg/OTIO unit tests over synthetic WAV/MP4 fixtures (testing Room Tone 10% floor, `S/T/D/K/P` tail protection, demo motion hold preservation, and `.otio`/`.fcpxml`/`.kdenlive` round-trip).
- **Phase 2 (HyperFrames Runtime, Starter Asset Pack v0.1 & Contact Sheet):**
  - Install `hyperframes` (`0.9.86`) in `video_pipeline/hyperframes/`.
  - Implement the 5 Scene Layouts, 5 Framework templates, 1 Engineering Section Card Deck Hero template, core GSAP motion/transition behaviors, `storyboard` planner updates, and `cli.py contact-sheet` static PNG grid generator.
  - *Verification:* `hyperframes lint`, `hyperframes check`, and contact-sheet generation pass on a fixture timeline.
- **Phase 3 (Automated QC Runner & Audio Mix Layer):**
  - Add `opencv-python-headless` and `mediapipe` to `video_pipeline/pyproject.toml`.
  - Implement `qc.py` (all 8 gates + 6 delivery checks + `run.json` waiver audit) and `audio_mix.py` (Picture Lock guard, ducking, SFX triggers, `-14 LUFS / -1.0 dBTP`).
  - *Verification:* Synthetic defect suite triggers expected failures for Flash Frames, clipped DOM text, face overlap, stale hash, mid-word cut, and jitter; loudness passes `ebur128` bounds.
- **Phase 4 (Real Recording Trial, Taste Profile Loop & Harness Unification):**
  - Run the complete pipeline end-to-end on one real lesson recording (such as `de-for-fun/purchase-evidence`).
  - Inspect rendered frames and audio end-to-end, log real effort/observations in `experiments/post-production-video-editing.md` and `editing_system/memory/review_log.jsonl`.
  - Unify `.opencode/skills/post-production/` into thin wrappers delegating to `editing_system/`, update skill tests, and retire legacy `video_pipeline/renderer/` once HyperFrames parity is verified.
