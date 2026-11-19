# From event to answer

- **Subject / lesson ID:** `de-for-fun` / `event-to-answer`
- **Status:** saved-snapshot MCP evidence verified; 145-second silent evidence-replay draft rendered; one rendered frame per scene inspected for readability and webcam clearance. Human pacing rehearsal and final recording pending.
- **Audience:** engineers, hiring managers, and career contacts
- **Goal:** show end-to-end engineering judgment by connecting a business question to a defined metric and an actual answer.
- **Format / duration:** six-scene walkthrough, approximately 115 seconds; presenter optional.
- **Narration and scenes:** [presenter.json](presenter.json). Keep narration there rather than duplicating it here.

## Evidence and demo preparation

- **Subject repository:** https://github.com/marckeelingiv/de-for-fun
- **Source commit:** `07305d610cc14ff6aec9d17ae96cb4247b1128aa` (clean subject working tree). Existing database and semantic manifest are generated artifacts; their original build commit is not established.
- **Business question:** Which vendor generated the most revenue in the synthetic arena dataset on 2025-07-12?
- **Verified result:** `merch_002` leads with 71,488.11. All eight vendors total 231,206.05 across 10,000 purchases. Raw `SUM(amount)`, modeled `SUM(total_revenue)`, and the MCP result sum agree within floating-point tolerance; displayed values are rounded to two decimals.
- **Technical prerequisites / demo command links:** pending; link versioned instructions in the subject repository.
- **Generated event:** captured an actual stored synthetic row from `base_pos_transactions`, not a newly observed Redpanda event. The draft must not imply a fresh ingestion run.
- **Model and metric:** [model SQL](https://github.com/marckeelingiv/de-for-fun/blob/07305d610cc14ff6aec9d17ae96cb4247b1128aa/dbt_project/models/marts/seg/mtt_dynamic_pricing.sql), [semantic definition](https://github.com/marckeelingiv/de-for-fun/blob/07305d610cc14ff6aec9d17ae96cb4247b1128aa/dbt_project/models/marts/semantic_models.yml), and [metric](https://github.com/marckeelingiv/de-for-fun/blob/07305d610cc14ff6aec9d17ae96cb4247b1128aa/dbt_project/models/marts/metrics.yml).
- **MCP interaction:** successful FastMCP client calls to `list_metrics`, `get_metric_details`, and date-bounded `query_metric`, grouped by `vendor_id`. Captured JSON is in the local workspace below. This is an evidence replay, not a recorded natural-language assistant conversation.
- **Verification boundary:** current SQL groups by tenant/vendor/item/hour, deriving date from the minimum timestamp rather than grouping by date. The verified source snapshot contains only 2025-07-12. The existing mart lacks `latest_timestamp`, which current source includes: do not claim the saved database was built from the recorded source commit or that current incremental rebuilds were verified.

## Boundaries

Label the demo **local portfolio sandbox / synthetic data**. Do not imply production adoption, customer impact, or single-event-ID tracing through the entire platform. Explain the metric's grain, aggregation, and one boundary using verified implementation details.

## Before recording

- [ ] Fill the source commit, exact question, verified answer, and technical links above.
- [ ] Rehearse event → data journey → metric definition → MCP answer.
- [ ] Prepare the editor and assistant windows; make code and results readable.
- [ ] Explain one decision and tradeoff; keep the local/synthetic disclosure visible.
- [ ] Check microphone and recording surface with a short capture, then inspect it.
- [ ] Record the full take; pause between sections and restart whole sentences after mistakes.
- [ ] Download and preserve the original recording and take notes before closing the recorder.
- [ ] Review the final capture for accuracy, readability, private-note exposure, and clean transitions.

## Handoff

- **Media folder:** pending; use `<media-root>/de-for-fun/event-to-answer/` outside Git.
- **Local draft workspace:** `video_pipeline/workspace/event-to-answer/` (ignored). `event-to-answer-silent.mp4`, `voiceover.md`, and `evidence.json`; reserved bottom-right webcam area. This 145-second evidence-replay draft is separate from the original 115-second live presenter script. No microphone or webcam capture is performed.
- **Selected take / notes:** pending
- **Reviewed output / feedback:** pending
- **Platform copy and publication record:** [publishing.md](publishing.md)

See the [recording guide](../../../lesson_studio/README.md#rehearse--record--edit--publish) and [asset ownership](../../../CONTENT_ASSETS.md). Editing is optional; use the simplest approach that communicates the evidence clearly.
