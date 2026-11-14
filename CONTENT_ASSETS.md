# Repository references and content assets

## Source of truth

| Home | Owns | Reference |
| --- | --- | --- |
| DE for Fun | Data platform, technical documentation, subject roadmap, demo evidence and publication log | https://github.com/marckeelingiv/de-for-fun |
| Lesson Studio | Framework mission, production workflow, portable lesson JSON, reusable templates, recording UI and post-production code | https://github.com/marckeelingiv/lesson-studio |
| Google Drive | Media archive and shared editorial feedback | Folder URL pending; no Drive folder has been created or verified |

This guide belongs with Lesson Studio. A repository link is a navigation pointer, not a dependency: the studio must run without the subject repository. Use GitHub URLs for cross-repository documentation and record commit hashes for reproducible evidence; avoid developer-specific absolute paths. Update pending references when their destinations exist.

## Where assets go

| Asset | Authoritative location |
| --- | --- |
| Framework purpose and boundaries | Lesson Studio: `LESSON_FRAMEWORK_MISSION.md` |
| Subject lesson roadmap, technical briefs, demo prerequisites | Subject repo; DE for Fun starts at `docs/content-plan.md` |
| Narration, scenes, timings, evidence prompts | Lesson Studio: `lesson_studio/lessons/<lesson-id>.json` |
| Reusable lesson templates | Lesson Studio: `lesson_studio/templates/` when needed; not yet created |
| Reusable graphics, styles, rendering templates | Lesson Studio: alongside the studio or renderer code that uses them; commit source and license/attribution |
| Subject-specific diagrams, screenshots, code examples | Subject repo for small, safe source/evidence files; large or sensitive captures in the media archive |
| Raw video/audio, camera tracks, capture logs and take notes | Drive media archive; local working copy outside Git |
| Transcripts, EDLs, pipeline workspace, intermediate renders | Local pipeline workspace outside tracked source; archive the selected take's workspace in Drive |
| Reviewed final video, thumbnails, caption exports | Drive media archive |
| Post text, publication date/URL, source commit, script commit, media links | Subject repo's lesson brief/publication log; Drive may hold a linked review draft |
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

Lesson Studio has been extracted into its own repository with both sibling directories and production documentation. The source DE for Fun worktree is preserved. Its `docs/content-plan.md` and updated cross-references still need to be committed/published there. The Drive root remains pending; no Drive folder has been created or verified.

1. Keep `lesson_studio/` and `video_pipeline/` together, preserving their relative layout, guides, dependency locks, and ignore rules. Keep the mission, this guide, roadmap, and applicable agent instructions with them.
2. Leave DE for Fun's `docs/content-plan.md`, subject briefs, and platform code in DE for Fun. Preserve the existing work until the destination copy is verified.
3. Replace transitional relative links with verified cross-repository URLs in both repos. Replace data-repo framework instructions with a short pointer to Lesson Studio; keep the full production instructions only in Lesson Studio.
4. Select the Drive root, record its URL here, and add per-lesson media links to subject briefs. Keep generated media and environments out of Git.
5. Verify the studio runs and the pipeline instructions work independently of DE for Fun before calling extraction complete.
