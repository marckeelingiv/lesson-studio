VIDEO_INPUT ?=
VIDEO_MODEL ?= gpt-4o-mini
WHISPER_MODEL ?= base
VIDEO_EVENTS ?=
VIDEO_CAMERA ?=

.PHONY: video-setup video-test video-run video-cursor video-studio

video-setup:
	@echo "=== Installing video_pipeline Python and Remotion dependencies ==="
	@uv --project video_pipeline sync
	@npm --prefix video_pipeline/renderer install

video-test:
	@echo "=== Running video_pipeline unit and FFmpeg smoke tests ==="
	@uv --project video_pipeline run python -m unittest discover -s video_pipeline/tests -v

video-run:
	@test -n "$(VIDEO_INPUT)" || (echo "Usage: make video-run VIDEO_INPUT=/path/to/video.mp4" && exit 1)
	@uv --project video_pipeline run python video_pipeline/src/cli.py run "$(VIDEO_INPUT)" --whisper-model "$(WHISPER_MODEL)" --model "$(VIDEO_MODEL)" $(if $(VIDEO_EVENTS),--events "$(VIDEO_EVENTS)") $(if $(VIDEO_CAMERA),--camera "$(VIDEO_CAMERA)")

video-cursor:
	@uv --project video_pipeline run python video_pipeline/src/cli.py record-cursor -o "$(or $(VIDEO_EVENTS),events.json)"

video-studio:
	@npm --prefix video_pipeline/renderer run studio
