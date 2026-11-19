# FilmCraft transcript command research

## Scope and provenance

**Static documentation/source/test inspection only.** No FilmCraft runtime, build, test execution, binary installation, model acquisition, project/config/media mutation, or visual/audio review was performed. The user PDF is a wishlist, not an API specification; none of the findings below depends on it.

- Task date: 2026-11-18. Retrieval host UTC clock: **2026-11-19T04:23:45Z** (the date difference is retained rather than silently backdating upstream evidence).
- Official upstream: <https://github.com/storytold/filmcraft>.
- FilmCraft pin: **`f67d38b35cc5af6853ef5a6921ccba014512694b`**, resolved from GitHub HEAD during research. GitHub reports commit time `2026-11-19T02:59:34Z`; retained response: [`upstream/commit.json`](upstream/commit.json). Retained recursive file inventory: [`upstream/tree.json`](upstream/tree.json).
- Its workspace pins `craft-timeline` to craft-libs **`3b8e426a260695af840a2cd79a064d40778f939e`**; see [`upstream/Cargo.toml`](upstream/Cargo.toml).
- Downloaded files are verbatim upstream text, not implementations authored here. Their URLs follow the exact mapping below.

### Evidence index and exact download URL mapping

For every FilmCraft file below, its URL is
`https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/<path after upstream/>`.
For the two craft-libs files, use
`https://raw.githubusercontent.com/storytold/craft-libs/3b8e426a260695af840a2cd79a064d40778f939e/<path after upstream/craft-libs/>`.

| Key | Local downloaded evidence | Relevant contents |
|---|---|---|
| D | [`upstream/docs/transcripts.md`](upstream/docs/transcripts.md) | Official transcript documentation, especially lines 21–103 |
| E | [`upstream/crates/engine/src/transcript.rs`](upstream/crates/engine/src/transcript.rs) | Actual command handlers and registered parameter descriptions |
| ET | [`upstream/crates/engine/src/transcript_tests.rs`](upstream/crates/engine/src/transcript_tests.rs) | Engine tests; fake transcriber, mutations, import and persistence |
| P | [`upstream/crates/project/src/transcript.rs`](upstream/crates/project/src/transcript.rs) | Serde shape, defaults, normalization, validation |
| X | [`upstream/crates/edit/src/transcript.rs`](upstream/crates/edit/src/transcript.rs) | Sequence mapping, matching, ranges, batch deletion, captions |
| XT | [`upstream/crates/edit/src/transcript/tests.rs`](upstream/crates/edit/src/transcript/tests.rs) | Deterministic mapping/range/caption tests |
| F | [`upstream/crates/edit/tests/fixtures/interview.transcript.json`](upstream/crates/edit/tests/fixtures/interview.transcript.json) | Actual tick-based test fixture |
| A | [`upstream/crates/edit/src/lib.rs`](upstream/crates/edit/src/lib.rs) | `lift` and `extract`, lines 392–418 |
| C | [`upstream/crates/engine/src/commands.rs`](upstream/crates/engine/src/commands.rs) | Track targeting/settings, sequence extract; lines 2732–2759 and 3617–3691 |
| T | [`upstream/crates/time/src/lib.rs`](upstream/crates/time/src/lib.rs), [`upstream/craft-libs/crates/timeline/src/time.rs`](upstream/craft-libs/crates/timeline/src/time.rs), [`upstream/craft-libs/crates/time/src/lib.rs`](upstream/craft-libs/crates/time/src/lib.rs) | Re-export chain to actual tick serde/conversion implementation |
| S | [`upstream/crates/speech/src/lib.rs`](upstream/crates/speech/src/lib.rs), [`upstream/crates/speech/README.md`](upstream/crates/speech/README.md) | Recognizer interface, sample rate, load/availability |
| W | [`upstream/crates/speech/src/whisper.rs`](upstream/crates/speech/src/whisper.rs), [`upstream/crates/speech/src/whisper/align.rs`](upstream/crates/speech/src/whisper/align.rs), [`upstream/crates/speech/src/whisper/model.rs`](upstream/crates/speech/src/whisper/model.rs) | Native Whisper, alignment, explicit `Device::Cpu` |
| V | [`upstream/crates/speech/src/vad.rs`](upstream/crates/speech/src/vad.rs), [`upstream/crates/speech/src/diarize.rs`](upstream/crates/speech/src/diarize.rs) | Audio-bound tightening and speaker clustering |
| M | [`upstream/crates/speech/src/models.rs`](upstream/crates/speech/src/models.rs) | Pinned model URLs, sizes, SHA-256, installed check and downloader |
| B | [`upstream/crates/speech/Cargo.toml`](upstream/crates/speech/Cargo.toml), [`upstream/crates/engine/Cargo.toml`](upstream/crates/engine/Cargo.toml), [`upstream/apps/filmcraft/Cargo.toml`](upstream/apps/filmcraft/Cargo.toml), [`upstream/apps/filmcraft-cli/Cargo.toml`](upstream/apps/filmcraft-cli/Cargo.toml) | Optional features, default empty feature sets |
| WT | [`upstream/crates/speech/tests/whisper_model.rs`](upstream/crates/speech/tests/whisper_model.rs) | Optional real-model test and skip conditions |
| CD | [`upstream/docs/captions.md`](upstream/docs/captions.md), [`upstream/crates/engine/src/captions.rs`](upstream/crates/engine/src/captions.rs) | Caption commands and sidecar-format documentation |

