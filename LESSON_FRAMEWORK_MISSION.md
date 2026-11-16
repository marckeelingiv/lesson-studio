# Mission: make engineering judgment visible

## Purpose and audience

Help Marc communicate engineering skill and judgment clearly, using credible evidence, to advance his career. The intended audience includes engineers, hiring managers, and career contacts. Lessons, live demonstrations, presentations, and edited videos are possible formats, not requirements.

This document's canonical home is [Lesson Studio](https://github.com/marckeelingiv/lesson-studio). Lesson Studio owns reusable communication and production experiments, independent of any subject. Project Sandbox in DE for Fun is the first subject. See [repository and asset ownership](CONTENT_ASSETS.md) for external references and storage locations.

## Desired outcomes

- Clearer explanations that connect engineering decisions to business questions.
- Visible judgment: evidence, reasoning, tradeoffs, and limitations rather than tool demonstrations alone.
- Work suitable for sharing with career contacts or publishing when useful.
- A sustainable process whose preparation, delivery, and editing effort are worth the communication benefit.

## Principles

- Support claims with verified evidence. Label synthetic data and local deployment; distinguish demonstrations from production adoption or measured customer impact.
- Choose a format that serves the communication goal. Slides, a presenter interface, camera overlays, AI editing, and publication are optional.
- Preserve source material and human editorial control. Review the actual audience experience before sharing; rendering success does not establish visual or narrative quality.
- Keep reusable tools independent of subject applications and their infrastructure. Store source and assets according to the asset guide.

## Experimental approach

Current implementations are replaceable experiments, not permanent mission requirements. They may be used independently or together. Existing code and roadmap entries do not by themselves justify further investment.

1. Choose a communication goal and audience.
2. Prepare and verify the supporting evidence; problem → decision → evidence → tradeoff is a useful starting structure, not a required format.
3. Try an approach appropriate to that goal. Record the effort and friction as well as the output.
4. Review clarity, credibility, and the actual viewing or presentation experience.
5. Publish or share when appropriate; an internal trial is also a valid outcome.
6. Record what was observed and decide whether to retain, revise, pause, or retire the approach.

## Current experiments

| Experiment | Hypothesis and current manifestation |
| --- | --- |
| [Presenter-assisted delivery](experiments/presenter-assisted-delivery.md) | Private prompts and a clean audience view may improve delivery. Currently a JavaScript presenter/audience interface. |
| [Post-production video editing](experiments/post-production-video-editing.md) | Transcript-assisted editing may reduce editing effort without harming meaning or visual continuity. Currently the video pipeline. |

Implementation exists for both; evaluated communication benefit is not established by that fact. Each brief owns its evaluation questions, observations, and continuation decision. Operational details stay in the implementation guides.

## Ownership and documentation

- **Mission (this file):** enduring purpose, outcomes, and principles. Change it when the objective changes, not whenever a tool changes.
- **Experiment briefs:** hypotheses, alternatives, trial evidence, and retain/revise/retire decisions.
- **READMEs:** how current implementations work, including limitations and verification instructions.
- **[Roadmap](IDEAS_AND_ROADMAP.md):** implementation ideas and status, not commitments or evidence of benefit.
- **[Asset guide](CONTENT_ASSETS.md):** repositories, storage, and handoff conventions.
- **Lesson plans:** keep the [lesson library](lessons/README.md), including the [DE for Fun series](lessons/de-for-fun/README.md), independent of production tools. Each lesson owns its preparation brief, optional delivery script, and publication record. Subject repositories own platform roadmaps and technical evidence, not duplicate lesson plans.

## Working agreement for future agents

Before changing an experiment, read this mission, its brief, and the relevant implementation guide and agent instructions. Preserve the purpose, not necessarily the current solution. Keep implementation status, tested behavior, and evaluated benefit distinct. Update the owning document and its pointers rather than copying rules between documents. Record an experiment decision when changing direction; leave unobserved results explicitly unrecorded. Never claim visual review without inspecting the actual output.
