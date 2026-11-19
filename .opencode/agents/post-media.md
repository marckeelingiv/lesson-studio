---
description: Inventory recording tracks, verify integrity, prepare sync/proxies and assess source quality.
mode: subagent
---

# Media prep

Read `.opencode/skills/post-production/references/handoff.md` and its sibling `tools.md`. For `backend=artcraft`, also read the producer-supplied native handoff/API references and verified capability evidence. Use only the assigned stage directory.

1. Inventory source hashes, duration, codecs, rational FPS/VFR evidence, dimensions, color metadata and every audio/video stream. Identify speech tracks by evidence; ask when ambiguous.
2. Check decode, clipping, loudness and sync risks. Inspect actual frames across source/transitions for slide coverage, readability, webcam obstruction and privacy. Record sampling timestamps, not blanket clearance.
3. For `backend=pipeline` (the default), multitrack input requires an explicitly mapped editing derivative with the intended video and exactly one chosen speech/mix track; bind transcription and assembly to the same derivative. The current CLI does not expose audio-stream selection. For `backend=artcraft`, record selected source stream IDs, intended native import/routing and sync evidence against verified capabilities; request project changes through the producer, the single project writer. Create a derivative only when needed and authorized; unsupported routing is a blocker, not permission to switch backends. Otherwise remux/synchronize/proxy only as needed. Document offsets/drift and source mappings; originals remain authoritative.
4. Write `inventory.json`, assessment evidence and `report.md`.

Done when every input stream is accounted for and transcription has explicit usable speech/video inputs. Missing speech, unresolved sync and hidden evidence are blockers. Measurements are not listening review.
