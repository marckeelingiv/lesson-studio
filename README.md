# Lesson Studio

Local lesson authoring, presenter/audience recording, and video post-production.

These are experiments in communicating engineering judgment, not a required slides-to-video workflow. Use either implementation independently, combine them, or choose a simpler format.

- [Framework mission](LESSON_FRAMEWORK_MISSION.md)
- Experiment briefs: [presenter-assisted delivery](experiments/presenter-assisted-delivery.md) and [post-production editing](experiments/post-production-video-editing.md).
- [Recording studio guide](lesson_studio/README.md): start with `node lesson_studio/serve.mjs`.
- [Repository and asset ownership](CONTENT_ASSETS.md)
- [Lesson library](lessons/README.md): start with the [DE for Fun series](lessons/de-for-fun/README.md) and its first recording brief; platform code and technical evidence remain in DE for Fun.

## AI Video Post-Production Pipeline

Local-first, transcript-driven post-production pipeline for technical walkthroughs and talking-head recordings:

1. **Capture** raw takes with OBS or `gpu-screen-recorder`, optionally alongside a separate webcam file (`--camera`) and Hyprland cursor event log (`record-cursor` / `--events`).
2. **Transcribe & detect retakes** with word-level timestamps via `faster-whisper` (`video_pipeline/src/transcribe.py`).
3. **Plan edits via an AI agent** (`video_pipeline/src/planner.py` via OpenCode or LiteLLM, with deterministic heuristic fallback) emitting `edl.json`.
4. **Assemble & render** loudness-normalized cuts with FFmpeg (`assemble.py`), animated React captions/overlays/PiP compositing with Remotion (`video_pipeline/renderer/`), and FCPXML 1.9 timelines for DaVinci Resolve (`export_nle.py`).

## Quick Start

```bash
# 1. Install Python (.venv) and Remotion (node_modules) dependencies
make video-setup

# 2. Optional: record Hyprland cursor coordinates and dwell clicks
make video-cursor VIDEO_EVENTS=events.json

# 3. Run the full pipeline (with optional cursor events and separate camera track)
make video-run VIDEO_INPUT=/path/to/screen.mp4 VIDEO_MODEL=opencode
make video-run VIDEO_INPUT=/path/to/screen.mp4 VIDEO_MODEL=opencode VIDEO_EVENTS=events.json VIDEO_CAMERA=/path/to/camera.mp4

# 4. Preview or tweak Remotion templates interactively
make video-studio
```

Run tests and typecheck:

```bash
make video-test
uv --project video_pipeline run python -m unittest discover -s video_pipeline/src -p "test_*.py" -v
npx --prefix video_pipeline/renderer tsc -p video_pipeline/renderer/tsconfig.json --noEmit
```

## Recording Tips & Pipeline Behavior

- **Spoken retake markers & pause-restarts (`A1`)**: Say `"scratch that"`, `"retake"`, `"take two"`, `"start over"`, `"let me restart"`, or `"cut cut"` to drop both the marker and the preceding botched segment. Short aborted starts (`<= 5` words) followed by a `>= 1.0s` pause are also flagged automatically. Leave clean ~1-second pauses between sections (`--min-silence 0.6`, `--noise-db -35`).
- **7 `GraphicCue` types & overlay safe zones (`A2`)**: `lower_third` (bottom-left), `callout`, `stat_card`, `broll_card`, `slide_card`, `code_card`, and `cursor_highlight` (normalized `x`, `y` focus ring). Keep critical screen UI above the bottom ~15% caption band (`paddingBottom: 72px`) and clear of the bottom-right PiP corner when using `--camera`.
- **Hyprland cursor & click logger (`A3`)**: `cli.py record-cursor` (or `make video-cursor`) polls `hyprctl cursorpos -j` to emit `events.json`; passing `--events events.json` maps dwell/focus clicks onto kept segments as `cursor_highlight` cues and drops clicks inside cut takes.
- **Separate camera + screen compositing (`A4`)**: Pass `--camera /path/to/camera.mp4` (`VIDEO_CAMERA=...`) to cut `rough_camera.mp4` in sync with `rough_cut.mp4` and render it muted as a bottom-right picture-in-picture overlay in Remotion.
- **Audio loudness & micro-fades (`A5`)**: `assemble_rough_cut` applies `0.02s` per-segment `afade` micro-fades to prevent hard-cut clicks and normalizes the main track with FFmpeg `loudnorm` (`-16 LUFS`, `-1.5 dB` true peak, `48 kHz`).

## Planner Options (`OpenCode` / `LiteLLM`)

- **OpenCode (`VIDEO_MODEL=opencode` or `opencode/<provider>/<model>`)**: Reuses your authenticated `opencode` CLI login without a separate API key. Only transcript text and detected edit candidates are sent to the model.
- **LiteLLM (`VIDEO_MODEL=gpt-4o-mini`, etc.)**: Export `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or `OPENROUTER_API_KEY`.
- **Heuristic fallback**: If no credentials are configured (or `--heuristic` is passed), `planner.py` deterministically removes detected silences and retakes and injects baseline graphic cues.

## Key Documents

- [video_pipeline/README.md](video_pipeline/README.md) — Stage-by-stage CLI commands, recording guidelines, and workspace artifacts.
- [IDEAS_AND_ROADMAP.md](IDEAS_AND_ROADMAP.md) — Architecture decision (`D1`), open-source inspiration (`O1`–`O5`), and feature status (`A1`–`A6`).
- [video_pipeline/AGENTS.md](video_pipeline/AGENTS.md) — Detailed planner, PyAV compatibility, and visual review constraints.
- [video_pipeline/RESEARCH.md](video_pipeline/RESEARCH.md) — Reference automated editing workflows and zero-cost local stack notes.
