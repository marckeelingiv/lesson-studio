# Scout E — reuse of post-production specialists

## Scope and conclusion

Read-only source analysis against checked-out commit `9e53d1b` (verified with `git rev-parse --short HEAD`). This report is the only authored file. No installs, builds, tests, media operations, configuration changes, commits, or delegation were performed. Existing untracked ArtCraft research was left untouched. No `graphify-out/graph.json` exists; targeted source reads were used instead.

**Recommendation:** reuse the same ten agents and the existing shared handoff. Add an explicit backend contract to dispatch/run records, and narrowly conditionalize the few profiles that currently prescribe pipeline execution. Keep the old producer pipeline-first and the new producer ArtCraft-first. Do not duplicate agents, extend the legacy EDL into a universal editor schema, or rely on a dispatch prompt to contradict an agent profile.

“ArtCraft-first” is a routing policy, not evidence that a particular editor operation works. Missing native capability must produce a blocker or an explicitly approved alternative, never an automatic legacy assembly/render fallback. This scout establishes integration seams, not ArtCraft API compatibility.

## Source-backed conflicts

| Source | Current requirement | Consequence |
| --- | --- | --- |
| `.opencode/skills/post-production/SKILL.md:19–34` | Fresh single-use sessions, shared handoff, ten named specialist stages. | Reuse dispatch identities and stage dependency graph. |
| Same, `:38–44` | Pacing emits EDL/audit/rough cut; producer composes treatments; rough-cut and final human gates. | New producer must describe its own native candidate/promotion path; gates remain unchanged. |
| Same, `:49–53` | Artifact-hash approvals, serialized writes/renders, stale dependents, distinct review states. | These are shared safety rules, not FFmpeg requirements. |
| `references/handoff.md:7–11` under the old skill | Assigned-directory ownership; no installs/uploads without approval; read `schema.py` before executable EDLs/manifests. | Schema instruction is already conditional, but needs explicit legacy scope to avoid treating native project JSON as a pipeline manifest. |
| Same, `:15–50` | Six report headings; source/edit mapping; ordinary producer-owned `run.json`; exact revision approvals and evidence. | Already a useful backend-neutral contract. Keep one canonical copy. |
| `.opencode/agents/post-media.md:12` | Materialize a one-speech-track derivative for multitrack sources because the CLI cannot select tracks. | This is a legacy limitation, not a universal prerequisite for native editor imports. |
| `.opencode/agents/post-transcript.md:11` | Otherwise use existing transcription stage. | A strict native-transcript route needs an explicit alternative, not just a producer prompt. |
| `.opencode/agents/post-story.md:13–15` | Emit `story_edl.json` using existing schema; pacing receives executable proposal. | Direct conflict with a native-project-only workflow. |
| `.opencode/agents/post-pacing.md:12` | Emit `edl.json` and assemble `rough_cut.mp4` using explicit output/transcript paths. | Strongest direct conflict; prompt-only reuse is insufficient. |
| `.opencode/agents/post-visual.md:12` | Keep assets/proposals separate from promoted EDL. | Rename to promoted timeline/project revision without weakening ownership. |
| Old `references/tools.md:7–14` | FFmpeg/Remotion limits, stage-local EDL copies, single-track workaround and shared renderer staging. | Must be labeled legacy-specific, not inherited as constraints on every backend. |
| Same, `:25–29` | FilmCraft optional, published claims not local tests; disposable-project verification required. | Keep this true for the old producer. New skill may be native-first but cannot convert published claims into tested support. |

The other five profiles are already effectively backend-neutral: audio (`:10–16`), color (`:10–15`), accessibility (`:10–15`), packaging (`:10–16`), QC (`:10–16`). They need exact backend inputs in dispatch, not duplicated profiles or forced native project writes.

## Why not make native projects look like EDLs?

`video_pipeline/src/schema.py:113–124` describes one `source_path`, optional synchronized `camera_path`, kept segments, fixed graphic cues and caption enablement. It has no general tracks, clip placement, effects graph, source stream selection or independently timed audio. The Remotion manifest is a props payload (`:135–146`), not a general editor timeline.

`src/assemble.py:33–66` cuts matching video/audio ranges and concatenates them; normalization defaults to −16 LUFS/−1.5 dBTP (`:57–59`). `src/cli.py:145–181` validates the EDL/transcript, invokes assembly and can rewrite the input EDL for a camera override (`:167–169`). These semantics are not a harmless interchange layer.

Also, `src/planner.py:77–94` sorts and clamps kept intervals: sending intentionally reordered story selections through `sanitize_edl` would change their order. Preserve ordered piecewise mappings independently; do not use legacy sanitization to validate a native edit.

`src/render.py:29–39,59–63` copies into and deletes from shared `renderer/public`. Native routing should not invoke this as an invisible last step.

## Minimal exact change proposals (not applied)

### 1. Keep one shared handoff; add a small backend paragraph

File: `.opencode/skills/post-production/references/handoff.md`.

After its introductory paragraph, add an explicit rule equivalent to:

