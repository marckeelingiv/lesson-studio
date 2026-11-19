# Experiment: post-production video editing

**Status:** experimental implementation available; outcome evaluation not recorded here.

## Hypothesis

Transcript-assisted editing can reduce the effort required to produce a clear, shareable engineering video while preserving meaning and visual continuity.

## Current manifestation

`video_pipeline/` provides transcription, retake detection, optional model-assisted edit planning, FFmpeg assembly, Remotion captions/graphics, and an NLE handoff. See its [operating guide](../video_pipeline/README.md) and [agent instructions](../video_pipeline/AGENTS.md).

Input can come from OBS, a direct screen recording, or the presenter experiment. The JavaScript presenter interface and slides are not prerequisites. The planner uses transcript evidence, not video frames; screen continuity requires human review. Presenter take notes are not automatically ingested as edit decisions.

## Alternatives

Publish a good uncut take; use simple manual trimming; edit entirely in an NLE; use deterministic cuts without AI planning; use captions without motion graphics. A simpler acceptable output is a valid result.

## Next trial and evaluation

Preserve a raw take and compare the pipeline-assisted edit with an uncut or simply trimmed baseline, using the same communication goal.

- Record processing time separately from hands-on editing/review time and correction effort.
- Inspect meaning preservation, retake removal, audio transitions, screen continuity, captions, readability, framing, and overlay placement.
- Record whether the result is suitable for sharing and whether added polish improves understanding; collect viewer feedback when available.

Continue automation where it saves effort without sacrificing the explanation. Simplify or prefer manual editing where correction costs erase the benefit. Agree concrete thresholds after observing a baseline.

## Trial record

### 2026-11-18 — staged agent workflow decision

Retain the existing pipeline as the execution backend and add a project-local
[producer skill](../.opencode/skills/post-production/SKILL.md) with specialist
agents, auditable edits, independent QC and human approval gates. The November 17
recording's initial trim-only candidate did not meet the user's expectation of
pause/filler removal; the later tightened candidate still needs human listening
and end-to-end approval. This motivates measurable stage handoffs, not a claim
that the new workflow improves output quality or retention.

FilmCraft remains an optional evaluation, not a required dependency. Pilot the
skill on the existing transcript and tightened cut after obtaining pacing
feedback. Captioned master, standalone clips, effort comparison, NLE import
verification, and final outcome evaluation remain pending.

No outcome evaluation is recorded in this brief yet. For each trial append: date, communication goal, raw take and code commit, baseline, edit/workspace and reviewed output links, effort and corrections, observations, and a retain/revise/pause/retire decision with rationale. Preserve originals and selected workspaces according to the [asset guide](../CONTENT_ASSETS.md).

### 2026-11-18 — separate ArtCraft-first workflow implementation decision

Prepare an opt-in [ArtCraft-first skill](../.opencode/skills/post-production-artcraft/SKILL.md),
with FilmCraft as the primary editor and EffectCraft/SoundCraft as optional
treatments. Verify tool sources and actual capabilities before installation or
use; do not infer supported operations from product names or workflow intent.
This is a separate implementation trial, not a replacement for the default
`@post-production` workflow or its pipeline backend, and does not revise the
existing run or the preceding evaluation record.

Installation, local runtime compatibility, media processing, and outcome
evaluation remain unverified/pending. No successful local execution or reviewed
output is claimed. Preserve originals, use the existing workspace conventions,
and apply the same baseline comparison and human review before deciding whether
to retain this alternative.
