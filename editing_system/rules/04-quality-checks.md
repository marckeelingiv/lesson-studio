# Rule 04: Automated Quality Checks (Technical Engine Room)

Before any V1 review cut, Revision Pass render, or final master is presented to the human reviewer, the automated QC runner must execute and pass all blocking gates. Automated passes catch technical defects; they never replace human visual and listening review.

## 1. Eight Hard-Blocking Pre-Human Gates

1. **`flash`**: Zero unintended 1–2 frame Flash Frames or luma/chroma spikes at cut joins and transition boundaries.
2. **`blank_check`**: Zero unintended black, blank, or zero-variance frames (`blackdetect` + pixel variance check).
3. **`fit`**: Zero clipped, truncated, or overflowing text/container elements in rendered compositions (`hyperframes check` + DOM bounds).
4. **`margin_check`**: Zero Safe Zone margin violations for captions, lower thirds, or Motion Plates (`>= 5%` title-safe margins).
5. **`eyes_mouth_check`**: Zero frames where overlays, cards, or captions cover the speaker's eyes or mouth when a camera stream is visible.
6. **`stale_check`**: Zero rendered outputs built from stale upstream timelines, transcripts, Storyboards, or Design Tokens (verified via SHA-256 dependency hashes in `run.json`).
7. **`hold_sentence`**: Zero timeline cuts interrupting mid-word or slicing before a sentence finishes (`.otio` cut bounds verified against word-level transcript timings).
8. **`stability`**: Zero caption position drift across frames (fixed caption anchor invariant) and zero unintended frame-to-frame Motion Plate jitter.

## 2. Six Final Delivery Checks (Stage 4)

In addition to re-running the 8 gates above on the final locked render:

1. **`decode`**: Full container decode without stream corruption, missing audio, or VFR drift.
2. **`tail_check`**: Consonant Tail acoustic decay audit verifying cut outs preserve `S/T/D/K/P` endings.
3. **`freeze_check`**: Flag unexpected frozen video intervals distinguishing deliberate reading holds.
4. **`captions`**: Verify exported `.srt` and burned-in captions match corrected text, zero-based final timeline timings, and contrast rules.
5. **`loudness`**: Measure encoded integrated loudness (`-14 LUFS` default) and true peak (`<= -1.0 dBTP`) via `ebur128` against the Creative Brief target.
6. **`frames_and_boxes`**: Sample join frames, start/end frames, transition midpoints, and overlay bounding boxes for clean readability and zero occluded UI disclosures.

## 3. Explicit Waiver Policy

- **Only two checks may ever be waived**: `eyes_mouth_check` and `freeze_check` (for example, deliberate static reading holds on SQL/architecture diagrams or intentional full-canvas cutaways).
- Waivers must record exact edited-timeline `start`, `end`, `gate`, `reason`, `approved_by`, and `timestamp` in `run.json`.
- `flash`, `blank_check`, `fit`, `margin_check`, `stale_check`, `hold_sentence`, `stability`, `decode`, and `loudness` cannot be waived.
