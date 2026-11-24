Here is the full breakdown of **Stockton Walbeck’s** video, *"How I Trained Claude/Open/Codex to Edit Like a Real Editor (7 Rules)"* ([http://www.youtube.com/watch?v=fMdsZTsVG5A](http://www.youtube.com/watch?v=fMdsZTsVG5A)), including the on-screen technical specs and frameworks shown at your timestamps.

## Chapters & Core Architecture

* **0:00** — 100 editors, 7 rules
* **0:30** — Rule 1: Creative direction
* **4:20** — Rule 2: Sift scientifically
* **6:50** — Rule 3: Good input, good output
* **10:31** — Rule 4: Less is more
* **12:29** — Rule 5: Intentional scene cuts
* **14:13** — Rule 6: Make it once, use it 10x
* **16:03** — Rule 7: Catch it before I do

Before the 7 rules, Walbeck splits AI video editing into **Two Engine Rooms** [[00:36](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=36)]:

* **Technical Engine Room (Static Foundation):** Doesn't change video to video—373 codified rules (e.g., *let the word finish, cut dead space, last take wins, captions never move*), 152 templates, and a deterministic pipeline (`01 Sift` → `02 Storyboard` → `03 Build`) [[00:48](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=48)].
* **Creative Engine Room (Variable Per Video):** Preferential and subjective—governed by **Taste, Vibe, and Flow** sliders that shift based on the specific video's creative brief [[00:56](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=56)].

---

## Rule 1: Creative Direction (The Creative Brief)

Spending 10 minutes on a **Creative Brief** upfront prevents 2 hours of revision notes later [[02:15](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=135)]. Every brief has three parts [[02:29](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=149)]:

1. **References (Good vs. Not Good):** Provide **1–2 videos max** (never 50, which confuses the model) [[02:55](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=175)]. Explicitly label what is *good* vs. *not good* [[02:39](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=159)] and call out the exact attributes to emulate: **B-roll, Compositions, and Sound Design** [[03:04](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=184)].
2. **The Feel:** Define the edit intensity (**Heavy/Punchy**), pacing speed (**Fast**), and specific **Moments** to emphasize [[03:19](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=199)]. Even a rambling, amorphous voice rant can be reverse-engineered by Claude into concrete whole-video decisions (e.g., *Full A-roll for opinion/conviction, Side panel for explaining, Centre panel for two-sided comparisons, max 3 deliberate transitions*) [[03:33](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=213)].
3. **Starting Visuals:** Give the AI a concrete visual anchor—such as a screenshot of the 7 fanned-out cards used to structure this video—so it doesn't randomly invent generic metaphors like pillars or fingers [[03:55](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=235)].

---

## Rule 2: Sift Scientifically (Not by Feeling)

Sifting is always step one before any B-roll or graphics are touched [[04:26](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=266)]. Walbeck’s system breaks it into a strict four-step order (`sync` → `dead space` → `retakes/mistakes` → `filler words`) using deterministic audio analysis rather than guesswork [[06:29](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=389)].

### Dead Space Removal

* **Adaptive Noise Floor:** Chop the audio into **10ms windows**, take the **quietest 10%** of those windows, and set that as **The Floor** (room tone) [[05:15](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=315)]. Never use fixed/absolute decibel thresholds—every mic and room is measured fresh [[00:27](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=27)].
* **Frame Thresholds:** Any gap longer than **2–3 frames** is cuttable, leaving 2–3 frames of natural breathing room [[05:10](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=310)].
* **Consonant Tail Protection:** Words ending in **`S`, `T`, `D`, `K`, or `P**` decay quietly (-38 to -45 dB) and get clipped if cut too aggressively [[05:34](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=334)]. Track the tail down to -50 dB, set the in-point 1 frame before the next word's first sound, and add 2–3 frames when unsure [[09:48](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=588)].

### Retake & Mistake Removal (5 Categories)

To catch tone resets, pacing redos, word flubs, lost trains of thought, and awkward pauses, the AI is trained on **5 distinct categories** [[06:24](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=384)]:

1. **Repeats:** Repeated sentences/phrases (the last take wins; delete everything from the first attempt through the cue) [[09:48](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=588)].
2. **Reopens:** A re-opened passage is redone in full [[06:29](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=389)].
3. **Replacements:** Swapped words or mid-sentence corrections.
4. **Rephrases:** Restating the same thought differently.
5. **Exceptions:** Callbacks are *not* redos; intentional beats inside a sentence are rhythm, not dead space [[06:29](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=389)].

*Additional on-screen sifting rules:* Every cut gets listened back to (a blip means it's 1 frame too tight); filler words are removed from a 25-word list only if the sentence still makes sense; every cut point snaps to the frame grid; transcripts are audited against raw sound for stutters the transcript can't hear [[09:48](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=588)].

---

## Rule 3: Good Input = Good Output (The Asset Moat)

Generic prompts produce generic slop. Asking *"write me a good hook"* is a crapshoot, whereas feeding three concrete assets—(1) a **Google Doc of 100 verbal hook templates**, (2) a **360° Ideal Customer Profile (ICP)** doc, and (3) **5 viral Instagram Reels** on similar topics—produces high-performing copy immediately [[07:25](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=445)].

**Why skills and prompts alone aren't enough:** Anyone can vibe-code a basic Claude Code editor in 2 hours, and most paid `$47–$197` `SKILL.md` packs are just washed-down prompts (*"Add a hook in the first 3s. Make it engaging."*) [[08:53](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=533)]. The real moat is feeding the agent a structured system of **reusable assets, scripts, and patterns** [[09:12](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=552)]:

| Asset Category | What Walbeck Feeds the AI |
| --- | --- |
| **Composition Rules & Templates** | **127 layouts** segmented for short-form, long-form, or both [[09:14](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=554)]. |
| **Infographic & Framework Kit** | **93 framework graphics** mapped to **5 framework types** shown on screen [[09:19](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=559)]:<br>

<br>• **Linear** (step flows, timelines, acronyms)<br>

<br>• **Non-Linear** (segmented rings, pillars, radial hubs)<br>

<br>• **Cyclical** (loops, feedback cycles)<br>

<br>• **Hierarchical** (org trees, pyramids, tiers)<br>

<br>• **Matrix** (2x2 grids, Venns, plus Ladder, Roadmap, Iceberg, Cone Funnel, Leaderboard, Threat Map) [[09:25](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=565)]. |
| **Icons, PNGs, SVGs & Mockups** | **120 files**: 36 icons, 20 logos, and 25 device mockups [[09:29](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=569)]. |
| **Sound Effects & Libraries** | Curated SFX library paired with rules teaching AI *when* to attach a sound effect to a motion and when *not* to [[09:35](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=575)]. |
| **Motion Mechanics (12 Types)** | Explicitly defined on screen [[09:41](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=581)]:<br>

<br>1. **Text Entrances** · 2. **Things Sliding In and Out** · 3. **Live Numbers** · 4. **Colour** · 5. **Mattes** · 6. **Camera Moves** · 7. **Tiles Landing** (tile animations) · 8. **Circles and Marks** · 9. **Transitions** · 10. **Captions** · 11. **Cards** · 12. **Sound Hits** |
| **Process & QA Systems** | Codified sifting rules, storyboarding processes, quality-checking rules, VE templates, and analyzed Premiere Pro projects [[09:48](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=588)]. |

---

## Rule 4: Less Is More (Intentionality)

The #1 tell that a video "looks like AI" is **retention maxing**—slapping constant keyframes, hyperactive motion, and loud whooshes/dings onto every second [[10:51](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=651)].

* **The Control Spectrum:** Treat intensity as a controllable dial between **Clean ↔ Retention Max**, with independent sliders for **Animation**, **Visuals**, and **Sound Design** [[11:06](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=666)].
* **Intentionality Filter:** Every visual, tile animation, and sound effect must have a **Reason, Purpose, and Intention** [[11:20](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=680)].
* **Hard Cap on Transitions:** Walbeck enforces a strict rule of **no more than 3 transitions per video** (choosing deliberately between *Swipe, Zoom, Subtle,* or *Film Burn*) so scene changes don't feel like a nauseating roller coaster [[12:04](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=724)].

---

## Rule 5: Intentional Scene Cuts

After sifting and transcribing, the storyboard maps specific spoken beats to deliberate **scene layouts (compositions)** rather than cutting randomly [[13:10](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=790)]. Long-form videos use a wider library of layouts than short-form [[12:40](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=760)]:

* **Full Screen:** Pure talking head for conviction, opinions, or punchlines [[12:48](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=768)].
* **Panel:** Speaker boxed on the left, supporting visuals on the right [[12:51](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=771)].
* **Centre:** Speaker centered with two competing ideas/comparisons flanking left and right [[12:57](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=777)].
* **Full Graphic:** 100% motion graphic or B-roll with speaker off-screen [[13:01](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=781)].
* **Circle:** Small circular PiP on the left/right over a full-canvas graphic [[13:05](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=785)].

---

## Rule 6: Make It Once, Use It 10x

Efficiency protects both render time and Claude Code token budgets [[14:24](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=864)]. Spending 6 hours (or burning 97% of a weekly token limit) on a bespoke graphic that only appears for 3 seconds is a massive waste [[14:45](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=885)].

* **Build 1–2 Core Hero Visuals:** For educational or listicle videos, invest effort into one or two signature recurring templates—like the **7-card fan** in this video or the **12-prompt 3D carousel** reused 12–15 times in an 18-minute video—and bring them back with slight variations at each section [[15:43](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=943)].

---

## Rule 7: Catch It First (Automated QC & Compounding Memory)

Human editors often skip rewatching their own cuts, forcing creators to spend **45 minutes leaving 300+ technical notes** instead of **5 minutes leaving 4 creative notes** [[16:35](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=995)].

### Non-Negotiable AI Quality Checks

Before a cut is ever handed over for human review, the AI must pass **8 automated technical gates** [[17:03](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=1023)]:

1. `flash (E5)` — 0 flash frames
2. `blank_check` — 0 blank frames
3. `fit (AS-3)` — 0 clipped text
4. `margin_check` — 0 margin violations
5. `eyes_mouth_check` — 0 frames covering the speaker's face
6. `stale_check` — 0 stale rows
7. `hold_sentence` — 0 cuts before a sentence finishes
8. `stability (MO-7)` — 0 jitter

*(The final pipeline summary also checks **Freeze, Tails, Captions, Audio, Frames, and Boxes** before delivery [[19:55](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=1195)].)*

### The Compounding Feedback Loop

Unlike human editors—where tens of thousands of past revision comments are lost over time—the AI logs every timestamped review note, tags it (`PREFERENCE`, `NON-NEGOTIABLE`, `DON'T`, `DO`), and builds a persistent taste profile [[17:45](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=1065)]. After 5–6 videos, it runs pattern recognition across recurring issues (e.g., sound design, visuals, or sifting flagged in 6 of 6 videos) and locks in permanent technical fixes—leaving you to spend 100% of your revision time (typically just 2–3 rounds) purely on creative polish [[18:55](https://www.youtube.com/watch?v=fMdsZTsVG5A&t=1135)].

---

Let me know if you want to turn this into a standalone **interactive HTML playbook** (with Mermaid diagrams, checklists, and Claude Code system/skill templates) or if you'd like to drill into any specific part—like the sifting rules or the 8 QA checks—first.