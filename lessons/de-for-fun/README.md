# DE for Fun content plan

Canonical series plan: this file in Lesson Studio. Subject implementation and technical evidence live in [marckeelingiv/de-for-fun](https://github.com/marckeelingiv/de-for-fun). Keep lesson plans here and link back to the subject rather than copying its technical documentation.

## Purpose

Make engineering judgment visible to engineers, hiring managers, and career contacts through evidence-backed demonstrations of Project Sandbox. Connect business questions to engineering work. Label synthetic data, local deployment, and limitations; this is not evidence of production adoption or measured customer impact.

## Planned series

| Lesson | What viewers should assess |
| --- | --- |
| [From event to answer](event-to-answer/brief.md) — scripted; evidence verification pending | End-to-end delivery and clear communication |
| Why DuckDB; when to choose something else | Technical judgment and cost awareness |
| Malformed or duplicate data | Reliability and correctness, using observed behavior |
| Defined metrics through MCP | Practical AI integration and its boundaries |
| An agent change reviewed and verified | Engineering with agents |
| An architectural rule enforced automatically | Repeatable delivery and platform leadership |

These are demonstrations to prepare, not claims that every capability exists. Prioritize one clear demo and three strong posts before adding platform breadth. A recurring theme is turning engineering decisions into automated checks.

## Production handoff

Use this repository's reusable presentation and post-production experiments only when useful. Read the [mission](../../LESSON_FRAMEWORK_MISSION.md), relevant [experiment brief](../../experiments/), and [asset ownership](../../CONTENT_ASSETS.md) before changing production tools. Presentation and post-production are independent options, not a required sequence.

The first script is [presenter.json](event-to-answer/presenter.json): six scenes, 115 seconds, with narration and evidence prompts. Start with its [preparation brief](event-to-answer/brief.md). The other five topics are outlines, not completed scripts.

Before recording each lesson:

1. Choose one business question and verify its actual result.
2. Record the DE for Fun commit, links to technical prerequisites and demo commands, model/metric paths, and known limitations in the lesson's `brief.md`.
3. Link the matching Lesson Studio script and media folder from that brief. Use the same lesson ID across repositories and media, starting with `event-to-answer`.
4. Rehearse problem → decision → evidence → tradeoff. Use observed behavior, not invented numbers or unverified reliability claims.

Track preparation in each lesson's `brief.md` and platform copy and publication outcomes in its `publishing.md`. Link reusable production instructions rather than copying them.
