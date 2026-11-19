# ArtCraft handoff extension

Read the [shared stage handoff](../../post-production/references/handoff.md) first. Its ownership, six report headings, source identity/mapping, run record and evidence rules remain authoritative. This extension applies only to explicit `backend=artcraft`; omitted backend retains the shared pipeline default. Missing/conflicting backend instructions block work rather than select a fallback.

## Ownership and native artifacts

- Producer alone mutates native projects/timelines, imports into the project, saves, integrates proposals and starts exports. Specialists write only assigned stage-local proposals, independently generated assets and reports; supplied project snapshots are read-only.
- Producer-controlled native projects, capability samples, revisions, evidence and exports stay under the assigned run workspace. Identify any tool cache/database writes outside it and obtain authorization before proceeding. Preserve originals and prior revisions.
- Native delivery includes the editable project, selected sequences, source-to-edit map and relink/dependency manifest, not just flattened video. Record original/current media paths, stream IDs, hashes, size, proxy/derivative provenance and mapping, external assets, fonts/plugins/models/versions needed to reopen or render, and redistribution/licensing constraints. A dependency not bundled must have an explicit relink requirement.
- Each revision is immutable: record parent, native project path/hash, dependency-manifest path/hash and individual external asset hashes, map, exports/hashes and review evidence. Serially write a new revision for changes. Project hashes alone do not bind mutable linked media. Mark affected dependents and approvals stale on any changed input; retain unaffected source analysis.

## Capability gate: disposable sample

Before production mutation, producer verifies the approved installed runtime on a disposable project and short, identified sample in the run workspace. Consult [FilmCraft API guidance](filmcraft-api.md) for discovery and operations, not assumed syntax. Optional [EffectCraft](effectcraft-api.md) or [SoundCraft](soundcraft-api.md) verification is required only when selected for a demonstrated need.

Record each check as pass, blocked or not applicable with evidence and reason. Source-backed means documented in the cited upstream version; runtime-tested means actually executed on the recorded local build. Neither label implies editorial approval.

1. **Discover:** capture executable path, actual versions/builds, help, transport/session mode, MCP wrapper schemas where available, command catalog including disabled commands, relevant parameter documentation and enabled/precondition state for the actual project. Engine catalog `params` may be documentation strings, not strict JSON Schemas; MCP wrapper validation does not validate every engine parameter. Obtain actual clip/track/sequence IDs from inspection. Missing executable blocks; request permission rather than installing or downloading models.
2. **Cut/map:** import selected media streams and perform two known-boundary cuts with positive, in-bounds ranges. Compare inspected timeline and exported boundaries with expected frames/audio, duration and ordered source mapping; check speech and screen continuity around both cuts.
3. **Transcript:** verify reuse/import of an existing source-matched transcript, including text and timing after native serialization. If reuse/import is unavailable, verify native STT only when authorized; record engine/model/version, selected speech stream and timing granularity. Missing word timings stay missing. Preserve original machine evidence and corrections. If the chosen route cannot supply required evidence, block or request an approved analysis helper.
4. **Treatments:** when requested, actually apply a representative zoom, caption and audio treatment using each selected route; inspect its exported frames and listen to the audio. Verify caption timing/text, legibility, framing/occlusion, transition continuity and chosen audio target. Mark unrequested treatments not applicable, not tested. Unverified requested work blocks that scope.
5. **Persist/relink:** explicitly save to a new native checkpoint, reopen it in a fresh compatible session and inspect sequences, cuts, tracks, transcript/captions and media mappings. Confirm required media resolve; capture migration/missing-media results. Project existence alone does not pass.
6. **Export/inspect:** resolve the intended sequence/range, duration, frame count, dimensions, codec, caption policy and audio settings; export and await the actual matching job/result. Capture raw responses, warnings, `offlineMedia` and exact returned paths/job IDs. Reject required missing/offline media or unexplained duration/range discrepancies, even if export reports success. Verify actual output existence and decode, inspect representative rendered frames including both cut boundaries and requested treatments, and listen for speech, cut clicks, sync and treatment behavior. Measure encoded duration, loudness/peaks and other selected targets; leave unavailable listening checks pending.

**Minimum acceptance:** all required checks above pass with saved/reopened editable project, complete media mapping, two verified cut boundaries and a decodable, frame-inspected/listened-to sample export. Any missing evidence blocks production for that capability; authorization may narrow the requested scope or change backend, but is not a substitute for passing a technical check. Record the capability envelope and rerun affected checks after runtime, dependency or operation changes.

## Timing and editorial proposals

