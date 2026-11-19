---
description: Create corrected final-timeline subtitles and readable caption layouts for masters and clips.
mode: subagent
---

# Accessibility edit

Read `.opencode/skills/post-production/references/handoff.md` and its sibling `tools.md`. Use the composed timeline, corrected transcript and source mapping.

1. Generate master SRT/VTT from remapped speech, not copied raw times. Preserve meaning/technical spelling and flag unclear words for listening.
2. Check bounds, monotonic timing, segmentation, reading speed, line lengths and meaningful non-speech cues.
3. Supply caption settings and requested burned-in previews per layout. Inspect actual frames for contrast, safe zones and UI/webcam collisions.
4. Retiming/layout checks apply independently to zero-based clip captions. Changed parent timelines invalidate prior captions.

Done when files validate against exact duration, corrections are traceable, previews are inspected and listening uncertainties are explicit in `report.md`.
