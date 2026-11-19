# SoundCraft: optional aligned audio processing

**FilmCraft first.** Keep ordinary gain, fades and suitable processing in the picture editor. Use SoundCraft only for a specific unmet audio need, preferably after picture lock. The default handoff is a **full-length, aligned PCM WAV replacement**, not a second independently edited timeline.

Evidence: inspected upstream documentation/source at **`a02d892f831f0a4e1220e0357c7b941030b9cd6f`**. No local application, plugin, save/reopen, bounce or FilmCraft reimport was tested. Production use is **blocked until the disposable-sample gate passes**. Installation, configuration, downloads and third-party plugin loading require separate consent.

## 1. Connect and discover

| Surface | Source-confirmed entry |
| --- | --- |
| Headless MCP | `soundcraft-cli mcp` |
| Live app | `soundcraft --control <port>` then `soundcraft-cli mcp --connect <port>` |
| Live CLI | `soundcraft-cli app --port <port> <method or command id> [JSON]` |
| Headless command discovery | `soundcraft-cli commands --json`, `soundcraft-cli describe file.bounce_mix` |
| Headless edits | `soundcraft-cli run` or `script` (command scripts use one `ID JSON` per line) |

Use the authorized app's actual port and current `--help`; SoundCraft uses `--connect`, not EffectCraft's `--bridge`. Do not transfer other apps' port, authentication or envelope assumptions. Headless sessions do not change an existing GUI document. [CLI][cli]; [control connection][control].

Discover MCP `tools/list` before calls. Actual MCP names include `list_commands`, `execute`, `batch`, `inspect_session`, `new_session`, `open_session`, `save_session`, `import_audio`, `bounce_mix`. Obtain their live schemas; engine IDs such as `file.bounce_mix` are not MCP tool names. `batch` is ordered with optional `keep_going`; inspect every result after errors rather than assuming rollback. [MCP catalog][mcp].

## 2. Preserve alignment and session dependencies

1. Freeze the parent FilmCraft revision. Export an approved full-program voice/mix PCM WAV with leading silence preserved. Record timeline origin/offset, source hash, sample rate, channel layout, exact sample count and picture duration. Avoid lossy handoff codecs and implicit resampling.
2. Import at the agreed origin; inspect actual source/clip positions before processing. SoundCraft numeric positions are **samples**, not seconds; seconds use `{"seconds":x}`. Choose session sample rate deliberately and account for any conversion.
3. Apply only the approved processing. Keep clip positions and program length stable; independent removal of audio time breaks picture sync.
4. Save a new `.scraft` session and preserve its sibling `Audio Files/` bundle plus dependency/plugin versions and state. Reopen using `open_session`; require empty `missing` and inspect `sources[].loaded` with `inspect_session`. Live control also exposes `session.inspect {"detail":"full"}`. A saved JSON file or remembered plugin name alone is insufficient. [Session bundle][formats]; [inspection and positions][control]; [missing-media/save behavior][mcp].

## 3. Bounce an explicit PCM range

Source-confirmed **engine parameters** for `file.bounce_mix` (route through the discovered MCP `execute` schema or CLI/control wrapper, not a guessed tool envelope):

```json
{"path":"<absolute fresh run path>/processed.wav","format":"wav","bit_depth":24,"start":0,"end":480000,"source":"main","normalize":false,"dither":true}
```

Here `480000` is an illustrative **sample position**, ten seconds only at 48 kHz. Replace it with the exact agreed program-end sample; this is not a sample-rate setting. `file.bounce_stems` instead takes `dir` and range/format/depth/dither settings; do not copy mix-only fields into it. [Exact parameter contracts][bounce].

