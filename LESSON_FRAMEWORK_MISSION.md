# Mission: a reusable build-in-public lesson workflow

## Why this exists

Help Marc make his engineering skill and judgment visible through clear, evidence-backed lessons. Project Sandbox is the first subject: follow synthetic business activity through data ingestion, analytical models, defined metrics, and AI-assisted exploration. The larger deliverable is a reusable creation process for this and future lessons.

The intended audience includes engineers, hiring managers, and career contacts. Show the reasoning behind decisions and the working evidence that supports them. Connect business questions to engineering work. Label synthetic data, local deployment, and limitations explicitly; do not imply production adoption or measured customer impact.

## Requested experience

- A private presenter view with the lesson rundown, narration notes, evidence prompts, timing, and source controls.
- A separate audience view suitable for recording, with Marc's face in the bottom-right and no private notes or controls.
- Present slides, code, VS Code/native apps, websites, and localhost services. Use browser window/tab capture for native apps and sites that refuse embedding. The presenter operates captured apps in their original windows.
- Reusable lesson definitions independent of the application. The first lesson is the 90–120-second “From event to answer” walkthrough.
- A repeatable recording and editing handoff to `video_pipeline/README.md`, preserving source footage and making editorial review practical.
- Keep the studio and video pipeline self-contained so they can move together into a separate repository later.

## End-to-end process

1. Pick a business question and verify the actual result and supporting metric/model.
2. Plan the lesson around **problem → decision → evidence → tradeoff**. Identify the visible evidence for every claim.
3. Rehearse the scenes and sources. Keep important content clear of the camera and bottom caption band.
4. Record only the audience stage with camera and microphone. Leave one-second pauses between sections. Restart full sentences on mistakes. Preserve raw video and take notes.
5. Process the source recording through the existing video pipeline. Prefer its documented OpenCode integration when model-assisted planning is desired.
6. Review cuts, captions, screen readability, face framing, and graphics against the actual video. The transcript-only planner cannot verify screen continuity.
7. Revise the edit, publish deliberately, and retain the lesson, source, take notes, output, post text, and URL as evidence for future lessons.

## Initial lesson series

| Lesson | What viewers should assess |
| --- | --- |
| From event to answer | End-to-end delivery and clear communication |
| Why DuckDB; when to choose something else | Technical judgment and cost awareness |
| Malformed or duplicate data | Reliability and correctness, using observed behavior |
| Defined metrics through MCP | Practical AI integration and its boundaries |
| An agent change reviewed and verified | Engineering with agents |
| An architectural rule enforced automatically | Repeatable delivery and platform leadership |

These are demonstrations to prepare, not claims that every capability already exists. A recurring theme is turning engineering decisions into automated checks. Prioritize one clear demo and three strong posts before adding platform breadth.

## Current implementation and boundaries

`lesson_studio/` contains a buildless HTML/CSS/JavaScript studio, a loopback-only Node standard-library server, portable lesson JSON, browser capture/recording, and recording notes. `lesson_studio/README.md` is the operational guide. `video_pipeline/` remains the editing/rendering workflow. No new hosted service, user account, data-stack dependency, or browser-to-shell API is required.

The studio cannot bypass screen-capture permission pickers or website iframe restrictions. It does not remotely control VS Code. The presenter console must stay open to own source streams. Browser recording is intended for short lessons; OBS is an alternative for longer/durable recordings. Take notes are not the pipeline's edit-decision-list format and are not automatically ingested. Actual camera, microphone, capture permissions, and output quality require a recording rehearsal.

Future work should close observed gaps in this workflow. Automatic scene-aware editing, richer authoring, direct pipeline ingestion of markers, and publication automation are not promised by the current implementation.

## Worktree provenance and portability

At Marc's request, work began in a Herdr worktree named `lesson-studio`, based on `ai-video-pipeline`. The source worktree had modified `.gitignore`, `AGENTS.md`, and `Makefile`, plus an untracked `video_pipeline/` tree. All 29 modified/untracked source files were copied and byte-verified before studio work. Ignored environments, dependencies, and generated media were excluded; the original worktree was left untouched.

Keep `lesson_studio/` and `video_pipeline/` as sibling directories using relative references. Avoid hardcoded developer/worktree paths and imports from Project Sandbox's data application. Preserve dependency locks and pipeline instructions; do not commit recordings, secrets, environments, or generated rendering workspaces. The future repository should carry this mission document, the studio guide, pipeline guide, and applicable agent instructions.

## Working agreement for future agents

Read this document, `lesson_studio/README.md`, and `video_pipeline/AGENTS.md` before changing the lesson workflow. Preserve the separation between audience content and presenter-only material. Distinguish implemented behavior, tested behavior, and planned work. Update this mission when Marc changes the objective; update operational instructions when behavior changes. Never claim that a rendered video was visually reviewed unless it actually was.