Direct official document URL: <https://raw.githubusercontent.com/storytold/filmcraft/f67d38b35cc5af6853ef5a6921ccba014512694b/docs/transcripts.md>.
Browsable pinned engine source: <https://github.com/storytold/filmcraft/blob/f67d38b35cc5af6853ef5a6921ccba014512694b/crates/engine/src/transcript.rs>.

## 1. `transcript.set`: exact shape and units

**Source verified:** E:221–236 deserializes the nested `transcript` directly as `Transcript`, normalizes/checks it, then stores it on the resolved underlying media item in one undoable edit. `item` is a numeric project media/subclip ID, not a filename, clip-placement ID or sequence ID. A subclip resolves to its parent media for storage.

This is a **command-parameter object**, not a claimed CLI/MCP transport envelope. Assuming existing media item ID `42`, this source-valid example stores “Hello” from media 1.0 to 1.5 seconds:

```json
{
  "item": 42,
  "transcript": {
    "language": "en",
    "source": "manual",
    "speakers": [{"name": "Presenter"}],
    "words": [
      {
        "text": "Hello",
        "start": 254016000000,
        "end": 381024000000,
        "speaker": 0,
        "confidence": 1.0
      }
    ]
  }
}
```

This example was **not executed**. The upstream engine test ET:132–150 actually supplies `{"item": item.0, "transcript": {"language":"en","words":[{"text":"b","start":2000,"end":3000,"speaker":1},{"text":"a","start":0,"end":1000}]}}`, then asserts sorting, generated speaker labels, default `"imported"` source and save/load persistence. Its tiny numbers are ticks, **not milliseconds**.

Units and conversion (T; P:15–29; S:29–43):

- `Tick` is a serde-transparent **signed 64-bit integer**. Send bare JSON integers, not `{"ticks":...}`, seconds, milliseconds, decimal seconds or timecode strings.
- **254,016,000,000 ticks = one second**. Native `Tick::from_seconds_f64(s)` computes `round(s * 254016000000)` then casts to `i64`.
- Prefer exact rational/integer conversion when original units are known: milliseconds × `254016000`; 16 kHz sample index × `15876000`; 48 kHz sample index × `5292000`. Frame tick duration uses `TICKS_PER_SECOND * den / num` for the actual rational frame rate; do not assume 30 fps for 30000/1001.
- JSON timestamps are **media time**, with `end` exclusive. They are not sequence-relative times. Inspect/search results, by contrast, expose **sequence-time ticks**.
- An excerpt-only external transcript must have the source excerpt offset added before import. Trim/speed mapping is performed later by X:62–100.
- JavaScript `Number` cannot represent every integer above `2^53-1` (about 9.85 hours at this tick rate); preserve exact integer serialization for long media. This is an integration precaution, not a tested FilmCraft failure.

P:71–164 establishes optional/default fields and normalization:

- `language`, `source`, `speakers`, `words` default if absent; empty `source` becomes `"imported"` in E.
- Each supplied word requires `text`, integer `start`, integer `end`; `speaker` is optional/null or zero-based `u32`, `confidence` defaults to `1.0`.
- Normalization drops blank words, trims text, sorts by `(start,end)`, clamps reversed ends up to starts, shortens overlaps, clamps confidence to 0–1 and supplies missing speaker labels. Indices >=1024 lose their speaker.
- Zero-duration words and negative timestamps are not rejected by the inspected `check`; no media-duration bounds check is present in `set`. Validate source bounds externally rather than assuming strict rejection.
- `set` replaces the media item's transcript; it does not merge word lists or edit media.

