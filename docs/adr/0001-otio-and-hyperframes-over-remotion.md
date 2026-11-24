# ADR-0001: OpenTimelineIO and HyperFrames over Remotion

Status: accepted

We will adopt OpenTimelineIO (`.otio`) plus FFmpeg in `video_pipeline/` as the canonical NLE-native timeline and interchange layer, paired with HyperFrames (`heygen-com/hyperframes`) and HyperFrames Studio for HTML/CSS/GSAP motion plates, scene layouts, captions, contact sheets, and bidirectional visual and code editing. We will keep the existing Remotion renderer (`video_pipeline/renderer/`) untouched as a temporary legacy fallback and retire it once HyperFrames proves parity on one real video.

## Considered Options

- **Remotion-only (`video_pipeline/renderer/`)**: Already implemented with passing checks, but lacks bidirectional visual-plus-code timeline editing and does not give coding agents an NLE-native clip/track interchange model.
- **HyperFrames-only with one-way FCPXML export**: HyperFrames excels at HTML/CSS/GSAP motion plates and Studio visual editing, but `heygen-com/hyperframes` does not natively import or export `.otio` or FCPXML timelines.
- **FilmCraft + HyperFrames**: Documented in `.opencode/skills/post-production-artcraft/`, but FilmCraft is not locally installed or runtime-verified here, whereas OpenTimelineIO + FFmpeg + `kdenlive`/Resolve interchange runs locally on Python 3.13.

## Consequences

- Agents manipulate clips, tracks, markers, and rational time ranges directly in `.otio` instead of doing brittle manual frame math, while round-tripping with FCPXML and Kdenlive via `otio-fcpx-xml-lite-adapter` and `otio-kdenlive-adapter`.
- Phase 1/2 setup requires adding `opentimelineio` and its adapters to `video_pipeline/pyproject.toml` (preserving `av<19`) and installing `hyperframes` under `video_pipeline/hyperframes/`.
- Existing Remotion unit tests and TypeScript checks stay green until HyperFrames passes a verified end-to-end trial on a real recording.