> Dispatch identifies `backend` (`pipeline` or `artcraft`) and an exact `backend_reference` path, parent revision, stage inputs, allowed operations and expected artifact types. If omitted, preserve existing `pipeline` behavior. Shared ownership, source mapping, reports, review gates and approvals apply to both. Backend-specific EDL, project, transcript and export requirements apply only to the selected route. Missing/conflicting backend instructions block execution; do not silently switch backends. Inspect only the installed/versioned capabilities actually needed.

Clarify line 11 to read the pipeline schema **when emitting pipeline executable EDLs or Remotion manifests**; native artifacts follow the supplied native reference.

Extend the existing ordinary `run.json` description, not the pipeline Python models:

- Add `backend`, `backend_reference` and version/capability evidence paths.
- For each revision identify artifact kind (legacy EDL or native project), path/hash, parent, source-to-edit map, and actual exports/hashes. The existing `timeline path` can point to a native project; do not create a second authoritative timeline field.
- Record any approved backend change and newly invalidated dependents. Existing approvals do not carry across changed artifacts.

These are file-based conventions, not a new schema framework, runner, service, plugin registry or Python interface. Preserve all six report headings and existing source/timebase validation.

### 2. Scope capabilities without moving the canonical files

File: `.opencode/skills/post-production/references/tools.md`.

Add one sentence that “Existing pipeline” restrictions apply to `backend=pipeline`; ArtCraft dispatch must supply its separate verified native capability reference. FFmpeg/ffprobe may remain authorized measurement/probing helpers where appropriate; that is not permission to switch editing/assembly/render backends.

Leave the optional FilmCraft evaluation and all legacy caveats intact for the existing producer. No relocation of `handoff.md`: all ten profiles and current tests intentionally point there.

### 3. Conditionalize only five agent profiles

All existing handoff links can remain unchanged; the shared handoff makes the supplied backend reference mandatory for native work.

| File | Narrow proposed edit |
| --- | --- |
| `.opencode/agents/post-media.md` | Scope step 3's one-track editing derivative to the pipeline route. Native route records selected source stream IDs, imports/routing and sync evidence; create a derivative only if native support actually requires one and it is authorized. Preserve originals and explicit transcript/source mapping in both routes. |
| `.opencode/agents/post-transcript.md` | Step 2 uses the selected backend's verified transcription/import route. Pipeline remains the default. Preserve/reuse machine evidence and word timing; if native output lacks required granularity or an export interface, report a blocker or request an approved analysis helper rather than inventing word timestamps. |
| `.opencode/agents/post-story.md` | Step 4 emits the backend-specific candidate. Pipeline retains `story_edl.json`; native route supplies ordered source selections, rationale and piecewise map plus verified native project/proposal artifacts required by the native reference. No legacy EDL is required for native mode. “Executable proposal” means verified native operations/project or an explicit blocked implementation, not an unvalidated JSON claim. |
| `.opencode/agents/post-pacing.md` | Branch step 3: pipeline keeps stage-local `edl.json` and current assembly safeguards; native mode edits an assigned project copy and exports a native rough-cut preview through verified operations. Both require `cut_audit.json`, mapping, source-bound/timebase checks, actual preview and existing metrics/listening checks. Native mode must not call pipeline `assemble`/Remotion as an unapproved fallback. |
| `.opencode/agents/post-visual.md` | Replace “promoted EDL” with “promoted timeline/project revision”; supported cues/compositions are selected-backend-specific. No direct authoritative project mutation. |

No content change is necessary to `post-audio.md`, `post-color.md`, `post-accessibility.md`, `post-packaging.md`, or `post-qc.md` for first integration. Shared instructions give them backend routing; their present completion evidence remains required. If a native implementation cannot satisfy a completion condition, block it rather than dilute the condition.

### 4. New producer skill and one native execution reference

New `.opencode/skills/post-production-artcraft/SKILL.md` should:

- Link the canonical handoff, and supply `backend=artcraft` plus its native reference on every fresh dispatch.
- Reuse the same ten stages and specialists. No “ArtCraft variants” of the agents.
- Use a unique run under `video_pipeline/workspace/<source-stem>/post-production/<unique-run-id>/`, preserving established artifact placement despite the directory name.
- Own native project revisions and serialize project writes/exports. Parallel audio/visual analysis or independent assets are fine; concurrent mutation of one project is not.
- Send a stage-local project copy/snapshot, not the approved authoritative file. Producer alone promotes accepted results and records hashes.
- Retain rough-cut approval, actual representative cut checks, independent fresh QC, exact-revision final viewing/listening, dependency invalidation and separate publication permission.
- Distinguish native editing/rendering from optional approved analysis helpers. Never auto-install, upload, configure credentials/system settings, or fall back to pipeline assembly.

Proposed single companion path: `.opencode/skills/post-production-artcraft/references/backend.md`. Keep actual app/version, verified operations, transcript/export formats, project copy/save/reopen semantics, time units, track selection, output paths and capability blockers here. Reference the other scouts' verified findings rather than guessing commands/API schemas. This is documentation of a concrete backend, not a generic adapter abstraction.