## 2. Read-only inspection versus immediate mutation

E:257–340, 380–431 and 466–522 provide these verified command names/parameter objects:

| Command | Parameter example | Effect |
|---|---|---|
| `transcript.inspect` | `{}` or `{"paragraphGapSeconds":1.5}` | Query; words with `i`, `text`, `start`, `end`, speaker name, clip/item IDs, confidence; paragraphs, speakers, current word and transcript-item summaries |
| `transcript.search` | `{"query":"you know"}` | Query; word-index matches and sequence tick bounds |
| `transcript.select` | `{"from":3,"to":4}` | **Mutates marks/playhead**, not media; `to` inclusive, defaults to `from`; outward frame-snapped range |
| `transcript.extract` | `{"from":3,"to":4}` | Immediate ripple edit of word frames |
| `transcript.lift` | `{"from":3,"to":4}` | Immediate edit, leaving a gap |
| `transcript.removeFillers` | `{"fillers":["um","uh","you know"]}` | Immediate bulk ripple edit |
| `transcript.removePauses` | `{"minSeconds":1.0,"keepSeconds":0.15}` | Immediate bulk ripple edit |
| `transcript.createCaptions` | `{"maxChars":42,"lines":2,"minSeconds":1.0,"maxSeconds":7.0,"gapFrames":0,"name":"Transcript","format":"Subtitle"}` | Immediate creation of a new caption track |

**No transcript-specific preview/dry-run/review/approval mode is registered or checked by either removal handler.** Both find ranges and immediately call `remove_ranges`, which enters `s.edit_sequence`. Do not send `{"preview":true}` or `{"dryRun":true}` expecting safety: these handlers never read those keys. There is no registered `transcript.findFillers` or `transcript.findPauses` engine query. Pure functions with those purposes exist in the edit crate, but that does not make them remotely callable.

Bulk response is `{"removed":n,"ticks":total,"seconds":totalSeconds}`, or `{"removed":0,"ticks":0}` when empty. `removed` is the **pre-merge range count**, not guaranteed to be the count of actual cuts; deletion merges touching/overlapping ranges first (E:380–386; X:291–316).

Algorithm details (X:151–288):

- Filler defaults: `um`, `uh`, `umm`, `uhm`, `erm`, `er`, `ah`, `hmm`, `mm`, `mhm`. An explicit `fillers` list **replaces** this list.
- Matching is lower-case with edge punctuation removed; phrases match whole words, longest first. Filler cuts snap to nearest frames and constrain boundaries against neighboring words.
- Search's **last query word may be a prefix**, unlike exact filler matching. A search for `"um"` can include a longer final word; manually verify candidates.
- Pause removal examines only gaps between consecutive transcript words, not leading/trailing silence or an independent waveform silence detector. It accepts gaps **at least** `minSeconds` (documentation says “longer than”); keeps `keepSeconds` at **each** edge and snaps inward. It does not impose an In/Out or per-speaker scope.
- A transcript gap is not proof of silence: omitted/misrecognized speech, another speaker, music or demonstrations can occupy it.
- `transcript.extract`/`select` word ranges snap **outward**, unlike the bulk filler-removal nearest/constrained algorithm. A reviewed `extract` of a filler is therefore not an exact reproduction of bulk filler removal.

## 3. Track scope: critical safety distinction

Source E:326–338, 380–405; X:304–316; A:392–418:

| Operation | A/V tracks affected | Captions |
|---|---|---|
| `transcript.lift` | Targeted **and unlocked** only; no gap closure | This underlying lift function does not modify caption tracks |
| `transcript.extract` | Unlocked tracks that are **targeted OR sync-locked** | Unlocked **sync-locked** caption tracks follow extraction |
| `removeFillers` / `removePauses` | **Every unlocked A/V track**, whether targeted or sync-locked or neither | Unlocked **sync-locked** caption tracks follow extraction |

Thus disabling targeting, or turning sync lock off, **does not protect an unlocked B-roll/music/screen track from bulk removal**. Locks protect it from the edit but may leave it out of sync with the rippled tracks. A/V linking is not a substitute for checking this policy. These source paths do not expose a per-call `tracks`/`items` scope for the bulk commands.

Track-setting parameter objects verified in C:3617–3691:

