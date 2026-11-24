# Rule 03: Audio Mix and Sound Design (Technical Engine Room)

Audio layering happens exclusively in Stage 4 **after Picture Lock** is confirmed at Stage 3. Never design sound effects or music cues against unlocked visual timings.

## 1. Sourcing & Licensing

- Use local, verified CC0 or royalty-free audio registered in `editing_system/assets/catalog.json` under class `audio`.
- Paid external audio APIs are disallowed unless explicitly authorized by the user.
- Every audio track or SFX file must record license and attribution metadata in `catalog.json`.

## 2. Delivery Loudness & True Peak Targets

- Default 16:9 YouTube preset (`clean-editorial`):
  - **Integrated Loudness**: `-14 LUFS` (configurable per delivery target in `creative-brief.yaml`).
  - **Maximum True Peak**: `-1.0 dBTP`.
  - **Sample Rate**: `48 kHz`.
- Apply gentle per-cut micro-fades (`<= 0.02s`) on dialogue joins after verifying Consonant Tail preservation so edits never click.
- Always retain a clean **dialogue-only stem/alternative** alongside the mixed master.

## 3. Dialogue Ducking & Music Beds

- Spoken voice is the primary information channel. Duck background music cleanly underneath dialogue so voice remains crisp and unmasked.
- Keep music subdued or absent during dense code/architecture explanations when Creative Brief `sound_design` dial is `1` or `2`.

## 4. Explicit SFX Attachment Rules

Every SFX placement must satisfy an explicit trigger rule and remain **quieter than the spoken voiceover**:

- **Attach SFX (`whoosh`, `pop`, `ui_click`, `soft_hit`, `riser`) ONLY when**:
  - Entering a major section boundary or Hero Visual state change.
  - Emphasizing a deliberate UI focus click or primary Motion Plate reveal (`<= 1` SFX per visual beat).
- **Omit SFX when**:
  - Rapid consecutive beats occur less than 2 seconds apart.
  - Dense technical narration is uninterrupted (avoid competing transients).
  - Standard hard cuts switch between `Full Screen` and `Panel` without a major conceptual shift.
