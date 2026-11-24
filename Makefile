.DEFAULT_GOAL := help

include video_pipeline/Makefile.mk

.PHONY: help

help:
	@echo "Available targets:"
	@echo "  make video-setup                                        Install Python and Remotion dependencies"
	@echo "  make video-test                                         Run video_pipeline unit and FFmpeg smoke tests"
	@echo "  make video-cursor [VIDEO_EVENTS=events.json]            Record Hyprland cursor and dwell-click events"
	@echo "  make video-run VIDEO_INPUT=... [VIDEO_MODEL=...]        Run full transcribe -> plan -> assemble -> render pipeline"
	@echo "                 [VIDEO_EVENTS=...] [VIDEO_CAMERA=...]"
	@echo "  make video-studio                                       Open Remotion Studio for template preview"
	@echo "  make video-sift VIDEO_INPUT=...                         Run Stage 1 scientific sifting"
	@echo "  make video-contact-sheet STORYBOARD=... MANIFEST=...    Generate Stage 2 HyperFrames Contact Sheet"
	@echo "  make video-qc VIDEO_INPUT=...                           Run automated QC gates"
	@echo "  make video-catalog-check                                Validate editing_system/assets/catalog.json"
