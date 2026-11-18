# Experiment: presenter-assisted delivery

**Status:** experimental implementation available; outcome evaluation not recorded here.

## Hypothesis

Private prompts and a clean audience view can improve Marc's explanation clarity and delivery confidence at an acceptable preparation and capture cost.

## Current manifestation

`lesson_studio/` is a buildless JavaScript presenter/audience interface with portable lesson JSON, source capture, camera overlay, and short browser recordings. The first script is the 115-second “From event to answer” walkthrough. See the [operating guide](../lesson_studio/README.md) for instructions and limitations.

Private notes must remain separate from audience content while this interface is used. Its layout and recording method are implementation choices, not requirements for other approaches.

Implementation note (2026-11-17): the evidence desk now integrates the portable
purchase-evidence public slides into a persistent modular canvas, separate
evidence content rendering, validated camera-only two-window synchronization,
and in-place evidence refresh. Native checks cover projection/privacy, message
ordering, compound focus and retained scroll/focus. This is implementation
verification, not a visual review or evidence of communication benefit; actual
audience framing/capture and subject realism/exposure still require separate
review. See the operating guide's **Canvas implementation seams**.

## Alternatives

Ordinary slides with speaker notes; a live code/demo walkthrough; direct screen recording with OBS; scripted narration over recorded evidence; a presentation without video or slides. Post-production is optional and can be tested separately.

## Next trial and evaluation

Use one verified explanation and audience goal. Where practical, compare delivery with this interface against a simpler approach using the same material.

- Review whether the explanation makes the decision, evidence, and tradeoff understandable; collect viewer feedback when available.
- Record preparation/rehearsal time, delivery confidence, retakes, and capture or switching friction.
- Inspect the actual audience capture for private-note exposure, readable evidence, framing, and interruptions.

Continue if the communication benefit justifies the effort. Simplify or switch approaches if operating the interface distracts from delivery. Agree concrete thresholds after an initial baseline rather than inventing success numbers.

## Trial record

No outcome evaluation is recorded in this brief yet. For each trial append: date, communication goal, script/source commit, output or asset link, observations and effort, feedback, and a retain/revise/pause/retire decision with rationale. Store footage according to the [asset guide](../CONTENT_ASSETS.md).
