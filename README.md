# Lesson Studio & AI Video Pipeline

A local-first, agent-friendly post-production workflow for technical lessons and engineering walkthroughs:

1. **Record raw takes** with OBS (or `gpu-screen-recorder`), using spoken retake markers (`"retake"`, `"scratch that"`, `"take two"`) or clean 1-second pauses before restarting botched sentences. Optionally run the lightweight browser presenter stage in [lesson_studio/](lesson_studio/README.md).
2. **Transcribe & detect retakes** with word-level timestamps via `faster-whisper` (`video_pipeline/src/transcribe.py`).
3. **Plan edits via an AI agent** (`video_pipeline/src/planner.py` using OpenCode or LiteLLM) to emit a structured Edit Decision List (`edl.json`) with kept speech segments and graphic cues.
4. **Assemble & render** clean cuts with FFmpeg (`assemble.py`), React captions/slides/code/cursor overlays with Remotion (`video_pipeline/renderer/`), and FCPXML 1.9 timelines for DaVinci Resolve (`export_nle.py`).

## Key Documents

- [IDEAS_AND_ROADMAP.md](IDEAS_AND_ROADMAP.md) — Architectural decision (`D1`), open-source inspiration catalog (`O1`–`O5`), and feature backlog (`A1`–`A6`).
- [video_pipeline/README.md](video_pipeline/README.md) — Recording habits, setup, CLI commands, and output artifacts.
- [video_pipeline/RESEARCH.md](video_pipeline/RESEARCH.md) — Reference creator workflows and zero-cost local stack notes.
- [lesson_studio/README.md](lesson_studio/README.md) — Optional dual-window browser presenter console and audience stage.
- [LESSON_FRAMEWORK_MISSION.md](LESSON_FRAMEWORK_MISSION.md) — Reusable lesson methodology and evidence guidelines.

## Quick Start

```bash
# 1. Install video pipeline Python + Remotion dependencies
make video-setup

# 2. Run pipeline on a raw recording (using OpenCode auth or litellm API key)
make video-run VIDEO_INPUT=/path/to/raw.mp4 VIDEO_MODEL=opencode

# 3. Preview or edit Remotion components interactively
make video-studio

# Optional: run the browser presenter/audience stage on http://127.0.0.1:4173
make studio
```

Run tests:

```bash
make video-test
uv --project video_pipeline run python video_pipeline/src/test_planner.py
```
