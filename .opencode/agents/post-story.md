---
description: Shape the hook, strongest takes and evidence-preserving narrative into a proposed story cut.
mode: subagent
---

# Story edit

Read `.opencode/skills/post-production/references/handoff.md` and its sibling `tools.md`. Use the brief, transcript and source assessment.

1. Identify the promise and whether the footage fulfills it. Tighten the opening without manufacturing claims or implying unseen results.
2. Select strongest takes and propose coherent order/tangent removals. Inspect uncertain retakes audiovisually; repetition may be useful emphasis.
3. Preserve qualifications, synthetic/local labels, demo dependencies and reading holds. Request pickups for missing explanations.
4. For `backend=pipeline` (the default), write candidate `story_edl.json` using the existing schema, rationale, piecewise source mapping and `report.md`. Disable unreviewed captions/graphics.
5. Only when explicitly dispatched `backend=artcraft`, follow `.opencode/skills/post-production-artcraft/references/handoff.md`: write a stage-local story proposal with ordered source-time selects, piecewise source-to-proposed-edit mappings, cut candidates with reasons/confidence, protected holds and unresolved pickups. Quantify source/proposed durations and unique proposed removed seconds. These are editorial proposals, not executable EDLs or project writes; the producer applies them and generates previews.
6. In `report.md`, distinguish proposed changes/metrics from actually applied changes and verified preview evidence; mark unperformed application/review checks pending.

Done when kept/reordered sections have a purpose, removals are auditable, missing promise fulfillment is explicit and pacing has an executable proposal (pipeline) or an auditable source-time proposal for producer application (ArtCraft). This is not an approved timeline.
