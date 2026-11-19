# AI Video Pipeline — Creator & Recording Guide

This pipeline automates rough-cut editing, animated captions, and motion graphic overlays from raw talking-head footage.

It is an independent [post-production experiment](../experiments/post-production-video-editing.md) serving the [communication mission](../LESSON_FRAMEWORK_MISSION.md). Recordings do not require the presenter interface or slides. This guide describes operation; the experiment brief owns evaluation and continuation decisions.

## 1. Recording Guidelines

For agent-led production, invoke `@post-production` from this repository. The
[producer skill](../.opencode/skills/post-production/SKILL.md) coordinates ten
project-local specialist agents with rough-cut and final human review gates.
It reuses the CLI below; optional treatments and editor integrations are not
automatically implemented by the pipeline. See its capability reference before
using multitrack edits, vertical layouts, or external NLE handoffs.

Follow these habits while filming so the automated cut and graphic steps work reliably:

- **Use spoken retake markers or pause before restarting (`A1`).**
  - Say a retake marker (`"scratch that"`, `"retake"`, `"take two"`, `"start over"`, `"let me restart"`, or `"cut cut"`) to discard both the marker segment and the preceding botched segment automatically.
  - For short aborted starts (`<= 5` words), pause for `>= 1.0s` before restarting from the beginning of the sentence (`detect_retakes` also catches consecutive segments with shared starting words).
- **Leave a 1-second pause between takes and sections.**
  By default, silence detection triggers on gaps `>= 0.6s` below `-35 dB` (`--min-silence` and `--noise-db`). Clean 1-second pauses give the cutter unambiguous boundaries.
- **Keep room noise low.**
  If your room or fan noise sits above `-35 dB`, silence detection will miss pauses. Record in a quiet space or pass a higher threshold when transcribing (for example `--noise-db -28`).
- **Optionally capture a separate webcam track (`A4`).**
  Record the screen and webcam as separate files and pass `--camera /path/to/camera.mp4` (`VIDEO_CAMERA=...`). Remotion composites the camera in a bottom-right picture-in-picture frame over the screen track.
- **Optionally log Hyprland cursor events (`A3`).**
  Run `cli.py record-cursor` (or `make video-cursor`) alongside your screen recording to capture `events.json`, then pass `--events events.json` (`VIDEO_EVENTS=...`) to auto-generate `cursor_highlight` cues from dwell/focus clicks.
- **Frame for overlay safe zones.**
  - **Bottom ~15%**: Reserved for word-highlighted captions (`paddingBottom: 72px`). Keep important visuals or text above this band.
  - **Bottom-left**: Used by `lower_third` intro cards.
  - **Bottom-right**: Used by the picture-in-picture webcam container when `--camera` is provided.
  - **Top-left / Top-right**: Used by `callout`, `broll_card`, `stat_card`, `slide_card`, and `code_card` overlays. Leave headroom above your head so cards do not cover your face.

## 2. One-Time Setup

```bash
make video-setup
```

This installs the isolated Python environment in `video_pipeline/.venv` and the Remotion Node dependencies in `video_pipeline/renderer/node_modules`.

## 3. Running the Pipeline

### Full Automated Run

```bash
make video-run VIDEO_INPUT=/path/to/raw.mp4
# With companion cursor log and separate camera track:
make video-cursor VIDEO_EVENTS=events.json
make video-run VIDEO_INPUT=/path/to/screen.mp4 VIDEO_EVENTS=events.json VIDEO_CAMERA=/path/to/camera.mp4
```

Or invoke the CLI directly:

```bash
uv --project video_pipeline run python video_pipeline/src/cli.py record-cursor -o events.json --duration 30
uv --project video_pipeline run python video_pipeline/src/cli.py run /path/to/screen.mp4 --events events.json --camera /path/to/camera.mp4
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

During assembly (`A5`), `assemble_rough_cut` applies per-segment audio micro-fades (`0.02s`) to prevent cut clicks and normalizes the concatenated main audio with FFmpeg `loudnorm` (`-16 LUFS`, `-1.5 dB true peak`, `48 kHz`). Separate camera tracks (`rough_camera.mp4`) are cut without audio normalization (`has_audio=False`, `normalize_audio=False`).

### Output Artifacts

All outputs are written to `video_pipeline/workspace/<video-filename>/`:

| File | Purpose |
| --- | --- |
| `metadata.json` | Resolution, FPS, duration, and audio stream info from `ffprobe` |
| `audio.wav` | Extracted 16 kHz mono WAV used for transcription |
| `transcript.json` | Word-level timestamps plus detected silences, fillers, and retakes |
| `edl.json` | Edit Decision List (`kept_segments`, optional `camera_path`, and `graphic_cues`) |
| `rough_cut.mp4` | Concatenated A-roll / screen video with dead air and bad takes removed (`loudnorm` `-16 LUFS` + micro-fades) |
| `rough_camera.mp4` | Cut separate camera track when `--camera` is provided (muted, no audio normalization) |
| `timeline_manifest.json` | Remapped word timings, optional `cameraFile`, and graphic cues for Remotion |
| `timeline.fcpxml` | FCPXML 1.9 timeline with cut clips and markers for DaVinci Resolve |
| `final.mp4` | Final rendered MP4 with animated captions, motion graphics, and optional PiP camera |

## 4. Reviewing and Tweaking Edits

You do not need to re-transcribe if you want to adjust cuts or graphics:

1. Open `video_pipeline/workspace/<name>/edl.json` and edit `kept_segments` (source timestamps in seconds) or `graphic_cues` (`lower_third`, `callout`, `stat_card`, `broll_card`, `slide_card`, `code_card`, and `cursor_highlight` with normalized `x`/`y` coordinates (`A2`), positioned on the edited timeline).
2. Re-plan with cursor events or re-assemble and re-render:

```bash
uv --project video_pipeline run python video_pipeline/src/cli.py plan video_pipeline/workspace/<name>/transcript.json --events events.json
uv --project video_pipeline run python video_pipeline/src/cli.py assemble video_pipeline/workspace/<name>/edl.json --camera /path/to/camera.mp4
uv --project video_pipeline run python video_pipeline/src/cli.py render video_pipeline/workspace/<name>/timeline_manifest.json
```

3. To preview or tweak Remotion templates interactively:

```bash
make video-studio
```

4. To finish the edit manually in DaVinci Resolve instead, import `video_pipeline/workspace/<name>/timeline.fcpxml` via **File -> Import -> Timeline** (`Import AAF, EDL, XML...`).
