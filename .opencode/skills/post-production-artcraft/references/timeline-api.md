# FilmCraft timeline and treatment reference

Read this branch for placement/stream mapping, linked edits, retiming, zooms/highlights, camera grading, microphone processing or interchange fidelity. Use [filmcraft-api.md](filmcraft-api.md) for transport, discovery, project lifecycle and export operations; [handoff.md](handoff.md) owns authorization, evidence and acceptance.

**Evidence boundary:** official source at [`f67d38b35cc5af6853ef5a6921ccba014512694b`](https://github.com/storytold/filmcraft/tree/f67d38b35cc5af6853ef5a6921ccba014512694b), not a runtime-tested capability. Discover the installed build's commands, parameters and effects before mutation. Payloads below are illustrative, **not executed**; uppercase ID/index tokens stand for inspected/returned values, not literal strings or valid ready-to-send JSON. Use explicit targets rather than ambient selection.

## Placement, streams and identity

An **item** identifies imported project media; a **clip** is a timeline instance; track IDs, stream indices and graphic-layer indices are different addresses. Preserve item/source identity, selected stream and source interval through cuts; razor/overwrite can create new clip IDs.

```text
timeline.place {
  "item": ITEM_ID, "track": "V1", "audioTrack": "A1",
  "seconds": 0, "sourceIn": {"seconds": 0},
  "duration": {"seconds": 5},
  "video": true, "audio": true, "insert": false
}
```

- This places picture and **all available audio streams**, on consecutive audio tracks, adding tracks when needed. Stream-zero channel interpretation can produce additional clips before the remaining streams. Inspect the resulting tracks rather than assuming one audio clip per imported file.
- `audioTrack:"A2"` selects a destination, **not source stream 2**. `video:false` or an audio destination in `track` gives audio-only placement; `audio:false` gives picture only.
- `TrackItem.audio_stream` is a zero-based index into the media's **audio-stream vector**, not necessarily the container-global stream number. Default zero can be omitted from serialized JSON. Check `source_channels` as well.
- The inspected media model has one optional video stream and a vector of audio streams. `timeline.place` declares neither `audioStream` nor `videoStream`. Arbitrary multi-video-stream selection is **not established**; two OBS video streams in one container are not proven separable. Use separately supplied camera/screen files, or stop for an approved preparation route unless installed discovery and a sample prove selection. `clip.audioChannels` changes audio channel interpretation, not video selection.
- `project_inspect` / `sequence_inspect` are summaries: effect values are debug strings, keys are counts, and per-clip `audio_stream` / `source_channels` plus caption-track lists are absent in this snapshot. Verify stream maps and full key curves in a saved scratch `.fcproj`, then reopen; summary inspection alone cannot establish fidelity.

Sources: [placement implementation][placement], [media model][media], [track model][track], [inspection schema][inspection].

## Links, synchronization and locks

- Placement links picture/audio partners; audio-only multistream placement can also share a link. `clip.link` is a **toggle**, not “ensure linked.” Inspect before use/retry.
- `sequence.linkedSelection {"on":true}` controls linked selection. Explicit `timeline.move {"moves":[{"clip":CLIP_ID,"track":"V1","time":{"seconds":2}}],"linked":true}` moves linked partners by the same delta on their own tracks, **except locked partners stay behind**. A shared link is not a synchronization guarantee.
- `timeline.setTrack {"track":"A1","locked":false,"syncLock":true,"enabled":true,"muted":false}` separates edit protection (`locked`), ripple participation (`syncLock`) and output state (`enabled`/`muted`). Reinspect IDs after track insertion/reordering; A1/V1 are positional addresses.
- `clip.synchronize` supports `audio|in|out|timecode|marker`, explicit `clips` and `reference`; its `offset` is in **frames**. Audio synchronization uses waveform correlation (up to 30 minutes at 48 kHz); the inspected analyzer reads default source audio, not an arbitrary selected stream. Synchronizing and linking are separate operations.

Sources: [command registrations][commands], [linked-edit implementation][clip-ops], [audio synchronization][sync], [multicam analyzer][multicam].

## Clock, origins and post-ripple maps

| Quantity | Origin / conversion |
|---|---|
| Native time | Signed integer ticks; **254,016,000,000 ticks/second**. Timecode is a display, not a new clock. |
| Sequence `start`, `end`, playhead | Positions on the sequence timeline; record its origin separately from source timestamps/timecode. |
| `sourceIn`, `sourceOut` | Positions in source/media time, not elapsed time from the edited clip's start. |
| Placement frame objects | `sourceIn` uses the source rate; `duration` and placement time use the sequence rate. Start and end independently snap to the sequence grid. |
| Clip effect keys | Stored in **media time**. `effects.setParam.time` accepts **sequence ticks** and converts through `effect_time_at`. |
| Track mixer automation | **Sequence ticks**, unlike clip Volume/Panner keys stored in media time. |

For rational rate `N/D`, one frame is `254016000000 × D/N` ticks (30 fps: 8,467,200,000; 30000/1001 fps: 8,475,667,200). Use rational/integer calculations and the installed snap rule; record transcript/PTS offsets and rounding explicitly. Do not assume source rate equals sequence rate or source zero equals container timecode/first PTS. VFR requires verified presentation timing or a derivative map, not nominal-rate arithmetic.

At normal forward speed, `sourceTime = sourceIn + (sequenceTime − clip.start)`. For speed/reverse/holds use the engine mapping: `source_time_at` may freeze the source; `effect_time_at` lets effects continue through a hold unless Hold Filters is enabled.

**Ripple first, decorate second.** `edit.rippleDelete` expands links and closes actually uncovered spans, merged across affected tracks, right-to-left. Other sync-locked, unlocked tracks move only without conflicts; conflicts reject the cloned edit. Locked tracks stay. Summing selected clip lengths double-counts overlapping/linked material.

For surviving points, conceptual mapping is `newTime = oldTime − closedDurationBefore(oldTime)`; deleted points have no destination. Derive the **actual piecewise map from fresh inspections/source ranges after each edit**, including changed IDs, rather than trusting planned cut totals. Sequence markers follow only with `markers.rippleSequenceMarkers {"on":true}`; caption tracks have separate locks/sync-lock. Recheck overlays, captions, markers and track automation.

Sources: [clock][clock], [placement][placement], [source/effect mapping][track], [ripple implementation][ripple], [ripple tests][ripple-tests], [mixer][mixer].

## Zooms, transforms and highlights

Motion `position` is **sequence pixels**, `anchor` is **source pixels**, and `scale` is **percent**. Defaults center the source anchor and place it at sequence center. Source dimensions, pixel aspect ratio and scale-to-frame flags affect the final box; scale alone does not establish framing.

Illustrative 1920×1080 sequence, screen clip covering sequence seconds 1–2:

```text
effects.setParam {"clip":SCREEN_CLIP_ID,"effect":"motion","param":"position","value":[960,540]}
effects.setParam {"clip":SCREEN_CLIP_ID,"effect":"motion","param":"scale","value":100,"time":254016000000,"keyframe":true}
effects.setParam {"clip":SCREEN_CLIP_ID,"effect":"motion","param":"scale","value":140,"time":508032000000,"keyframe":true}
```

These are sequence-time inputs, not “one/two seconds after clip start.” Explicit times outside the clip remain outside it; omitted time uses the playhead clamped to the clip. `keyframe:true` writes a key at the mapped time. An unanimated static update may correctly return `keyframes:0`. `effects.addKeyframe` and `effects.toggleAnimation` are **non-idempotent toggles**; inspect state after ambiguous responses instead of blindly retrying. `effects.deleteKeyframe` requires stored **`mediaTime`**, not the preceding sequence-time input.

Native highlights are ordinary authored shapes, not inferred click locations or verified semantic target tracking:

```text
graphics.newShape {"shape":"rectangle","position":[960,540],"size":[600,120],"seconds":2,"track":1,"time":254016000000}
graphics.list {"clip":GRAPHIC_CLIP_ID}
graphics.set {"clip":GRAPHIC_CLIP_ID,"layer":LAYER_INDEX,"props":{"fill":false,"stroke":true,"stroke_color":"#ffff00","stroke_width":6}}
```

Graphics placement uses a **zero-based video-track index**: `track:1` means an inspected, existing V2 with a free, unlocked destination range. Unlike timeline commands, `"track":"V2"` is not parsed as an explicit graphic destination and can silently trigger automatic placement. An absent/out-of-range index can also select an automatic destination. Inspect the actual returned placement. Resolve the returned graphic/layer before setting properties. Shape position is its center in canvas pixels; paragraph text with `box` uses a top-left position. `graphics.list` exposes bounds/quads. Convert source content through clip transforms to canvas coordinates; application-window/screenshot coordinates are another space. Review actual frames for target bounds, legibility and occlusion; a successful command proves none of those.

Media-time clip keys stay with media after trims; a head trim advances source-in and moves their apparent offset from clip start. Responsive graphic intro/outro retiming remaps **layer** keys, not the graphic clip's own Motion/Opacity/mask keys.

Sources: [Motion definitions][effects], [render coordinate map][render], [parameter/keyframe commands][keyframes], [graphics coordinates and retiming][graphics], [graphic destination parsing][graphic-placement].

## Camera-only color

Discover `effects.list {"kind":"Video","detail":true}` for parameter IDs, ranges, units, choices and animatability. Apply `lumetri` to **explicit camera clip IDs**, then address the returned effect instance index:

```text
effects.apply {"clips":[CAMERA_CLIP_ID],"effect":"lumetri"}
effects.setParam {"clip":CAMERA_CLIP_ID,"effect":RETURNED_EFFECT_INDEX,"param":"exposure","value":0.2}
```

Exposure's hard range at this pin is −5…5. Discover other settings rather than guessing labels. After cuts, resolve every intended camera-source instance. A string effect ID addresses the first match; returned indices disambiguate repeated effects.

Clip-local correction is the narrow seam: global adjustment layers/sequence color can tint the screen/UI, while `clip.interpretFootage` changes source-item interpretation across instances. Give `clip` explicitly to Lumetri helpers. Compare frames containing camera **and** screen to verify isolation, not just improved skin tone.

Sources: [effect definitions][effects], [color commands][color].

## Microphone-only DSP, mix and loudness

- Native EQ, compressor, gate, look-ahead limiter, dehum, denoise, de-esser, dereverb, speech-enhance and routing implementations exist. Availability is source-backed; dialogue-repair quality is untested.
- Discover `effects.list {"kind":"Audio","detail":true}`. `effects.apply {"clips":[MIC_AUDIO_CLIP_ID],"effect":"parametric_eq"}` followed by `effects.setParam` uses **engine-discovered** parameter IDs/ranges, not DSP-internal field names. Applying audio effects to picture expands to linked audio; explicit mic audio targets avoid treating desktop/system audio.
- Essential Sound `setType`, `set`, `autoMatch`, `generateDucking` accept explicit `clips` but **expand linked audio targets when linked selection is enabled**, even for an explicit microphone ID. This differs from `effects.apply` on explicit audio IDs. Multistream placement can link microphone and system sound. For mic-only Essential Sound work, inspect linked partners and effective targets, record the prior linked-selection state, set `sequence.linkedSelection {"on":false}`, and pass only inspected mic audio IDs. Verify the resulting affected clips, then restore the prior state explicitly. Automatch/ducking change the edit; select them deliberately and review the result.
- Inspect routing first with `mixer.inspect`. Track-level processing is appropriate only when the strip actually contains the intended microphone signal:
  - `mixer.setStrip {"strip":"A1","volumeDb":-3,"pan":0,"muted":false,"solo":false,"output":"Mix"}`
  - `mixer.addInsert {"strip":"A1","effect":"compressor"}` → `mixer.setInsert` using returned `slot` and discovered `params`.
  - `mixer.setKeyframe {"strip":"A1","lane":"volume","time":254016000000,"value":-6}`; `mixer.writeAutomation` accepts `points:[[ticks,value],…]`. Track automation uses sequence time. Sends/submixes and pre/post-fader inserts exist; verify routing and latency rather than assuming unity behavior.
- **No `mixer.measure` endpoint is established.** Internal BS.1770-4 / EBU R128 meter code is not proof of an agent-callable analysis command. Discover a supported endpoint or use approved independent measurement.
- Export supports flat `loudnessLufs` or resolved `effects.loudness` settings (`enabled`, `targetLufs`, `truePeakDbtp`). The exporter measures the selected range, refines gain within bounds, limits true peaks and compensates look-ahead delay. Impossible targets can plateau; reports of input LUFS/applied gain do not establish achieved encoded-output compliance.

Listen across cuts and effect tails; check channel routing, sync, doubled mic/system feeds, latency and truncation. Independently measure **decoded delivered audio** for LUFS/true peak against the delivery specification and codec/tolerance policy.

Sources: [DSP catalog][dsp], [mixer implementation/API][mixer], [Essential Sound][essential], [export loudness implementation][loudness].

## Interchange boundary and targeted smoke coverage

Keep `.fcproj` as the editable master. Discover each intended export command (`file.exportEdl`, `file.exportFcp7Xml`, `file.exportFcpxml`, `file.exportOtio`, `file.exportAaf`, `file.exportOmf`) and inspect its loss `report`, not just success.

Graphics/adjustment layers do **not** round-trip faithfully through the cited formats. AAF/OMF lose unsupported picture/effects; OMF carries no video. Rendered effects/mixdowns can aid delivery but sacrifice editability. FCPXML nondefault video sources can be skipped; interchange does not prove arbitrary source-stream selection. Production parsers use `craft-libs`; their dependency implementations were not independently audited here. Official facade/docs are evidence, not third-party-editor round-trip tests.

Extend the [handoff capability sample](handoff.md#capability-gate-disposable-sample), rather than creating a second acceptance gate:

| Requested branch | Additional bounded evidence |
|---|---|
| Multistream placement / links | Identifiable mic/system streams; saved/reopened vector/channel mapping; move/trim partner deltas; locked-partner divergence and undo. Prove required multi-video selection or mark blocked. |
| Ripple / zoom / graphics | Known middle deletion with fresh source-to-edit map; conflicting-ripple no-mutation check; keys/bounds before and after cut/head trim; rendered frames before/during/after treatment. |
| Grade / DSP / delivery | Camera changes while screen stays unaffected; selected mic only; listening/routing/tails; independent encoded LUFS/true peak. |
| Interchange | Intended format's loss report plus scratch reimport comparison of source ranges, timing, links and streams; retain native master. |

Sources: [interchange limitations][interchange], [engine interchange facade][interchange-engine]. All smoke checks above remain **unperformed** until recorded against the installed runtime.

[commands]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/commands.rs
[placement]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/commands.rs#L1174-L1502
[inspection]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/commands.rs#L5268-L5302
[media]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/media/src/lib.rs#L170-L257
[track]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/project/src/track.rs
[clip-ops]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/clip_ops.rs
[sync]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/sync.rs
[multicam]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/multicam.rs#L363-L468
[clock]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/time/src/lib.rs
[ripple]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/edit/src/lib.rs#L429-L527
[ripple-tests]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/ripple_delete_tests.rs
[effects]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/project/src/effect.rs
[render]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/render/src/lib.rs#L472-L510
[keyframes]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/commands.rs#L3793-L3985
[graphics]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/graphics.md#L105-L207
[graphic-placement]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/graphics.rs#L117-L171
[color]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/color.rs
[dsp]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/audio-dsp/README.md#L19-L98
[mixer]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/mixer.rs
[essential]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/essential_sound.rs
[loudness]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/export/src/audio_out.rs#L19-L140
[interchange]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/interchange/README.md#L45-L115
[interchange-engine]: https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/interchange.rs
