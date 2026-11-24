# Taste Profile (Creative Engine Room Memory)

Persistent editorial guidance synthesized from timestamped human review feedback across completed videos. Agents read this file during Stage 2 (Storyboard) and Stage 3 (Visual Build & Revision Passes).

## 1. `review_log.jsonl` Record Schema

Append one JSON object per line to `editing_system/memory/review_log.jsonl` whenever human feedback is given during a Revision Pass or Gate 3 review:

```json
{
  "date": "2026-11-23",
  "video_id": "de-for-fun/purchase-evidence",
  "timestamp": "00:14.200",
  "category": "layout",
  "tag": "DON'T",
  "note": "Avoid covering chart axis labels with callout cards in Panel mode.",
  "promoted_rule_id": null
}
```

Allowed values:
- `category`: `sifting` | `layout` | `motion` | `captions` | `audio` | `pacing`
- `tag`: `DO` | `DON'T` | `PREFERENCE` | `NON-NEGOTIABLE`
- `promoted_rule_id`: `null` until promoted to a rule file, then rule identifier (for example `R02-safe-axis`)

## 2. Rule Promotion Protocol (>= 3 Videos)

1. After each video reaches Gate 3 delivery, scan `review_log.jsonl` for recurring patterns across **3 or more distinct `video_id` entries** in the same `category` or tagged `NON-NEGOTIABLE`.
2. **Propose** the generalized rule change to the human editor with links to the supporting log entries.
3. **Never silently mutate** `editing_system/rules/*.md` automatically. Apply the promotion and populate `promoted_rule_id` only after explicit human approval.

## 3. Active Taste Profile

*No historical video reviews recorded yet. Entries synthesized from `review_log.jsonl` will populate below by tag:*

### NON-NEGOTIABLE
- *(none recorded yet)*

### DON'T
- *(none recorded yet)*

### DO
- *(none recorded yet)*

### PREFERENCE
- *(none recorded yet)*
