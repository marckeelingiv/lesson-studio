# Rule 01: Scientific Sifting (Technical Engine Room)

Sifting is always Stage 1 before any B-Roll, Scene Layout, or Motion Plate work begins (unless entering at Stage 2 with an already approved clean A-Roll Rough Cut).

## 1. Strict 4-Step Order

Run sifting in this exact sequence using deterministic audio and transcript analysis:

1. `sync` — Verify A/V sync, track selection, and separate camera alignment before cutting.
2. `dead_space` — Remove non-speaking gaps that hold no intentional visual demo activity.
3. `retakes_and_mistakes` — Remove aborted starts, repeated takes, and self-corrections.
4. `filler_words` — Remove isolated hesitation sounds and qualifying verbal fillers only when safe.

All cut timestamps must snap to the source video frame grid (computed from exact rational frame rate, never rounded assumptions).

## 2. Adaptive Room Tone & Dead Space Rules

- **Adaptive Room Tone (never fixed dB)**: Slice the selected speech track into 10ms RMS windows and measure the **quietest 10%** of windows as Room Tone for that exact recording and microphone. Never apply a hardcoded global decibel threshold across recordings.
- **Frame Thresholds**: Any Dead Space longer than 2–3 frames is eligible for cutting, while preserving **2–3 frames of natural breathing room** around cuts unless visual-activity protection applies.

## 3. Consonant Tail Protection

Words ending in unvoiced or soft plosive/fricative consonants—especially **`S`, `T`, `D`, `K`, and `P`**—decay quietly (`-38 dB` to `-45 dB`) and sound clipped if cut purely on ASR word boundaries.

- Track acoustic energy decay at word endings down to **`-50 dB`** above Room Tone before placing a cut out-point.
- Set the cut in-point **1 frame before** the next kept word's acoustic onset.
- When energy decay is ambiguous, add **2–3 safety frames** rather than clipping speech.
- Listen back to cut joins; an audible click or consonant blip indicates a cut at least 1 frame too tight.

## 4. Retake & Mistake Categories (5 Categories)

Classify retake candidates explicitly in `cut_audit.json`:

1. **Repeats**: Repeated phrases or sentences. **Last take wins**—remove from the first aborted attempt through any spoken retake cue (`"retake"`, `"scratch that"`, `"take two"`, `"start over"`, `"let me restart"`, `"cut cut"`). High-confidence auto-cut candidate.
2. **Reopens**: A passage re-opened and re-delivered in full. Surface in `cut_audit.json` for approval.
3. **Replacements**: Swapped words or mid-sentence self-corrections. Surface in `cut_audit.json` for approval.
4. **Rephrases**: Restating the same thought with different wording. Surface in `cut_audit.json` for approval.
5. **Exceptions**: Deliberate callbacks, rhetorical repetition, and intentional pauses inside a sentence are **not** retakes and must be preserved.

Audit transcripts against raw waveform energy to catch stutters or false syllables that speech recognition omits.

## 5. Context-Aware 25-Word Filler List

Never strip discourse words blindly. Use this 25-entry candidate list split into two tiers:

- **Tier A — Pure Hesitations (auto-cut when isolated with clean margins):**
  `um`, `uh`, `uhh`, `umm`, `er`, `erm`, `ah`, `hmm`, `eh`, `mm`, `mhm`, `uh-huh`
- **Tier B — Context-Sensitive Fillers (proposal-only in `cut_audit.json`; cut only if removing leaves grammar and meaning completely intact):**
  `like`, `you know`, `i mean`, `so`, `well`, `actually`, `basically`, `literally`, `right`, `okay`, `kind of`, `sort of`, `honestly`

## 6. Technical Demo Safeguards

Engineering walkthroughs rely on visual comprehension:

- **Screen-Activity Protection**: Protect Dead Space intervals that contain active screen motion, terminal output scrolling, cursor/click telemetry (`events.json`), or declared reading holds (minimum readable dwell on SQL, charts, or UI state changes).
- **Proposal-First Audit**: Every run emits `cut_audit.json` documenting removed and deferred ranges, unique removed seconds, category, confidence, neighboring words, and protected holds so Gate 1 reviews decisions cleanly without guessing.
