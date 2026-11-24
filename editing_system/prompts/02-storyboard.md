# Prompt 02: Storyboard and Contact Sheet (Stage 2)

Use this prompt after Gate 1 (Rough Cut approval) to plan Scene Layouts, Motion Plates, and Hero Visual variations, then generate the Contact Sheet for Gate 2 before rendering video.

## Prompt Template

```text
Read these authoritative inputs before writing any visual code:
1. Glossary: GLOSSARY.md
2. Rules: editing_system/rules/02-storyboard-and-layouts.md and editing_system/rules/05-workflow-and-gates.md
3. Creative Brief: {{CREATIVE_BRIEF_PATH}}
4. Taste Profile: editing_system/memory/taste_profile.md
5. Asset Catalog: editing_system/assets/catalog.json
6. Approved Rough Cut timeline & transcript: {{TIMELINE_PATH}} and {{TRANSCRIPT_PATH}}
7. Screen captures / evidence assets: {{EVIDENCE_DIR}}

Before animating or rendering any video:
1. Propose `storyboard.json` mapping exact Rough Cut timecodes to Scene Layouts (`Full Screen`, `Panel`, `Centre`, `Full Graphic`, `Circle`), reusable Hero Visuals/Frameworks from `catalog.json`, and Motion Plates.
2. Enforce the Intentionality Filter: every Motion Plate, layout switch, and transition (hard cap <= 3 transitions total) must state its Reason, Purpose, and Intention.
3. Apply the active Design Tokens (`{{TOKEN_KIT_ID}}`, theme `{{THEME}}`) and Safe Zones (fixed caption band, unobstructed face/eyes, readable UI).
4. Render static keyframe PNGs and a Contact Sheet grid covering every planned Scene Layout change and Motion Plate so I can approve layout, typography, contrast, and Safe Zones at Gate 2 before video rendering.
```
