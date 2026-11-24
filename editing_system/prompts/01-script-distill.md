# Prompt 01: Optional Script Distillation (Stage 0)

Use this prompt only when a raw voice rant or long unscripted take needs to be tightened into a short spoken script before re-filming a clean A-Roll.

## Prompt Template

```text
Read:
- Raw transcript: {{RAW_TRANSCRIPT_PATH}}
- Creative Brief: {{CREATIVE_BRIEF_PATH}}
- Lesson mission / evidence notes: {{LESSON_BRIEF_PATH}}

Task:
Distill the raw take into a crisp, word-for-word {{TARGET_DURATION}} spoken script for {{TOPIC}}.

Rules:
1. Preserve my natural speaking voice and engineering precision; do not invent unverified claims or metrics.
2. Follow the Creative Brief goal and structure:
   - Hook (first 5-8s): State the concrete engineering question or real result immediately.
   - Evidence & Mechanism: Walk through the decision, verified data/code proof, and key tradeoffs.
   - Close: Land the engineering takeaway cleanly without filler sign-offs.
3. Keep spoken sentences concise so every beat pairs cleanly with concrete visuals or demos.
4. Output ONLY the spoken script and brief beat markers so I can film a clean A-Roll take.
```
