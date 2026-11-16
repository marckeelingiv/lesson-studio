# Repository references and content assets

## Source of truth

| Home | Owns | Reference |
| --- | --- | --- |
| DE for Fun | Data platform, technical documentation, subject roadmap and demo evidence | https://github.com/marckeelingiv/de-for-fun |
| Lesson Studio | Framework mission, production workflow, portable lesson JSON, reusable templates, recording UI and post-production code | https://github.com/marckeelingiv/lesson-studio |
| Google Drive | Media archive and shared editorial feedback | Folder URL pending; no Drive folder has been created or verified |

This guide belongs with Lesson Studio. A repository link is a navigation pointer, not a dependency: the studio must run without the subject repository. Use GitHub URLs for cross-repository documentation and record commit hashes for reproducible evidence; avoid developer-specific absolute paths. Update pending references when their destinations exist.

## Where assets go

| Asset | Authoritative location |
| --- | --- |
| Framework purpose and boundaries | Lesson Studio: `LESSON_FRAMEWORK_MISSION.md` |
| Experiment hypotheses, trial observations, continuation decisions | Lesson Studio: `experiments/`; link large trial artifacts rather than embedding them |
| Lesson series and production plans | Lesson Studio: `lessons/<subject>/README.md` and `<lesson-id>/brief.md`; DE for Fun starts at `lessons/de-for-fun/README.md` |
| Technical briefs, demo prerequisites, platform roadmap | Subject repo: https://github.com/marckeelingiv/de-for-fun |
| Narration, scenes, timings, evidence prompts | Lesson Studio: `lessons/<subject>/<lesson-id>/presenter.json` when using the presenter |
| Reusable lesson templates | Lesson Studio: `lessons/templates/` |
| Reusable graphics, styles, rendering templates | Lesson Studio: alongside the studio or renderer code that uses them; commit source and license/attribution |
| Subject-specific diagrams, screenshots, code examples | Subject repo for small, safe source/evidence files; large or sensitive captures in the media archive |
| Raw video/audio, camera tracks, capture logs and take notes | Drive media archive; local working copy outside Git |
| Transcripts, EDLs, pipeline workspace, intermediate renders | Local pipeline workspace outside tracked source; archive the selected take's workspace in Drive |
| Reviewed final video, thumbnails, caption exports | Drive media archive |
| Post text, publication date/URL, source commit, script commit, media links | Lesson Studio: `lessons/<subject>/<lesson-id>/publishing.md`; Drive may hold a linked review draft |
| Credentials, tokens, private customer information | Neither public repo nor shared media folder; use private credential storage and sanitized evidence |

Git owns small, reviewable source; Drive owns bulky production artifacts. A Google Doc can collect feedback, but accepted script changes return to versioned lesson JSON. Link instead of maintaining competing canonical copies.

## Suggested media layout

Once a Drive root is selected, use the same structure for its local working copy:

```text
<media-root>/<subject>/<lesson-id>/
  raw/<take-id>/          # original footage, separate tracks, take notes, event logs
  work/<take-id>/         # transcript, EDL, workspace, intermediate outputs
  review/                # review exports and feedback
  final/                 # approved video, captions, thumbnails
```

For the first lesson: subject `de-for-fun`, lesson ID `event-to-answer`. Give every recording a unique take ID, such as `2026-11-13-take-01`. Preserve originals; render revisions to new filenames. A synced folder alone is not a backup: keep an additional copy of irreplaceable raw footage. Check folder sharing before uploading.

Each subject brief should link its script, media folder, source commit, and final publication. A downloaded archive should retain these IDs and relevant commit hashes so the handoff survives renamed folders.

## Repository handoff status

Lesson Studio owns both experimental implementations and all lesson plans. DE for Fun's `master` contains only the data project and its existing subject-specific slides/review tools; no production-repository pointer or lesson plan was merged there. The old DE `lesson-studio` and `ai-video-pipeline` worktrees and local branches were retired on 2026-11-15, and the remote DE `lesson-studio` branch was deleted.

The original pipeline had source differences from this repository. They were preserved, not merged: a verified Git bundle of both retired branches and a source/media archive are retained outside the repositories at `/home/marc/dev/cleanup-backups/de-for-fun-2026-11-15/`. Dependency environments were excluded from the file archive. Earlier extraction backups under `/tmp/opencode/` remain untouched. Retain these backups until their unique work has been reviewed; do not mistake the old pipeline snapshot for the canonical implementation.

Standalone verification passed: 11 pipeline tests, 3 planner tests, and the renderer TypeScript check. These checks do not establish camera/capture behavior or visual quality. The Drive root remains pending; no Drive folder has been created or verified.

1. Keep `lesson_studio/`, `lessons/`, and `video_pipeline/` together, preserving their relative layout, guides, dependency locks, and ignore rules. Keep the mission, this guide, roadmap, and applicable agent instructions with them.
2. Keep lesson plans here and link technical evidence to DE for Fun. Keep that data repository free of Lesson Studio content and production instructions.
3. Maintain cross-repository references here using verified repository URLs. Keep implementation guidance with its owning experiment.
4. Select the Drive root, record its URL here, and add per-lesson media links to subject briefs. Keep generated media and environments out of Git.
5. Verify the studio runs and the pipeline instructions work independently of DE for Fun before calling extraction complete.
