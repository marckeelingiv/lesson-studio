# Class 2: Scene Layouts (`layouts/`)

Parameterized HyperFrames HTML/CSS layout templates for 16:9 Scene Layouts (Starter Asset Pack v0.1). All templates consume Design Tokens from `../tokens/` and obey Safe Zones (`>= 5%` margins, fixed caption band).

## Canonical 16:9 Layouts (Slated for Phase 2 Implementation)

1. `full-screen` — Pure A-Roll speaker or full-canvas screen capture for conviction statements, punchlines, or critical live demo state.
2. `panel` — Speaker framed on left (or right) side panel alongside structured code, dashboard, or diagram content on the opposite panel.
3. `centre` — Speaker centered between two flanking comparison panels (before vs. after, option tradeoffs).
4. `full-graphic` — 100% Motion Plate, infographic framework, or B-Roll cutaway with speaker off-screen.
5. `circle` — Circular speaker picture-in-picture tucked into a non-occluding Safe Zone corner over full-canvas UI or screen capture.

Each template registers in `../catalog.json` with `class: "layouts"`, `aspect_ratios: ["16:9"]` (leaving `9:16` open for future expansion).
