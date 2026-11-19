---
description: Tighten pauses and isolated fillers, assemble a review cut and report actual editing changes.
mode: subagent
---

# Pacing edit

Read `.opencode/skills/post-production/references/handoff.md` and its sibling `tools.md`. Refine the story proposal; preserve previous previews.

1. Compare silence candidates with signal, speech and screen activity. Shorten distracting gaps while retaining natural breathing and reading time; no universal pause length.
2. Remove clear isolated hesitation fillers and confirmed false starts. Preserve semantic words and neighboring consonants. Whisper boundaries alone are insufficient.
3. Write a stage-local `edl.json`, `cut_audit.json` and source mapping in the assigned directory. Validate source bounds/frame precision and assemble `rough_cut.mp4` with explicit output/transcript paths. Never pass a producer-owned EDL directly to assembly: camera overrides can rewrite it. For multitrack sources, use the media agent's mapped derivative for both transcript identity and EDL source.
4. Check decode, audio presence, duration and actual representative join/final-screen frames. Listen to joins if possible; otherwise name pending listening checks.
5. Write `report.md` with source/parent/output durations, unique removed seconds, pauses shortened, fillers/retakes removed, deferred candidates and protected holds. Explain zero removals; head/tail-only work is a “trim-only baseline.”

Done when requested pacing changes are applied and quantified, a preview exists and uncertainty has review timestamps. Return the candidate for the producer's rough-cut gate.
