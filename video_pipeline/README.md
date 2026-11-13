# AI Video Pipeline — Creator & Recording Guide

This pipeline automates rough-cut editing, animated captions, and motion graphic overlays from raw talking-head footage.

## 1. Recording Guidelines

Follow these habits while filming so the automated cut and graphic steps work reliably:

- **Restart from the beginning of the sentence on mistakes.**
  `detect_retakes` compares consecutive transcript segments for shared starting words. If you stumble mid-sentence, pause briefly and repeat the full sentence from the start rather than patching only the last two words.
- **Leave a 1-second pause between takes and sections.**
  By default, silence detection triggers on gaps >= `0.6s` below `-35 dB` (`--min-silence` and `--noise-db`). Clean 1-second pauses give the cutter unambiguous boundaries.
- **Keep room noise low.**
  If your room or fan noise sits above `-35 dB`, silence detection will miss pauses. Record in a quiet space or pass a higher threshold when transcribing (for example `--noise-db -28`).
- **Frame for overlay safe zones.**
  - **Bottom ~15%**: Reserved for word-highlighted captions (`paddingBottom: 72px`). Keep important visuals or text above this band.
  - **Bottom-left**: Used by `lower_third` intro cards.
  - **Top-left / Top-right**: Used by `callout`, `broll_card`, and `stat_card` overlays. Leave headroom above your head so cards do not cover your face.

## 2. One-Time Setup

```bash
make video-setup
```

This installs the isolated Python environment in `video_pipeline/.venv` and the Remotion Node dependencies in `video_pipeline/renderer/node_modules`.

## 3. Running the Pipeline

### Full Automated Run

```bash
make video-run VIDEO_INPUT=/path/to/raw.mp4
```

To use an LLM for editorial cut selection and motion graphic cues, export an API key before running (any `litellm`-supported provider works, such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY`):

```bash
export OPENAI_API_KEY="sk-..."
make video-run VIDEO_INPUT=/path/to/raw.mp4 VIDEO_MODEL=gpt-4o-mini
```

If no API key is set, the planner automatically falls back to deterministic heuristic cutting (removing detected silences and retakes).

To reuse your existing OpenCode provider login instead (no additional API key):

```bash
make video-run VIDEO_INPUT=/path/to/raw.mp4 VIDEO_MODEL=opencode
# Or select a configured OpenCode provider/model:
make video-run VIDEO_INPUT=/path/to/raw.mp4 VIDEO_MODEL=opencode/openai/gpt-6.1-sol
```

Requires `opencode` on PATH and an authenticated provider. `opencode` uses your default model; `opencode/<provider>/<model>` selects one explicitly. Only the transcript and detected edit candidates are sent to the model, not the video. Planner errors stop the run rather than silently falling back.

### Output Artifacts

All outputs are written to `video_pipeline/workspace/<video-filename>/`:

| File | Purpose |
| --- | --- |
| `metadata.json` | Resolution, FPS, duration, and audio stream info from `ffprobe` |
| `audio.wav` | Extracted 16 kHz mono WAV used for transcription |
| `transcript.json` | Word-level timestamps plus detected silences, fillers, and retakes |
| `edl.json` | Edit Decision List (`kept_segments` and `graphic_cues`) |
| `rough_cut.mp4` | Concatenated A-roll video with dead air and bad takes removed |
| `timeline_manifest.json` | Remapped word timings and graphic cues for Remotion |
| `timeline.fcpxml` | FCPXML 1.9 timeline with cut clips and markers for DaVinci Resolve |
| `final.mp4` | Final rendered MP4 with animated captions and motion graphics |

## 4. Reviewing and Tweaking Edits

You do not need to re-transcribe if you want to adjust cuts or graphics:

1. Open `video_pipeline/workspace/<name>/edl.json` and edit `kept_segments` (source timestamps in seconds) or `graphic_cues` (`lower_third`, `callout`, `stat_card`, `broll_card` positioned on the edited timeline).
2. Re-assemble and re-render:

```bash
uv --project video_pipeline run python video_pipeline/src/cli.py assemble video_pipeline/workspace/<name>/edl.json
uv --project video_pipeline run python video_pipeline/src/cli.py render video_pipeline/workspace/<name>/timeline_manifest.json
```

3. To preview or tweak Remotion templates interactively:

```bash
make video-studio
```

4. To finish the edit manually in DaVinci Resolve instead, import `video_pipeline/workspace/<name>/timeline.fcpxml` via **File -> Import -> Timeline** (`Import AAF, EDL, XML...`).

## Presenting and recording lessons

Use [Lesson Studio](../lesson_studio/README.md) for a private presenter console, clean audience stage, reusable lesson JSON, and raw recording handoff into this pipeline.
