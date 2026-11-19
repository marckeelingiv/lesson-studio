---
name: Post Production
description: Coordinate specialist subagents to edit raw recordings, review existing cuts, add accessible polish, and prepare YouTube videos and LinkedIn clips in Lesson Studio.
---

# Post-production producer

Turn recordings into reviewable communication assets. Optimize for clarity and credible engineering judgment, not a promised retention score.

## Start

1. Read repository `AGENTS.md`, `LESSON_FRAMEWORK_MISSION.md`, `CONTENT_ASSETS.md`, `experiments/post-production-video-editing.md`, and `video_pipeline/AGENTS.md` and `README.md`. Resolve repository paths from the active project, not this skill directory.
2. Confirm source paths, audience/promise, deliverables, and existing approved revision. Ask only for missing decisions. Propose YouTube 16:9 plus up to two LinkedIn excerpts as defaults, not mandatory output counts.
3. Inspect the existing workspace and concurrent work. Preserve originals and previous revisions. Use `video_pipeline/workspace/<source-stem>/post-production/<unique-run-id>/` for new runs. Reuse verified transcripts and audits.
4. Read [handoff contract](references/handoff.md) and [tool capabilities](references/tools.md). Create `brief.md` and `run.json` inside the run directory. Record scope, delivery targets, source identities, artifacts, approvals, and stage states. This is a file-based workflow, not a new service.

## Dispatch

Launch the named agents below through the subagent tool. Each dispatch is a fresh single-use session. Only the producer launches agents; specialists report back without delegating.

Every prompt supplies repository/run paths, source identities, stage inputs and parent revision, exact writable stage directory, requested work, relevant approval, outputs, and completion checks. Require the shared handoff contract; do not rely on inherited conversation context.

| Stage directory | Agent | Prerequisite |
| --- | --- | --- |
| `01-media` | `post-media` | Brief and sources |
| `02-transcript` | `post-transcript` | Inventory and chosen speech track |
| `03-story` | `post-story` | Transcript and source assessment |
| `04-pacing` | `post-pacing` | Story proposal |
| `05-visual` | `post-visual` | Approved rough-cut revision |
| `06-audio` | `post-audio` | Approved rough-cut revision |
| `07-color` | `post-color` | Approved rough cut and visual plan |
| `08-accessibility` | `post-accessibility` | Composed timeline and corrected transcript |
| `09-packaging` | `post-packaging` | Stable master, captions, approved claims |
| `10-qc` | `post-qc` | Exact review exports and manifests |

## Sequence and gates

1. **Prep:** media agent inventories tracks, samples frames and diagnoses audio. Transcript follows speech-track selection. Severe noise/sync problems may require a fresh audio-agent repair task first, producing a derivative with documented time mapping.
2. **Radio edit:** story agent proposes selects/structure. Pacing agent refines the proposal, produces a candidate EDL/cut audit and assembles a rough-cut preview. Producer validates and promotes a candidate; specialists never overwrite the authoritative timeline.
3. **Rough-cut gate:** report duration before/after, actual pause/filler/retake counts, protected reading holds, uncertainty and preview path. Ask the user to watch/listen and approve story/pacing. A trim-only baseline is not a completed pacing edit. Stop until approval or requested revisions.
4. **Polish:** visual/audio agents may work independently on the approved revision. Color follows the visual plan and normally affects camera footage only. Each writes separate assets/proposals. Producer serially composes chosen treatments into a new revision using supported tools. Optional music, SFX, B-roll, zooms, J/L cuts and grading need a communication reason. Unsupported treatments remain blocked, not silently omitted.
5. **Accessibility/packaging:** accessibility supplies corrected final-timeline captions/previews. Packaging drafts chapters, titles, thumbnail concepts and standalone excerpts. Each selected derivative needs its own mapped timeline, layout, zero-based captions, mix target and render. Clip proposals can start earlier; final timings come from the stable revision.
6. **Independent QC:** a fresh QC agent inspects actual exports. Route defects to the owning specialist in a new session; regenerate affected artifacts and repeat QC. Present results with unresolved human checks.
7. **Final gate:** user approves the exact revision after end-to-end viewing/listening. Export readiness is not publication permission. Uploads, public links, installs, cloud media transfer and paid services need separate authorization.

## Coordination

- Track `pending`, `running`, `completed`, `skipped`, `blocked` stages. Skips explain why treatment is unnecessary; blocks name a missing input, capability or approval.
- Keep `run.json` as specified in the handoff contract. Approvals bind to exact revision/artifact hashes.
- Check output existence and completion evidence before accepting a stage report.
- Serialize timeline writes and renders; the current Remotion bridge has shared staging paths.
- Upstream cuts invalidate downstream captions, overlays, mix timing, chapters, clips and QC. Mark dependent artifacts stale and regenerate; reuse unaffected source analysis.
- Technical checks, sampled visual inspection, listening and human end-to-end approval are distinct. Never infer one from another.

## Existing dashboard recording trial

Locate sources/workspace from user input, not a hard-coded home directory. For the November 17 take, reuse matching `transcript.json`, `tight_v2/edl.json`, `tight_v2/cut_audit.json` and review notes after verifying source identity. `tight_v2` is unapproved.

First obtain listening feedback on pacing, closing narration/fulfilled promise, webcam obstruction and readable final slides. A baked-in webcam cannot reveal hidden screen content: request a clean supplemental capture when needed. Return fewer than two clips when appropriate. Append observed trial results to the experiment brief only after human review; leave unobserved outcomes pending.
