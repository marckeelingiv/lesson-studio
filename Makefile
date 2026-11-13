STUDIO_PORT ?= 4173

include video_pipeline/Makefile.mk

.PHONY: studio

studio:
	@node lesson_studio/serve.mjs $(STUDIO_PORT)
