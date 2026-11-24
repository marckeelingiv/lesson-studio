# Rule 02: Storyboard, Scene Layouts, and Anti-Slop (Technical Engine Room)

No video render runs until Stage 2 produces a Storyboard and an approved Contact Sheet (Gate 2).

## 1. The Intentionality Filter

Every Motion Plate, Scene Layout switch, Hero Visual variation, and transition must record three fields in the Storyboard:

- **Reason**: Why this visual change happens at this exact spoken beat.
- **Purpose**: What engineering concept, comparison, or evidence it clarifies.
- **Intention**: The viewer comprehension state it creates (matching Creative Brief intensity dials).

Default preset for engineering lessons (`clean-editorial`): **Animation 2/5, Visuals 2/5, Sound Design 1/5**. Reject hyperactive "retention-maxing" motion on every sentence.

## 2. Canonical 16:9 Scene Layouts

Map each spoken beat deliberately to one of the 5 Scene Layouts (using aspect-ratio-tagged templates from `editing_system/assets/layouts/`):

1. **Full Screen**: Pure A-Roll speaker or full screen capture for conviction, thesis statements, opinions, or critical live demo state.
2. **Panel**: Speaker framed on the left (or right) side panel alongside structured supporting visuals, code, or UI captures on the opposite panel.
3. **Centre**: Speaker centered with two competing concepts, before/after states, or architectural tradeoffs flanking left and right.
4. **Full Graphic**: 100% Motion Plate, diagram, or clean B-Roll cutaway with speaker off-screen for dense frameworks or focused walkthroughs.
5. **Circle**: Small circular speaker picture-in-picture tucked cleanly into a non-occluding corner over full-canvas UI or Motion Plate content.

## 3. Rule of Reuse ("Make It Once, Use It 10x")

- Invest effort into **1–2 signature Hero Visual templates** per video (e.g., an Engineering Section Card Deck or progressive architecture map) and reuse them across chapters with targeted state variations.
- Do not author one-off bespoke animations for 3-second beats when a parameterized template from `editing_system/assets/frameworks/` or `heroes/` communicates the point more consistently.

## 4. Transitions Hard Cap

- **Maximum 3 transitions per video.** Ordinary Scene Layout changes and beat cuts use clean hard cuts (or J-Cut / L-Cut audio bridges).
- Choose transitions exclusively from the 4 approved families:
  1. `subtle`
  2. `swipe`
  3. `zoom`
  4. `film_burn`

## 5. Safe Zones & Fixed Captions

- **Captions Never Move**: Keep captions anchored at a single consistent 16:9 Safe Zone coordinate band across the entire video (lower-center band clear of lower-third titles and PiP camera containers).
- Respect outer 16:9 Safe Zone margins (`>= 5%` horizontal, `>= 5%` vertical) for all text, cards, and callouts.
- Never place overlays or captions over the speaker's eyes or mouth (`eyes_mouth_check`) or obscure critical evidence labels/disclosures.

## 6. Anti-Slop Design Constraints

- **No generic glowing gradients or dark neon blobs.** Use centralized Design Tokens (`tokens.css` / `brand.json`) for clean surfaces, crisp typography, and high-contrast borders.
- **No fabricated metaphors.** Start from concrete visual anchors specified in the Creative Brief and real product/code screenshots or SVGs from `editing_system/assets/graphics/`.
- **Contact Sheet First**: Always render static keyframe stills for every planned Motion Plate and Scene Layout shift and pass Gate 2 before rendering motion video.
