# DE for Fun content plan

Canonical lesson plan: this file in Lesson Studio. Subject implementation and technical evidence live in [marckeelingiv/de-for-fun](https://github.com/marckeelingiv/de-for-fun). Keep lesson plans here and link back to the subject rather than copying its technical documentation.

## Purpose

Make engineering judgment visible to engineers, hiring managers, and career contacts through evidence-backed demonstrations of Project Sandbox. Connect business questions to engineering work. Label synthetic data, local deployment, and limitations; this is not evidence of production adoption or measured customer impact.

## Planned series

| Lesson | What viewers should assess |
| --- | --- |
| From event to answer | End-to-end delivery and clear communication |
| Why DuckDB; when to choose something else | Technical judgment and cost awareness |
| Malformed or duplicate data | Reliability and correctness, using observed behavior |
| Defined metrics through MCP | Practical AI integration and its boundaries |
| An agent change reviewed and verified | Engineering with agents |
| An architectural rule enforced automatically | Repeatable delivery and platform leadership |

These are demonstrations to prepare, not claims that every capability exists. Prioritize one clear demo and three strong posts before adding platform breadth. A recurring theme is turning engineering decisions into automated checks.

## Production handoff

Use the separate [Lesson Studio repository](https://github.com/marckeelingiv/lesson-studio) for reusable presentation and post-production experiments. Its mission is `LESSON_FRAMEWORK_MISSION.md`, experiment briefs are in `experiments/`, and repository/storage ownership is in `CONTENT_ASSETS.md`. Read that repository's instructions before changing production tools. Presentation and post-production are independent options, not a required sequence.

The first script is [event-to-answer.json in Lesson Studio](https://github.com/marckeelingiv/lesson-studio/blob/main/lesson_studio/lessons/event-to-answer.json): six scenes, 115 seconds, with narration and evidence prompts. The other five topics are outlines, not completed scripts. Studio and pipeline source are maintained only in that repository.

Before recording each lesson:

1. Choose one business question and verify its actual result.
2. Record the DE for Fun commit, demo commands/prerequisites, model/metric paths, and known limitations in a lesson-specific brief here under `docs/`.
3. Link the matching Lesson Studio script and media folder from that brief. Use the same lesson ID across repositories and media, starting with `event-to-answer`.
4. Rehearse problem → decision → evidence → tradeoff. Use observed behavior, not invented numbers or unverified reliability claims.

Track subject-specific briefs and publication outcomes here. Put reusable production instructions in Lesson Studio rather than copying them into this repo.
