# Ideas & Roadmap

## Core Architectural Decision

- **D1 (Post-Production Pipeline over Desktop GUI):** Do not build a custom native Linux desktop app (GTK4, PySide6, or Electron) to replace OBS or replicate Screen Studio live. Use **OBS** (or `gpu-screen-recorder`) for reliable raw capture, **faster-whisper** for word-level transcription, an **AI editorial planner** emitting structured JSON (`edl.json`), and **FFmpeg + Remotion** to render cuts, captions, React slides, code cards, icons/callouts, and animated cursor highlights.
  - Why: Remotion renders React components to video, keeping slides, captions, callouts, and cursor highlights in one codebase that coding agents can edit directly. The hard problem is reliable retake detection and visual polish, not window management.

## End-to-End Pipeline Sketch

1. **Capture:** OBS (or `gpu-screen-recorder`) records the raw take, paired with spoken retake markers (e.g., `"retake"`, `"scratch that"`, `"take two"`) or a deliberate >= 1s pause before restarting a sentence, plus an optional cursor/click event log.
2. **Transcribe & Flag Retakes:** `video_pipeline/src/transcribe.py` extracts word-level timestamps via `faster-whisper` and flags silences, filler words, spoken retake phrases, pause-bounded aborted starts, and overlapping false starts (`transcript.json`).
3. **Agent EDL Planning:** `video_pipeline/src/planner.py` (via OpenCode or LiteLLM, with deterministic heuristic fallback) reads `transcript.json` and emits `edl.json` containing `kept_segments` and `graphic_cues`.
4. **Assemble & Render:** `assemble.py` builds `rough_cut.mp4` via FFmpeg and remaps word timestamps into `timeline_manifest.json`. Remotion (`video_pipeline/renderer/`) renders captions and React motion graphics into `final.mp4`, while `export_nle.py` generates `timeline.fcpxml` for DaVinci Resolve.

## Open-Source Inspiration Catalog (`O1`–`O5`)

- **O1 (`remotion-dev/remotion`, `remotion-dev/recorder`, `@remotion/captions`, `remotion-dev/skills`):** Separate-track recording (webcam and screen captured independently so Remotion can zoom into code without cropping the presenter), `@remotion/captions` page/token timing primitives, and React-based video composition skills.
- **O2 (`siddharthvaddem/openscreen`, `cap-go/cap`):** Open-source Screen Studio alternatives demonstrating click-triggered auto-zoom keyframes, smooth cursor interpolation, and canvas styling.
- **O3 (`slidevjs/slidev`, `shikijs/shiki-magic-move`, `code-hike/codehike`):** Token-diff code morphing and step-by-step line highlighting for technical walkthroughs.
- **O4 (`DataAnts-AI/CutScript`, `vorniches/cutstorm`):** Transcript-first Descript-style word-level cutting workflows driven by Whisper/WhisperX + FFmpeg.
- **O5 (`heygen-com/hyperframes`, `browser-use/video-use`, `motion-canvas/motion-canvas`):** Agent-driven programmatic rendering workflows and code-driven diagram/explainer animations.

## Feature Backlog (`A1`–`A6`)

| Code | Status | Feature | Scope & Notes |
| --- | --- | --- | --- |
| **A1** | Implemented | Spoken retake marker & pause-restart detection | Detects `"retake"`, `"scratch that"`, `"take two"`, `"start over"`, `"let me restart"`, `"cut cut"` (both inline and standalone markers that discard the preceding botched segment) plus short aborted starts followed by a `>= 1.0s` reset pause. |
| **A2** | Implemented | Remotion React cards (`slide_card`, `code_card`, `cursor_highlight`) | Expands `GraphicCue` schema (`schema.py`, `types.ts`) and `Graphics.tsx` so the agent planner can emit presentation slides, monospace code snippets, and normalized `(x, y)` animated cursor/focus rings. |
| **A3** | Implemented | Companion cursor & click event logger | Record OS/window cursor coordinates and click timestamps alongside OBS capture (`events.json`) to auto-generate `cursor_highlight` cues and zoom keyframes. |
| **A4** | Implemented | Separate-track camera + screen compositing | Capture webcam and screen as separate files/tracks (`O1` pattern) so Remotion can zoom full-screen onto dense terminal or IDE content while keeping or hiding the presenter camera independently. |
| **A5** | Implemented | Audio loudness normalization & J/L-cuts | Add FFmpeg `loudnorm` (`-16 LUFS`), gentle compression, and audio overlap across cuts in `assemble.py`. |
| **A6** | Planned | Shiki syntax highlighting & code morphing | Render syntax-highlighted and token-morphed code transitions (`O3`) directly inside Remotion `code_card` compositions. |