- Match the required sample rate, channels and sample count; preserve leading silence and explicit placement offset. WAV BWF TimeReference includes session timecode start plus bounce start, but automatic FilmCraft placement is **unvalidated**. Carry alignment metadata separately and check placement.
- Mix rendering emits the requested range length after calculated latency compensation. It does not automatically extend the range for audible tails. Include wanted decay within the approved duration or deliberately fade; changing picture duration requires a new editorial decision.
- Nonzero-start bounces construct a fresh mix engine: preceding reverb/delay/instrument history may be absent (source inference). Prefer full-program bounce from zero, or a documented preroll-and-trim trial. PDC implementation is not proof for the chosen plugin chain; verify transient alignment. Clip-effects consolidation's ten-second tail cap is a different path, not a mix-bounce guarantee. [Range/latency/tail implementation][offline].
- `normalize:true` performs **peak normalization to -0.1 dBFS**, not a requested LUFS target. Returned LUFS/true-peak measurements do not establish delivery compliance; measure the final FilmCraft mix. [Normalization and BWF implementation][io].
- Prefer one approved voice/mix replacement when sufficient. Independently soloed stems include sends/auxes; shared/nonlinear processing may not sum identically to the complete mix. [Stem implementation][stems].

SoundCraft has no AAF/OMF import/export or video bounce at this pin. No live FilmCraft link or transferable native insert chain was established. Use rendered PCM media, not a promised session/timeline round trip. [Interchange limits][formats].

## Strip Silence and plugins: separate decisions

`edit.strip_silence_preview` is a real **read-only** command, not a guessed `preview:true` flag. Its source-confirmed fields are `threshold_db`, `min_length_ms`, `pad_before_ms`, `pad_after_ms`, `tracks`, `start`, `end`. Defaults are -48 dB / 50 ms / 5 ms / 20 ms; inspect returned sample ranges and listen before applying matching settings. [Preview contract][strip].

`edit.strip_silence` modes keep nonsilent regions (`strip`), keep silent regions (`extract`), or split only (`separate`). They do **not ripple-close gaps**. This is level-based segmentation, not transcript/filler-word or retake detection. Preserve consonants, breaths and meaningful pauses; perform approved synchronized pacing cuts in FilmCraft. [Apply semantics][strip-apply].

Prefer built-ins. Loading/scanning third-party CLAP/VST3/AU plugins executes native code; ask consent first, even with filesystem roots. Hosting is in-process, AU is macOS-only, and plugin state belongs to the SoundCraft session. Hosted plugins are not AudioSuite processors; platform/editor and latency limitations require a specific trial. [Plugin constraints][plugins].

## Safety and blocking reimport trial

- Use fresh run-local paths. CLI protects explicit inputs unless `--in-place`, but unrelated existing outputs can be overwritten; MCP `save_session` separately requires `replace:true` to overwrite another existing file.
- Headless `--automation-read-root` and `--automation-write-root` grant **separate** access; saving needs authority for sibling media/backups too. Reopen needs read authority. `--connect` cannot combine with root flags; the desktop bridge is not confined. Roots do not sandbox plugin binaries. [CLI overwrite rules][cli]; [confinement][mcp].
- Inspect state/files after an ambiguous mutation failure before retrying.
- **Trial:** save → close/reopen → confirm media/plugin state → bounded PCM bounce to fresh path → independently check sample rate/count/channels, leading silence, latency, tails and listen → import/place in disposable FilmCraft revision → mute/replace the original exactly once → verify head/middle/tail sync, offsets, duration, final loudness and absence of doubled audio → human review. Record hashes, warnings, timings and correction effort. Until passed, report **source-inspected, reimport unvalidated**; command success is not listening/QC evidence.

[cli]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/docs/cli.md
[control]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/docs/control-protocol.md
[mcp]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/docs/mcp.md
[formats]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/docs/file-format-parity.md
[bounce]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/crates/engine/src/cmd/file.rs#L92-L112
[offline]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/crates/mix/src/offline.rs#L56-L147
[io]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/crates/engine/src/io.rs#L357-L454
[stems]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/crates/engine/src/io.rs#L588-L618
[strip]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/crates/engine/src/cmd/strip_silence.rs#L9-L48
[strip-apply]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/crates/engine/src/io/strip.rs#L93-L164
[plugins]: https://github.com/storytold/soundcraft/blob/a02d892f831f0a4e1220e0357c7b941030b9cd6f/docs/plugin-parity.md#L27-L55