- `timeline.setTrack`: `{"track":"V1","locked":true}` or `{"track":"A1","syncLock":true}`.
- `timeline.setTargeting`: `{"track":"A1","targeted":true}` (likewise `"V1"`).
- These examples describe supported arguments, **not settings applied during this research**. Audit all tracks; setting one does not clear others.

The sequence word mapper (X:62–100) is independent of targeting: audio tracks top-first; upper transcribed clip coverage suppresses lower-track words by midpoint, even when they are different dialogue. Words map through source-in, timeline start and positive speed, are midpoint-selected and clamped to the placement. Disabled **clip items**, reverse, frame hold and nonpositive speed are skipped. Track-level mute/solo/enabled flags are **not consulted in this function**; do not assume the text exactly mirrors the monitored mix. Parent-media transcripts are still not resolved through subclip placements here, despite `set`/`generate` resolving their storage targets (D:98–99).

Additional source limitation: text extract/bulk removal calls the edit-crate extraction directly, whereas the ordinary `sequence.extract` handler additionally ripples sequence markers when the relevant state flag is set (C:2743–2754). Do not assume sequence-marker behavior is identical.

## 4. Captions

E:408–431 creates a **new** track at caption-track index 0, from the current derived sequence words; it returns `{"track":id,"captions":n}`. It does not simply export a subtitle file or update an existing track. Repeating it creates another track.

X:319–470 defaults to 42 characters/line, 2 lines, 1 s minimum, 7 s maximum, zero gap frames, and a 1 s caption-break pause. Breaks also use speaker change, line capacity and sentence punctuation after half-full. Times snap to frames; minimum duration extends into room after a block, bounded by the next caption; a single oversized word can exceed line capacity. These are layout heuristics, not a guarantee of editorial readability.

CD documents/implements caption listing, text/timing/style changes and file export (`captions.list`, `captions.setText`, `captions.setTimes`, `captions.setStyle`, `captions.export`). Caption tracks have separate `locked` and `syncLock` settings. SRT/WebVTT sidecars and burn-in are documented; **no caption export, font rendering, burn-in or interoperability was runtime-tested here**. Prefer making captions after approved structural cuts, then inspect actual rendered frames and listen before delivery.

## 5. Native Whisper, build features and model acquisition

**Documented and source-confirmed, not verified in any installed/released binary:**

- Native inference is pure Rust/candle on CPU (`Device::Cpu` in W model.rs:275), not an invocation of `whisper.cpp`, a Python package or a hosted transcription API.
- B has `default = []` in speech, engine, desktop and CLI manifests. Engine `whisper` enables speech inference; engine `speech-download` separately enables the downloader. Desktop/CLI `whisper` enables **both** engine features. D says these are not built for web.
- E disables `generate` without the feature or a host-installed transcriber, with “speech-to-text is not available in this build”; downloader availability is independently gated. A model being installed and a build supporting inference are different checks.
- `transcript.models {}` is a query exposing `available`, `default`, `dir`, and catalogue metadata including `installed`, `size`, license and source. `available` reports the compiled native backend, not necessarily a host-injected transcriber.
- Native loading checks installed model files before loading (S:121–134). `generate` itself **does not automatically download** a missing model. The engine download handler does not prompt: host code is instructed to show size/source/license and ask before invoking it (E:448–457). Never infer consent from invoking generation.
- Supported catalogue IDs: `whisper-tiny`, `whisper-base` (default), `whisper-small`; multilingual; no catalogue large/turbo/`.en` model. M retains exact sizes, pinned HF URLs and SHA-256s for each of `config.json`, `generation_config.json`, `tokenizer.json`, `model.safetensors`.
- Catalogue HF revisions: tiny `169d4a4341b33bc18d8881c4b69c2e104e1cc0af`; base `e37978b90ca9030d5170a5c07aadb050351a65bb`; small `973afd24965f72e36ca33b3055d56a652f456b4d`.
- Weights are not bundled. `models::installed` checks **size and SHA-256**, not merely file existence. Downloads use `.part` files, verify hashes/sizes, then rename. Destination is `<default_data_dir>/models/<id>/`; no particular user path was assumed here.
- Documented license: MIT OpenAI Whisper weights, HF conversion Apache-2.0. This reports upstream metadata, not independent legal analysis.

Exact registered parameter examples, **not executed and not authorized as next steps**:

```text
transcript.models         {}
transcript.downloadModel  {"model":"whisper-base"}
transcript.generate       {"items":[42],"model":"whisper-base","language":"en","diarize":true,"maxSpeakers":2}
```

