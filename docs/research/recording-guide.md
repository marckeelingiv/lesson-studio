# DE for Fun — click-through recording script

Target: about 3 minutes. Keep this file beside your recording window. Read only the **Say** paragraphs; the other text is your private direction. Timings are cues, not deadlines.

## Before pressing Record

- Start the prepared subject stack using [DE for Fun's setup guide](/home/marc/dev/de-for-fun/docs/lesson.md). Start Lesson Studio separately if needed: `node lesson_studio/serve.mjs` from its repository root.
- Open each link below once, complete logins, and confirm the intended data is visible. Local endpoints did not respond during preparation of this guide; these are configured destinations, not a verified running session.
- Keep a visible “Local portfolio sandbox · synthetic historical data” disclosure. The arena charts cover July 12, 2025; Podium charts use 2024 data.
- Record a browser window containing only the demo tabs; keep this script outside that window. If using Studio's clean audience instead, open it from the desk and arrange capture of external tool tabs separately: they do not automatically appear in the audience.
- Zoom pages until chart labels and SQL are readable. Record a ten-second microphone and screen check.

## 1. 00:00–00:25 — Start with the result

**Click:** [Lightdash — visual demo dashboard](http://127.0.0.1:8080/projects/8f398e45-220e-4c65-b153-50ee54af03a7/dashboards/9e587da7-3c26-4040-bd37-86f82134b9b8).

**Show:** Pause on the KPI cards, then scroll to the vendor revenue bars and hourly revenue line. Keep the historical-data label visible. Do not change filters during the opening.

**Say:**

> How does a purchase become a number you can trust? This is my local data engineering sandbox. The dashboard shows synthetic historical data: revenue, purchase counts, and how revenue varies by vendor and hour. I'll start with this business view, then show the data and definitions behind it.

## 2. 00:25–00:55 — Show the data journey

**Click:** [Lesson Studio — evidence desk](http://127.0.0.1:4173/dashboard.html).

**Show:** Select the purchase branch in the lineage view. Click a source or base model, then a downstream purchase model to show its table preview. If recording a clean audience, use **Open clean audience** from this desk and capture that window; keep private controls out of frame.

**Say:**

> The purchase path runs from source data through base and staging models into an analytical mart. This view lets me inspect the dependencies and sample the saved tables. The connecting lines show declared model lineage. They aren't an animation of events moving through a live pipeline.

## 3. 00:55–01:25 — Explain the metric

**Click:** Stay in the [evidence desk](http://127.0.0.1:4173/dashboard.html). Click the wire leading to `mtt_dynamic_pricing` to open downstream SQL. Inspect its columns and aggregation.

**Fallback:** [Open the model SQL in the editor](/home/marc/dev/de-for-fun/dbt_project/models/marts/seg/mtt_dynamic_pricing.sql) if the evidence API is unavailable. Show the actual editor window in your capture.

**Show:** Point to the grouping columns and revenue sum. Pause long enough for the viewer to read them. Explain any source/manifest mismatch shown by the desk rather than hiding it.

**Say:**

> The definition matters as much as the chart. This model groups purchases by tenant, vendor, item, and hour, then sums their amounts. In this implementation, the date label comes from the minimum timestamp in the group. That limits what we can claim across multiple days. The arena dashboard uses a single historical day, and I make that boundary explicit.

## 4. 01:25–01:50 — Show orchestration

**Click:** [Dagster](http://127.0.0.1:3000).

**Show:** Open the asset graph and select a purchase-related dbt asset. Show an existing materialization or run only if one is present. Do not start a build during the take.

**Say:**

> Dagster provides the orchestration view. Here I can inspect the analytical assets, their dependencies, and any recorded materializations. A model definition and a successful run are different kinds of evidence. I check the run history separately instead of assuming that a diagram proves execution.

## 5. 01:50–02:25 — Return to the business view

**Click:** [Lightdash — visual demo dashboard](http://127.0.0.1:8080/projects/8f398e45-220e-4c65-b153-50ee54af03a7/dashboards/9e587da7-3c26-4040-bd37-86f82134b9b8).

**Show:** Point at the vendor ranking, then the hourly line. Scroll to the Podium sentiment and SLA charts and their period/aggregation notes. Read actual values from the visible chart only after checking its filters and units; this script deliberately does not hard-code a result from a different snapshot.

**Say:**

> Back in the dashboard, the vendor ranking and hourly line give two views of the arena purchases. The other charts demonstrate a separate domain: merchant sentiment and AI service metrics. Those use a different historical period. They belong in the same engineering demonstration, but I don't present them as one shared timeline or a causal relationship.

## 6. 02:25–02:50 — Close on engineering judgment

**Click:** Stay on the [visual dashboard](http://127.0.0.1:8080/projects/8f398e45-220e-4c65-b153-50ee54af03a7/dashboards/9e587da7-3c26-4040-bd37-86f82134b9b8). Return to the most readable chart overview.

**Say:**

> The goal is to connect a business question to inspectable data, a defined calculation, and a readable answer. This is a synthetic historical demo, not evidence of production impact or live freshness. What I want to demonstrate is the engineering judgment behind the result: clear definitions, visible dependencies, and honest limits.

Pause for three seconds, then stop recording.

## Optional insert — ingestion and storage, 20 seconds each

Use these only after confirming the services and relevant data are available. Insert between steps 2 and 3; add about 40 seconds to the total.

| Click | Show | Say |
| --- | --- | --- |
| [Redpanda Console](http://127.0.0.1:8083) | Topics; open `seg.pos-transactions` and inspect a retained synthetic message if available. | “The ingestion design buffers generated business events in Redpanda. This console lets me inspect the topic and any retained messages. I'm not claiming that this historical dashboard was just rebuilt from the message on screen.” |
| [Object storage console](http://127.0.0.1:9001) | Confirm the console's actual product name, then open the isolated demo bucket and Parquet objects. | “Object storage holds the Parquet data separately from the query engine. That separation lets the serving layer work over stored data without treating a dashboard as the source of truth.” |

## Recording notes

- If a required page is unavailable, fix it before the take or omit that section and its narration. Do not record setup screens while describing a finished result.
- The links return to stable entry pages. Selection inside Dagster and the evidence canvas is a manual action; no unverified model-specific deep links are assumed.
- Save the original recording outside Git. This guide belongs to Lesson Studio; platform setup and technical evidence remain in DE for Fun.
