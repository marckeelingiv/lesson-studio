# Editing System

Tool-agnostic rules, Creative Brief templates, typed assets, reusable prompts, and Taste Profile memory for producing engineering lesson videos.

All terminology follows [GLOSSARY.md](../GLOSSARY.md). Architecture decisions and the phased roadmap live in [ADR-0001](../docs/adr/0001-otio-and-hyperframes-over-remotion.md), [ADR-0002](../docs/adr/0002-tool-agnostic-two-engine-rooms.md), and [video-editing-system-plan.md](../docs/plans/video-editing-system-plan.md).

## Two Engine Rooms

- **Technical Engine Room (`rules/`)**: Invariant craft standards applied to every video (`01-sifting.md` through `05-workflow-and-gates.md`).
- **Creative Engine Room (`briefs/`, `memory/`)**: Per-video direction (`creative-brief.template.yaml`, `presets/clean-editorial.yaml`) and compounding review feedback (`review_log.jsonl`, `taste_profile.md`).

## 5-Stage Pipeline & 3 Human Gates

1. **Stage 0 — Creative Brief & Ingest**: Author brief, probe media, select speech track, transcribe, initialize timeline.
2. **Stage 1 — Scientific Sift** *(bypassable for pre-cut A-Roll)* -> **Gate 1: Rough Cut Approval**.
3. **Stage 2 — Storyboard & Contact Sheet** -> **Gate 2: Contact Sheet Approval**.
4. **Stage 3 — Visual Build, 8 Automated QC Gates & Revision Passes** -> **Picture Lock**.
5. **Stage 4 — Audio Layer, Final QC & Delivery** -> **Gate 3: Final Delivery & Taste Log**.

## 7 Typed Asset Classes (`assets/`)

Every reusable asset is registered in `assets/catalog.json` against `assets/catalog.schema.json`:

1. `tokens/` — Brand palettes, typography, spacing, and Safe Zone CSS variables.
2. `layouts/` — Canonical 16:9 Scene Layouts (`Full Screen`, `Panel`, `Centre`, `Full Graphic`, `Circle`).
3. `frameworks/` — Structured infographic templates (`linear`, `non-linear`, `cyclical`, `hierarchical`, `matrix`).
4. `heroes/` — Signature recurring Hero Visual templates reused across sections.
5. `motion/` — Reusable motion mechanics and the 4 allowed transitions (`subtle`, `swipe`, `zoom`, `film_burn`).
6. `graphics/` — Vector icons, logos, SVG marks, and browser/terminal mockups.
7. `audio/` — Curated local CC0/royalty-free SFX and music beds plus attachment rules.
