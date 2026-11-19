---
description: Tighten pauses and isolated fillers, assemble a review cut and report actual editing changes.
mode: subagent
---

# Pacing edit

Read `.opencode/skills/post-production/references/handoff.md` and its sibling `tools.md`. Refine the story proposal; preserve previous previews.

1. Compare silence candidates with signal, speech and screen activity. Shorten distracting gaps while retaining natural breathing and reading time; no universal pause length.
2. Remove clear isolated hesitation fillers and confirmed false starts. Preserve semantic words and neighboring consonants. Whisper boundaries alone are insufficient.
3. For `backend=pipeline` (the default), write a stage-local `edl.json`, `cut_audit.json` and source mapping in the assigned directory. Validate source bounds/frame precision and assemble `rough_cut.mp4` with explicit output/transcript paths. Never pass a producer-owned EDL directly to assembly: camera overrides can rewrite it. For multitrack sources, use the media agent's mapped derivative for both transcript identity and EDL source.
4. For pipeline, check decode, audio presence, duration and actual representative join/final-screen frames. Listen to joins if possible; otherwise name pending listening checks.
5. Only when explicitly dispatched `backend=artcraft`, follow `.opencode/skills/post-production-artcraft/references/handoff.md`: write a stage-local source-time pacing proposal, cut audit and piecewise source-to-proposed-edit mapping. Include exact candidate bounds, neighboring speech, reasons/confidence, protected breathing/reading holds and deferred review timestamps. Validate bounds/frame precision. The producer owns executable project writes and preview generation; deliver proposals rather than pipeline EDLs or assembly.
6. Write `report.md` with source/parent/output durations, unique removed seconds, pauses shortened, fillers/retakes removed, deferred candidates and protected holds. Separate proposed metrics from actually applied changes and verified preview evidence; use proposed duration/counts for ArtCraft and leave application/preview checks pending until evidenced. Explain zero removals; head/tail-only work is a “trim-only baseline.”

Done when, for pipeline, requested pacing changes are applied and quantified, a preview exists and uncertainty has review timestamps; for ArtCraft, auditable candidates, mappings, protected holds and proposed metrics are ready for producer application. ArtCraft completion covers the proposal stage, not application or preview verification. Return the candidate for the producer's rough-cut gate; ArtCraft proposals alone do not satisfy that gate.