E:88–109, 148–189: explicit item IDs resolve to media and deduplicate; otherwise generation uses project selection, otherwise enabled audio placements in the active sequence. It reads full media audio, downmixed/resampled to mono 16 kHz, not just a marked timeline excerpt. Generated transcripts overwrite those media entries in one undoable edit. Unspecified model/language/diarization follow current preferences; use explicit params for reproducibility. Generation is synchronous; its engine progress callback always continues.

## 6. Timing/recognition limits and test evidence

- W describes sequential 30 s windows, language detection from the first window, greedy timestamp decoding and cross-attention/DTW word alignment at **20 ms resolution**. Exact tick storage does **not** imply sample-accurate recognition boundaries.
- V refines bounds using audio energy and internal pauses of at least 200 ms. D explicitly warns that late starts inside continuous speech remain late; a preceding word can contain the next word's onset, and sentence-scale alignment errors are not repaired. This can clip speech in otherwise frame-exact cuts.
- Speaker labels use per-chunk MFCC-statistic clustering, not verified identity recognition. Review names and turn boundaries.
- Native words are constructed with `Word::new` (W:339), whose confidence defaults to 1.0 (P:39–42). Do not interpret every returned confidence of 1.0 as a calibrated recognition probability.
- ET tests import/save/load, word edits/undo, bulk mutation and captions using `FixedTranscriber`; XT tests synthetic mapping, nearest/inward/outward snapping, filler phrases, pause removal and caption layout. These are **inspected assertions, not passing test results from this machine**.
- WT's real tiny-model test is gated by the Whisper feature and local model/speech fixtures; missing either prints `SKIPPED`. It checks transcript invariants, media-length bounds and WER <25%, not word-boundary alignment accuracy. `FILMCRAFT_MODELS_DIR` is a test lookup mechanism; the inspected production `models_dir()` instead uses the application data directory.
- D reports an upstream 2026-10-01 measurement: tiny English 12.2% WER over 797 words, about 9.5 minutes on an Apple-silicon laptop CPU in release mode. This is **an upstream claim**, not local timing, broad quality validation or proof that filler/pause boundaries are safe.
- No evidence here establishes automatic retake selection, meaning-preserving deletion, batch approval gates, native preview proposals, production-ready audio joins or overlay placement.

## 7. Safe review-first recipe (recommendation, not a run log)

1. Keep source recordings immutable. Work only in a disposable project copy and authorized output workspace. Record the real binary version/build features/command descriptions before relying on this pinned-source research.
2. Query `transcript.models {}` if checking native capability; **stop for explicit approval** before any model download or build/install. Importing an existing, authorized external transcript via `transcript.set` needs neither Whisper nor model downloads.
3. Validate transcript time units, media IDs, offsets, word order/bounds, speakers and normalization changes. Save a recoverable baseline; `set` is a mutation.
4. Use `transcript.inspect {}` and searches to create a separate human-readable **proposal ledger** of candidate words/gaps with context, source/sequence tick times and keep/remove reasons. Derive pause proposals externally from consecutive words using the inspected algorithm if exact reproduction is needed; this is not a built-in preview endpoint. Search matches need exact-word checking.
5. Listen/watch each candidate with context. Protect demonstrations, intentional pauses and conversational fillers. Verify all A/V targeting, locks, sync locks and caption policy; retained background tracks can intentionally need matching ripple edits.
6. For each individually approved word cut, optionally `transcript.select {"from":i,"to":j}` to mark/playhead-review it, then `transcript.extract` only after approval. `select` is **not read-only** and creates outward-snapped marks. For approved pauses, manually mark/review a precise inward-snapped timeline interval and use ordinary sequence editing; do not pretend a word-index extract selects silence.
7. Reinspect after **every mutation**: word indices and sequence times are derived and can change. Do not apply a stale index ledger. Use right-to-left frozen ranges only in a separately verified editing implementation.
8. Avoid bulk `removeFillers`/`removePauses` in a review-first agent workflow unless the entire resulting cut set and every affected track have been explicitly approved and tested on the copy. There is no per-hit approval or preview flag in these handlers.
9. Review each audio join and synchronization, undo/adjust bad cuts, then create captions and review text/timing/readability in rendered frames. Save/reopen/export verification is a **future runtime acceptance test**, not something this report establishes.

**Bottom line:** external tick-based transcript import is source-defined and can bypass optional native inference. Native generation and caption construction exist, but bulk cleanup is immediate cross-track mutation with recognition-boundary limitations—not a review queue.