- Reuse existing transcripts only after verifying source hash, selected speech track, offsets and derivative mapping. Record native ticks-per-second, rational frame rate, source timestamps/PTS, origin and offset, and the explicit conversion/rounding rule from transcript seconds to ticks/frames. Measure boundary error in the disposable test. Detect VFR; use actual presentation timing or a verified derivative map rather than assuming constant-rate arithmetic.
- Retain ordered piecewise source-to-edit maps for every kept interval, reorder, repeat, overlap and derivative excerpt. Do not run native decisions through a pipeline sanitizer that can reorder selections.
- Story/pacing deliver proposals, rationale, protected ranges and `cut_audit.json`; producer records applied results separately. Audit removed ranges/category/reason/confidence, neighboring speech, protected screen/reading holds and manual-review status without double-counting overlapping seconds. Preserve semantic qualifications, evidence, intentional pauses and readable final slides. A baked-in webcam cannot reveal covered content; request a supplemental capture where necessary.
- Metrics state method, input revision and evidence. Distinguish detected candidates, proposed removals, applied cuts, measured before/after counts and human listening findings. No invented filler counts, word timings, click telemetry or retention gains.

## Execution evidence

Keep sanitized raw MCP/CLI requests and responses, inspections and export settings/results in run-local evidence files. Retain exact returned paths, job IDs/status/results, warnings and `offlineMedia`, including failures and partial changes; never log authentication secrets. Follow installed command docs and actual enabled prerequisites.

Use explicit checkpoints: session state may be unsaved, batches may partially apply, one-shot invocations may lose edits, and locks do not replace single-writer ownership. After transport ambiguity inspect state before retrying a non-idempotent mutation. Long-running export success requires the actual terminal job result and returned artifacts, not a queued-job acknowledgement. Runtime-specific details live in the API references above.

Existing approved measurement/probing helpers are allowed for analysis only. Native editing/export limitations require a user decision about scope, manual work or backend change; pipeline assembly/rendering is never a silent fallback. Record any approved change and invalidate its affected artifacts and approvals.

## Producer run record extension

Extend the shared ordinary `run.json` object; this is a file convention, not an engine schema or new service:

- `backend: "artcraft"` and `backend_reference`: this handoff's resolved path.
- `capabilities`: tool paths/versions, session mode, source-backed reference versions, runtime evidence/report paths, smoke-test results and the verified operation envelope; unresolved limitations remain explicit.
- `revisions`: retain shared fields; `timeline_path` identifies the native project. Add artifact kind, project SHA-256, dependency-manifest path/hash, external dependency identities/hashes, selected sequence IDs and timebase/conversion evidence. Record actual output paths/hashes, export settings, jobs/results and evidence paths.
- `stages`: retain shared status/report/output fields; distinguish proposals, integrated revisions and verified exports. Record skipped treatments with rationale and blocked work with missing capability/input/authorization.
- `approvals`: retain gate/revision/artifact hashes, user decision/date; include dependency-manifest identity. An explicit rough-cut deferral records its editorial-continuation scope and outstanding gate, never approval. Changed dependencies invalidate affected approvals.

## Review and completion

Use the shared six-heading report without duplication. Add backend evidence under Inputs, Work performed, Outputs and Checks; return actual artifact/report paths, measured metrics, limitations and next dependency.

Producer presents the rough-cut export and actual audit for human viewing/listening. Stop for approval/revisions unless the user explicitly defers that gate for bounded editorial continuation; distinguish authorized continuation from approved pacing.

### Final editable-delivery verification

Before delivery, the producer reopens the **exact final saved production checkpoint** in a fresh compatible session, not merely the disposable capability sample or an unsaved working session. For every delivered project and selected master/derivative sequence:

1. Verify all required dependencies resolve with no missing/offline media. Inspect the reopened sequences, tracks, cut boundaries, transcript/captions, applied visual/audio/color treatments and source-to-edit/derivative maps against the intended final revision.
2. Record session/runtime identity, exact checkpoint path and SHA-256, dependency-manifest path/hash, individual dependency hashes, selected sequence IDs, inspection results, warnings and evidence paths in the revision record. Bind reopen evidence to these identities; a successful sample, save, export or screenshot alone is insufficient.
3. Keep inspection pure read: no saves, autosaves, migrations, relinks or other project/dependency mutations. If a repair or migration is needed, the producer alone writes a new immutable revision, updates identities and repeats verification; never overwrite the checkpoint under review.

A fresh independent QC agent verifies the reopen evidence, exact project/manifest/dependency hashes and exports by pure read inspection; QC does not repair, save, migrate or relink the project. Missing evidence, hash mismatch, unresolved dependencies or lost timeline state blocks editable delivery. Defects return to the producer as findings.

Repeat producer reopen verification and independent QC after every affected revision or dependency change; stale evidence cannot clear the new deliverable. Defects trigger new specialist proposals, producer revisions and repeated affected checks. Final human approval binds to exact hashes after end-to-end viewing/listening; unresolved rough-cut deferral and required QC checks remain outstanding. Technical pass, sampled review, continuous review and human approval are separate states. Publication/upload permission is a separate decision.
