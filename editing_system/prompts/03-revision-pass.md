# Prompt 03: Focused Revision Pass (Stage 3)

Use this prompt after inspecting a Contact Sheet or automated-QC-clean visual render. Limit each Revision Pass to 1-3 concrete, timestamped notes so edits stay fast and auditable.

## Prompt Template

```text
Revision Pass against: {{CURRENT_REVISION_PATH}}
Rules: editing_system/rules/02-storyboard-and-layouts.md and editing_system/rules/04-quality-checks.md
Taste Profile: editing_system/memory/taste_profile.md

Apply ONLY these targeted changes (1-3 items):
1. [{{TIMESTAMP_OR_PLATE_ID}}] Layout / Framing: {{LAYOUT_OR_PIP_NOTE}}
2. [{{TIMESTAMP_OR_PLATE_ID}}] Timing / Pacing: {{TIMING_OR_WORD_SYNC_NOTE}}
3. [{{TIMESTAMP_OR_PLATE_ID}}] Visual Clarity / Anti-Slop: {{VISUAL_FIX_NOTE}}

Constraints:
- Do NOT add background music or SFX until Picture Lock is declared.
- Preserve fixed caption positioning, Safe Zones, and existing approved beats.
- Re-run all 8 automated QC gates (`flash`, `blank_check`, `fit`, `margin_check`, `eyes_mouth_check`, `stale_check`, `hold_sentence`, `stability`) before reporting the updated render for review.
- Append timestamped notes to `editing_system/memory/review_log.jsonl` if flagged as `NON-NEGOTIABLE`, `DON'T`, `DO`, or `PREFERENCE`.
```
