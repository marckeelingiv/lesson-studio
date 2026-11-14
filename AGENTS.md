# AGENTS.md

Compact guidance for AI agents working in this repository.

## References

- For workflow changes, read `LESSON_FRAMEWORK_MISSION.md`, the relevant brief in `experiments/`, and its operating guide first. Treat the presenter and post-production implementations as independent experiments, not mission requirements. For asset placement, read `CONTENT_ASSETS.md`. Keep lesson plans here; link technical evidence to its subject repository.

- [video_pipeline/AGENTS.md](video_pipeline/AGENTS.md) — Planner auth, `av<19` constraint, and review rules.
- [video_pipeline/README.md](video_pipeline/README.md) — Setup, CLI stages, and output artifacts.
- [IDEAS_AND_ROADMAP.md](IDEAS_AND_ROADMAP.md) — Architecture (`D1`) and feature status (`A1`–`A6`).

## Toolchain & Verification

- **Python 3.13 via `uv`**: Always run Python commands with `uv run --project video_pipeline python ...` (never invoke bare `python`/`python3` or activate `.venv` manually).
- **PyAV constraint**: Keep `av<19` in `video_pipeline/pyproject.toml` until `faster-whisper` supports PyAV 19.
- **Unit tests**:
  - `uv --project video_pipeline run python -m unittest discover -s video_pipeline/tests -p "test_*.py" -v`
  - `uv --project video_pipeline run python -m unittest discover -s video_pipeline/src -p "test_*.py" -v`
- **Remotion TypeScript check**:
  - `npx --prefix video_pipeline/renderer tsc -p video_pipeline/renderer/tsconfig.json --noEmit`

## Operational Rules

- Never add `Co-authored-by` trailers to commit messages.
- Never claim visual review or overlay placement quality without inspecting rendered frames/video; successful rendering alone only proves execution.
- Preserve source recordings and keep generated outputs inside `video_pipeline/workspace/<video-filename>/`.
