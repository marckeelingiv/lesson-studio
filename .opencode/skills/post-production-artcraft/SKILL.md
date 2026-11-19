---
name: Post Production ArtCraft
description: Coordinate the existing post-production specialists through FilmCraft when the user chooses the ArtCraft-first workflow; verify native editing and export capabilities before production.
---

# ArtCraft-first producer

Make engineering judgment clear in a reviewable, editable deliverable. This opt-in producer uses FilmCraft as the primary editor; the existing `@post-production` skill and pipeline default remain unchanged. Source-backed API documentation is not local runtime verification.

## Start

1. Read repository `AGENTS.md`, `LESSON_FRAMEWORK_MISSION.md`, `CONTENT_ASSETS.md`, `experiments/post-production-video-editing.md`, and `video_pipeline/AGENTS.md` and `README.md`. Resolve repository paths from the active project.
2. Confirm sources, audience/promise, deliverables, existing revision and approval, and authorized runtime scope. Propose YouTube 16:9 plus up to two LinkedIn excerpts only as useful defaults.
3. Preserve originals and prior work. Create a unique run under `video_pipeline/workspace/<source-stem>/post-production/<unique-run-id>/`; reuse source-verified transcripts and audits. Read the [shared handoff](../post-production/references/handoff.md) and [ArtCraft extension](references/handoff.md). Create `brief.md` and producer-owned `run.json`.
4. **Capability gate:** read [FilmCraft API guidance](references/filmcraft-api.md), then satisfy the extension's disposable-sample acceptance before production mutation. Missing executable, unverified required operation, or unauthorized setup blocks native execution. If software is missing, offer the [pinned download-only setup command](references/setup.md): preview first, download only when authorized; installation and runtime checks remain separate. Ask before installations, model downloads, credentials, uploads, paid services or editor/system changes.

## Dispatch

Only the producer dispatches the existing named specialists, each in a fresh single-use subagent session. Specialists report back without delegating. Every prompt includes:

- `backend=artcraft`, exact repository/run paths, and both the shared and ArtCraft handoff paths above;
- exact source paths/identities and selected streams, input artifacts/hashes, parent revision/project snapshot and source-to-edit map;
- owner, exact writable stage directory, allowed operations, requested work, approval or explicit deferral, exact output paths/types, and completion checks.

The producer is the **single project writer** and owns native mutations, integration, saves and exports. Specialists receive read-only snapshots and supply stage-local proposals, independent assets and evidence only. A proposal is not an applied edit or verified preview.

| Stage directory | Agent | Prerequisite |
| --- | --- | --- |
| `01-media` | `post-media` | Brief and sources |
| `02-transcript` | `post-transcript` | Inventory and chosen speech track |
| `03-story` | `post-story` | Transcript and source assessment |
| `04-pacing` | `post-pacing` | Story proposal |
| `05-visual` | `post-visual` | Approved rough-cut revision or recorded explicit deferral covering assigned work (step 3) |
| `06-audio` | `post-audio` | Approved rough-cut revision or recorded explicit deferral covering assigned work (step 3) |
| `07-color` | `post-color` | Approved rough cut or recorded explicit deferral covering assigned work (step 3), and approved visual plan |
| `08-accessibility` | `post-accessibility` | Composed timeline and corrected transcript |
| `09-packaging` | `post-packaging` | Stable master, captions, approved claims |
| `10-qc` | `post-qc` | Exact review exports and manifests |

## Sequence and gates

1. **Prep:** media inventories streams, sync, VFR, rights/privacy and screen legibility. Transcript reuses verified evidence; otherwise propose the verified native transcription route. Producer performs native import/STT and records actual time conversion. Repair derivatives need explicit source mapping; a pipeline single-track workaround is not an automatic native requirement.
2. **Radio edit:** story proposes ordered selects; pacing supplies cut proposals, `cut_audit.json`, protected holds and piecewise mapping. Read the [timeline/treatment contract](references/timeline-api.md) before native placement, cuts or effects. Producer applies accepted operations to a new native revision and exports the rough-cut preview. Protect meaningful hesitations, reading/thinking time, UI transitions and evidence that supports claims; silence alone is not a cut instruction. Use actual event logs for click telemetry; observed screen actions are visual evidence, not inferred click events.
3. **Rough-cut gate:** present actual before/after durations and measured pause/filler/retake counts with method, removed ranges, protected holds, uncertainties and preview path/hash. Label proposed/unmeasured changes separately; trim-only work is not completed pacing. Ask for viewing/listening and approval or revisions. The user may explicitly defer this gate for **editorial continuation only**: record the decision, exact revision and allowed scope; it is not approval or release clearance. Polish prerequisites in the table may use only that explicitly authorized scope.
4. **Polish:** visual/audio analysis may run independently against the same immutable parent. Producer serially integrates accepted proposals into new native revisions. Use FilmCraft first. Read [EffectCraft guidance](references/effectcraft-api.md) only for a demonstrated visual need FilmCraft cannot suitably meet; read [SoundCraft guidance](references/soundcraft-api.md) only for a demonstrated audio need. Verify any selected optional app on the disposable sample first. Music, SFX, B-roll, zooms, J/L cuts and grading need a communication reason, not a checklist. Requested unsupported treatments remain blocked or become an explicit user-approved scope change.
5. **Accessibility/packaging:** producer applies corrected final-timeline captions; inspect actual caption frames, safe areas, contrast and reading time. Packaging supplies chapters, supported claims and optional standalone excerpts. Each selected derivative gets its own mapped native sequence/project, layout, zero-based captions, mix target and export.
6. **Final checkpoint and independent QC:** producer reopens the exact final saved production checkpoint in a fresh compatible session and completes the extension's [final editable-delivery verification](references/handoff.md#final-editable-delivery-verification); disposable-sample persistence does not satisfy this gate. Dispatch a fresh `post-qc` against exact exports, project/dependency hashes and reopen evidence. QC independently verifies that evidence and those exact hashes using pure read inspection, without project mutation. Separate decode/metrics, sampled frames, listening and continuous review. Route defects to the owner in fresh sessions, then producer revises and re-exports. Invalidate downstream captions, overlays, mix timing, chapters, clips, QC and approvals whenever their dependencies change; repeat affected checks, including final-checkpoint reopen verification.
7. **Final gate:** deliver the verified native editable project **and** relink/dependency manifest alongside exports, captions and reports only after final-checkpoint verification and independent QC pass. User final approval requires end-to-end viewing/listening of the exact revision/export hashes after independent QC; explicitly deferred rough-cut review remains outstanding until resolved. Export readiness is not publication permission: uploading, public links or publication require separate authorization.

## Coordination

- Use shared stage/report/run rules; track `pending`, `running`, `completed`, `skipped`, `blocked` with reasons and evidence. Accept outputs only after checking their existence and completion evidence.
- Serialize project writes and exports. Checkpoint to new immutable revisions; bind identity to project and external asset hashes, not session labels or screenshots. Inspect actual state after ambiguous errors before replaying mutations.
- Approved existing ffprobe/FFmpeg or pipeline measurement helpers may measure/analyze media; they do not authorize pipeline assembly, Remotion rendering or an editing fallback. Offer blocked capability, manual route or backend change for the user to decide; never silently fall back.
- Capture raw tool evidence, warnings, missing/offline media, returned paths and export jobs under the run. Never equate command success, saved project, source documentation or sampled inspection with reviewed output quality.
