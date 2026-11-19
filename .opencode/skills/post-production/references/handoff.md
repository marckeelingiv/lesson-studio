# Stage handoff contract

All specialists read this first. The producer supplies repository/run/input paths and an exact writable stage directory. Missing inputs or ownership conflicts are blockers.

## Ownership

- Preserve sources, previous revisions and other stages' artifacts. Write only in the assigned new stage directory. Request producer integration for tracked-source changes.
- Read repository and `video_pipeline/AGENTS.md`. Python runs only through `uv run --project video_pipeline python ...` from the repository root.
- Reuse installed tools. Ask before dependency installation, external uploads, paid processing, credential configuration or editor/system changes.
- Work once and report back; only the producer dispatches fresh follow-up agents.
- Read `video_pipeline/src/schema.py` and relevant implementation before emitting executable EDLs/manifests. Unsupported operations need an explicit alternative or blocker.

## Required report

Write `report.md` in your stage directory with these headings:

1. **Status:** completed / skipped / blocked, with reason.
2. **Inputs:** exact paths, hashes or producer-provided identities, parent revision, tool versions and approval used.
3. **Work performed:** decisions and commands/settings; proposals vs applied edits. Record processing time separately from known human review time.
4. **Outputs:** paths, durations/timebases and reproduction instructions.
5. **Checks:** actual results and evidence paths; sampled vs continuous visual inspection, measurements vs listening, machine vs human review.
6. **Open issues:** timestamped findings, uncertainty, missing pickups/assets and human decisions.

Return status, output/report paths, before/after metrics, blockers and next dependency. A report alone does not complete the stage.

## Source and timeline identity

- Label original-source seconds, edited seconds, or frame indices plus rational frame rate. Detect VFR before assuming constant-rate math.
- Keep source-to-edit mapping for every retained interval. Reordering needs piecewise mappings, not a single offset. Derivative clips identify parent-master intervals too.
- Validate finite, in-bounds, positive-length ranges, unique IDs and timebase precision. Document deliberate overlaps/repeats/reordering.
- Cut audits identify removed source ranges, category, reason, neighboring speech, confidence, protected holds and manual-review status. Do not double-count overlapping removed seconds.
- Corrections retain original machine text/timing evidence; never invent unclear or missing speech.

## Producer run record

`run.json` is an ordinary JSON object with:

- `run_id`, `brief_path`, `sources` (path, SHA-256, size, timebase/track-selection evidence).
- `stages` keyed by stage directory: `status`, `input_revision`, `report`, `outputs`, and `reason` for skips/blocks.
- `revisions`: ID, parent, timeline path, source-to-edit map, output paths/hashes and stale dependents.
- `approvals`: gate, exact revision/artifact hashes, user decision and date.
- `delivery_targets`: layout/aspect ratio, codecs, caption policy and selected loudness/peak targets.

Producer owns this record and promoted timeline. Agents own stage reports.

## Evidence and release

Inspect actual rendered frames for crop, overlays, captions and reading holds. Non-silence/levels do not prove intelligibility, filler identity, natural cuts or lip sync. If listening is unavailable, leave those checks pending for a human.

Distinguish technical pass, sampled review and human end-to-end approval. Sampled privacy checks never clear unsampled footage. Retain synthetic/local/snapshot caveats and media rights records through reframing and excerpting.
