# Temporary build research

This directory holds scouting receipts and downloaded upstream reference text
for the ArtCraft skill build. It is working evidence, not a runtime dependency.
The finished skill's `references/` directory owns its operating instructions.

| Folder | Scope |
| --- | --- |
| `automation/` | FilmCraft CLI, MCP, control channel, session and command discovery |
| `transcripts/` | Speech features, imported word times, cuts and captions |
| `timeline/` | Multitrack, visuals, audio, export and interchange |
| `optional-tools/` | EffectCraft and SoundCraft automation and handoffs |
| `integration/` | Reuse of Lesson Studio specialist profiles |

Each scout records upstream revision, URLs, acquisition date and evidence limits.
Downloaded documentation and inspected source do not establish local runtime
compatibility. The supplied ArtCraft PDF is a feature wishlist, not an API contract.
Reports and provenance manifests are versioned; raw third-party snapshots are
ignored local working evidence. Snapshot-relative links in research reports refer
to those local downloads, not files guaranteed to exist in a fresh checkout.

No FilmCraft, EffectCraft or SoundCraft executable was found on PATH during the
coordinator's initial check. Installation, model downloads and production-media
trials are outside this skill-documentation build.

Retain this temporary evidence until review is complete. It can then be removed
separately without breaking runtime instructions; no automatic cleanup is implied.
See `run.json` for ownership and build status.
