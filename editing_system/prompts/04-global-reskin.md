# Prompt 04: Global Design Token Reskin

Use this prompt to swap brand colors, typography, or light/dark theme globally across all Scene Layouts, Motion Plates, and Hero Visuals without changing cuts or animation timing.

## Prompt Template

```text
Inputs:
- New or updated Design Token kit: {{TOKEN_KIT_DIR}} (tokens.css + brand.json)
- Asset Catalog: editing_system/assets/catalog.json
- Current Storyboard & timeline: {{STORYBOARD_PATH}} and {{TIMELINE_PATH}}

Task:
1. Register or update the token kit in `editing_system/assets/catalog.json` (preserving schema compliance).
2. Update the project token import / CSS variables so every Scene Layout, Framework, Hero Visual, and Motion Plate inherits the updated palette, border styling, and typography without generic glowing gradients.
3. Keep all cut boundaries, Motion Plate timings, and audio sync unchanged.
4. Re-render the Contact Sheet and visual composition, run all automated QC checks (confirming `stale_check`, `fit`, `margin_check`, and contrast pass), and deliver the reskinned review output.
```
