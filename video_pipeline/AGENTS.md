# Video pipeline

- Read `README.md` in this directory for setup, stage commands, and artifact formats.
- Before workflow changes, read `../LESSON_FRAMEWORK_MISSION.md` and `../experiments/post-production-video-editing.md`. This experiment can operate without the presenter interface; implementation status is not evidence of communication benefit.
- From the repository root, invoke Python with `uv run --project video_pipeline python ...` to use the isolated environment.
- Prefer `--model opencode` (or `VIDEO_MODEL=opencode` for Make targets) to reuse existing OpenCode provider authentication without an additional API key. Explicit model selection uses `opencode/<provider>/<model>`.
- After planner changes, run `uv run --project video_pipeline python video_pipeline/src/test_planner.py` from the repository root. These tests mock OpenCode; verify authentication and CLI output compatibility with a real planning run when changing the bridge.
- Keep the `av<19` compatibility constraint until faster-whisper supports PyAV 19: faster-whisper 1.2.1 passes the removed `metadata_errors` argument to `av.open`.
- Planning uses transcript timestamps and detected edit candidates, not video frames. Screen-recording continuity and overlay placement require visual review; successful rendering alone does not establish edit quality.
- Preserve source recordings. Keep generated artifacts in `video_pipeline/workspace/<video-filename>/`; reuse the transcript for editorial revisions instead of transcribing again.
