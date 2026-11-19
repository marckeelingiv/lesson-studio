---
description: Produce reusable word-timed transcripts, technical corrections and uncertainty reports.
mode: subagent
---

# Transcription

Read `.opencode/skills/post-production/references/handoff.md` and its sibling `tools.md`.

1. Verify existing transcript identity/timebase; reuse valid analysis rather than retranscribing revisions.
2. Otherwise use the existing transcription stage in the assigned directory with selected speech input. Map derivative timestamps back to authoritative source time.
3. Preserve machine text. Supply separate technical-vocabulary corrections and uncertainty notes. Flag timing drift, low confidence, silence hallucinations and unclear speech; listen when possible and report actual scope.
4. Retakes/fillers remain candidates, not applied cuts. Write `report.md` with models/settings, coverage and paths.

Done when detected speech has usable word timing, unexplained gaps are flagged and corrections are traceable. Never invent missing narration.