If verification requires writes outside the assigned stage/workspace (application cache, database, global project state), document exact scope and obtain authorization or mark blocked; do not silently waive workspace ownership.

No change to the old `.opencode/skills/post-production/SKILL.md` is necessary: its omitted backend remains pipeline. An explicit `backend=pipeline` in old dispatch instructions is optional clarity, not required infrastructure.

## Shared vs backend-specific contracts

| Shared, retain once | Backend-specific, describe in execution reference |
| --- | --- |
| Audience/promise, source identity, rights/privacy, preserved originals | Media import/stream routing, proxy/repair necessities |
| Stage ownership, fresh sessions, producer-only promotion | EDL vs native project format, save/copy/reopen mechanics |
| Ordered source/edit maps, rational timebase evidence, audits | Native frame/seconds/tick conversion and checked operation syntax |
| Report headings, metrics, skipped/blocked reasons | Transcript generation/import/export and artifact format |
| Hash-bound revisions/approvals, stale downstream artifacts | Cut/effect/caption/mix implementation and output recipes |
| Actual previews, measured encoded targets, listening uncertainties | App capabilities, optional measurement helpers, proven limitations |
| Independent QC, rough-cut/final gates, no implicit publication | Export jobs/status, app-specific serialization and reproducibility evidence |

Native revision identity must cover the state actually reopened/exported, not merely a session label or screenshot. Where a project references external assets, record their identities too; the project-file hash alone cannot bind changing dependencies. A command success or project save does not prove preview/export quality.

## Tests: minimum useful extension

Existing test coverage was read, not executed:

- `video_pipeline/tests/test_post_production_skill.py:13–29` checks ten routes, subagent frontmatter, the old shared handoff link, `report.md` and “Done when”.
- Same `:31–42` checks Markdown links under the old skill and two guides only.
- Same `:44–58` checks selected old-producer safety/capability phrases.
- `video_pipeline/tests/test_pipeline.py` covers transcript/heuristic/remap/schema/cursor/FCPXML behavior and two FFmpeg smoke tests (`:34–491`). It has no native integration tests.
- `video_pipeline/src/test_planner.py:12–35` mocks OpenCode planner output/errors, not native editor execution.

Extend the existing static skill test file; no new testing framework:

1. Run the dispatch-table/profile checks for both producer skills; assert both select the same ten agents and unique stage names. Preserve old profile/handoff assertions.
2. Add the new skill's maintained Markdown docs to link checks. Exclude `research/` snapshots from this documentation contract: research may contain upstream-relative links, and it is not executable operating guidance.
3. Assert canonical handoff documents default pipeline behavior, explicit native backend reference, no silent fallback, unchanged report headings/ownership and hash-bound approvals. Assert new skill retains both human gates, stale invalidation and independent QC.
4. Assert story/pacing profiles now contain both routes: legacy filenames remain for pipeline; native project/preview handling does not mandate legacy EDLs. Assert media/transcript branch scope. These are guardrails on instructions, not behavioral proof.
5. Validate any published example `run.json` as ordinary JSON with backend/revision/source-map fields. Do not add a validator solely to test prose.

Later, only with separately approved native execution, verify a disposable local project: selected tracks, two exact cuts, source/edit mapping, save/reopen, native preview/export, caption timing and encoded audio. Inspect rendered frames/listen and record actual coverage. Test unsupported-capability blocking and absent authorization without fallback. Test approval/staleness discipline on a changed revision. Static tests cannot establish any of these outcomes.

Suggested check after implementation: `uv run --project video_pipeline python -m unittest discover -s video_pipeline/tests -p "test_post_production_skill.py" -v`. Do not run the FFmpeg smoke suite under this scout's no-media scope. Full repository verification belongs to the implementing session under its own authorization.

## Documentation points and bounded file list

Required shared edits: old `references/handoff.md`, old `references/tools.md`; the five profiles listed above; `video_pipeline/tests/test_post_production_skill.py`. New operational docs: ArtCraft `SKILL.md` and `references/backend.md`.

Two documentation updates when the workflow is adopted:

- `video_pipeline/README.md:9–14`: distinguish existing pipeline producer from the new native-first producer and link the latter. Do not rewrite pipeline setup/CLI artifacts as ArtCraft features.
- `experiments/post-production-video-editing.md:31–44`: append a dated decision describing the new opt-in native-first experiment and preserved legacy route. Its current historical decision says pipeline backend and optional FilmCraft; do not silently rewrite history. Keep unobserved trial outcomes pending.

No changes needed to mission, asset guide, either `AGENTS.md`, Python pipeline code/schema, dependencies, renderer, desktop configuration or generated media. `LESSON_FRAMEWORK_MISSION.md:18–25,45–54` explicitly treats implementations as replaceable experiments; `CONTENT_ASSETS.md:25–31,45` already locates production artifacts outside tracked source and requires preserved originals/revisions. Existing rules therefore support this seam without a new architecture.
