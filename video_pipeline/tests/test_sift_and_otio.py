"""Unit and synthetic FFmpeg integration tests for sift.py and timeline_otio.py."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import numpy as np
import opentimelineio as otio

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cursor_events import CursorEvent, CursorEventLog  # noqa: E402
from ingest import probe_video  # noqa: E402
from schema import (  # noqa: E402
    EditDecisionList,
    GraphicCue,
    KeepSegment,
    TimelineManifest,
    TranscriptBundle,
    TranscriptSegment,
    WordTiming,
)
from sift import (  # noqa: E402
    TIER_A_FILLERS,
    TIER_B_FILLERS,
    audit_raw_audio_stutters,
    classify_retakes,
    detect_tiered_fillers,
    detect_visual_activity_holds,
    measure_adaptive_room_tone,
    protect_consonant_tail,
    run_scientific_sift,
    snap_to_frame,
)
from timeline_otio import (  # noqa: E402
    TRACK_AROLL_VIDEO,
    TRACK_CAMERA,
    TRACK_DIALOGUE,
    TRACK_MOTION_PLATES,
    TRACK_MUSIC,
    TRACK_SFX,
    edl_to_otio,
    export_nle,
    import_nle,
    load_otio,
    otio_to_edl,
    save_otio,
    source_to_edit_map,
)


def _write_pcm_wav(path: Path, samples: np.ndarray, sample_rate: int = 16000) -> Path:
    """Write float [-1, 1] mono samples to a 16-bit PCM WAV file."""
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return path


def _dbfs_to_amp(dbfs: float) -> float:
    return 10.0 ** (dbfs / 20.0)


def _tone(duration_sec: float, freq: float, dbfs: float, sr: int = 16000) -> np.ndarray:
    t = np.arange(int(round(duration_sec * sr)), dtype=np.float64) / sr
    # Multiply by sqrt(2) so RMS matches dbfs directly.
    return (_dbfs_to_amp(dbfs) * math.sqrt(2.0)) * np.sin(2.0 * math.pi * freq * t)


def _noise(duration_sec: float, dbfs: float, sr: int = 16000, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(round(duration_sec * sr))
    raw = rng.standard_normal(n)
    rms = float(np.sqrt(np.mean(raw**2))) or 1.0
    return raw * (_dbfs_to_amp(dbfs) / rms)


class TestAdaptiveRoomToneAndFrameMath(unittest.TestCase):
    def test_adaptive_room_tone_two_noise_floors(self) -> None:
        sr = 16000
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            # Quiet studio take: -60 dBFS noise floor + speech bursts at -18 dBFS
            quiet = _noise(4.0, -60.0, sr=sr, seed=1)
            quiet[int(1.0 * sr) : int(2.2 * sr)] += _tone(1.2, 220.0, -18.0, sr=sr)
            quiet_wav = _write_pcm_wav(tmp_dir / "quiet.wav", quiet, sr)

            # Noisy room take: -30 dBFS noise floor + speech bursts at -14 dBFS
            noisy = _noise(4.0, -30.0, sr=sr, seed=2)
            noisy[int(1.0 * sr) : int(2.2 * sr)] += _tone(1.2, 220.0, -14.0, sr=sr)
            noisy_wav = _write_pcm_wav(tmp_dir / "noisy.wav", noisy, sr)

            prof_q = measure_adaptive_room_tone(quiet_wav)
            prof_n = measure_adaptive_room_tone(noisy_wav)

            self.assertLess(prof_q.room_tone_dbfs, -55.0)
            self.assertGreater(prof_q.room_tone_dbfs, -66.0)
            self.assertGreater(prof_n.room_tone_dbfs, -35.0)
            self.assertLess(prof_n.room_tone_dbfs, -26.0)

            # Adaptive speech threshold must scale with the noise floor and stay < -12 dBFS
            self.assertGreater(prof_n.speech_threshold_dbfs, prof_q.speech_threshold_dbfs + 15.0)
            self.assertGreater(prof_n.speech_threshold_dbfs, prof_n.room_tone_dbfs)
            self.assertLessEqual(prof_n.speech_threshold_dbfs, -12.0)
            self.assertGreater(prof_q.speech_threshold_dbfs, prof_q.room_tone_dbfs)

            # Stereo 24-bit PCM WAV support
            stereo_24_path = tmp_dir / "stereo24.wav"
            stereo_l = _noise(1.0, -50.0, sr=sr, seed=3)
            stereo_r = _noise(1.0, -50.0, sr=sr, seed=4)
            interleaved = np.column_stack([stereo_l, stereo_r]).reshape(-1)
            ints = np.clip(interleaved * 8388607.0, -8388608, 8388607).astype("<i4")
            raw_bytes = ints.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
            with wave.open(str(stereo_24_path), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(3)
                wf.setframerate(sr)
                wf.writeframes(raw_bytes)
            prof_s24 = measure_adaptive_room_tone(stereo_24_path)
            self.assertGreater(prof_s24.room_tone_dbfs, -58.0)
            self.assertLess(prof_s24.room_tone_dbfs, -45.0)

    def test_snap_to_frame_modes(self) -> None:
        fps = 30.0
        # 1.015s lies between frame 30 (1.0s) and frame 31 (1.033333s)
        self.assertAlmostEqual(snap_to_frame(1.015, fps, "nearest"), 30 / 30.0, places=6)
        self.assertAlmostEqual(snap_to_frame(1.015, fps, "floor"), 30 / 30.0, places=6)
        self.assertAlmostEqual(snap_to_frame(1.015, fps, "ceil"), 31 / 30.0, places=6)
        # Exact grid points stay exact
        self.assertAlmostEqual(snap_to_frame(0.5, 24.0, "floor"), 0.5, places=6)
        self.assertAlmostEqual(snap_to_frame(0.5, 24.0, "ceil"), 0.5, places=6)
        # Rational 29.97 fps quantization
        snapped_2997 = snap_to_frame(1.001, 30000 / 1001, "nearest")
        self.assertAlmostEqual(snapped_2997 * (30000 / 1001), 30.0, places=6)
        with self.assertRaises(ValueError):
            snap_to_frame(1.0, 0.0)


class TestConsonantTailProtection(unittest.TestCase):
    def test_stdkp_tail_extended_while_non_stdkp_is_not(self) -> None:
        sr = 16000
        fps = 30.0
        # Base room tone at -65 dBFS over 3 seconds
        samples = _noise(3.0, -65.0, sr=sr, seed=7)
        # Word speech [0.50, 1.00]
        samples[int(0.50 * sr) : int(1.00 * sr)] += _tone(0.50, 260.0, -20.0, sr=sr)
        # Quiet consonant tail [-42 dBFS] extending from 1.00s to 1.15s
        samples[int(1.00 * sr) : int(1.15 * sr)] += _tone(0.15, 3200.0, -42.0, sr=sr)
        # Next word [2.00, 2.40]
        samples[int(2.00 * sr) : int(2.40 * sr)] += _tone(0.40, 240.0, -20.0, sr=sr)

        next_w = WordTiming(word="next", start=2.00, end=2.40)

        for token in ("cats,", "stop!", "worked.", "build?", "kick:"):
            word = WordTiming(word=token, start=0.50, end=1.00)
            cut_out, cut_in = protect_consonant_tail(
                samples=samples,
                sample_rate=sr,
                word=word,
                next_word=next_w,
                room_tone_dbfs=-65.0,
                fps=fps,
            )
            self.assertGreaterEqual(cut_out, 1.15, f"Expected tail extension for {token!r}")
            # Cut in-point placed 1 frame before next_word.start
            self.assertAlmostEqual(cut_in, snap_to_frame(2.00 - 1.0 / fps, fps, "floor"), places=6)
            # Both boundaries quantized to frame grid
            self.assertAlmostEqual(cut_out * fps, round(cut_out * fps), places=6)
            self.assertAlmostEqual(cut_in * fps, round(cut_in * fps), places=6)

        # Trailing vowel/non-target consonant does NOT trigger tail scan
        non_tail_word = WordTiming(word="car,", start=0.50, end=1.00)
        cut_out_non, _ = protect_consonant_tail(
            samples=samples,
            sample_rate=sr,
            word=non_tail_word,
            next_word=next_w,
            room_tone_dbfs=-65.0,
            fps=fps,
        )
        self.assertAlmostEqual(cut_out_non, 1.00, places=6)

    def test_ambiguous_tail_adds_safety_frames(self) -> None:
        sr = 16000
        fps = 30.0
        samples = _noise(3.0, -65.0, sr=sr, seed=8)
        samples[int(0.50 * sr) : int(1.00 * sr)] += _tone(0.50, 220.0, -20.0, sr=sr)
        # Tail energy stays above -50 dBFS across the full 0.35s cap -> ambiguous decay
        samples[int(1.00 * sr) : int(1.40 * sr)] += _tone(0.40, 3500.0, -40.0, sr=sr)

        word = WordTiming(word="tests", start=0.50, end=1.00)
        next_w = WordTiming(word="run", start=2.00, end=2.30)
        cut_out, cut_in = protect_consonant_tail(samples, sr, word, next_w, room_tone_dbfs=-65.0, fps=fps)

        # Must exceed the 0.35s scan cap by 2-3 safety frames
        self.assertGreaterEqual(cut_out, 1.35 + 2.0 / fps - 1e-6)
        self.assertLess(cut_out, cut_in)


class TestVisualActivityHolds(unittest.TestCase):
    def test_opencv_moving_pixels_cursor_and_declared_holds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mp4 = Path(tmp) / "screen_demo.mp4"
            # 0..2s static black, 2..4s moving white square, 4..6s static black
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:r=30:d=6",
                "-f",
                "lavfi",
                "-i",
                "color=c=white:s=32x32:r=30:d=6",
                "-filter_complex",
                "[0:v][1:v]overlay=x='if(between(t,2,4), (t-2)*120, 20)':y=100[v]",
                "-map",
                "[v]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(mp4),
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            gaps = [
                (0.2, 1.8),  # static -> unprotected
                (2.2, 3.8),  # moving pixels -> video_motion hold
                (4.2, 4.9),  # cursor click -> cursor hold
                (5.1, 5.8),  # declared reading hold -> declared hold
            ]
            cursor_log = CursorEventLog(
                width=320,
                height=240,
                events=[
                    CursorEvent(t=4.5, x=0.6, y=0.4, kind="click", title="Inspect SQL"),
                    CursorEvent(t=0.5, x=0.1, y=0.1, kind="move"),
                    CursorEvent(t=1.2, x=0.105, y=0.1, kind="move"),  # negligible < 0.02 travel
                ],
            )
            holds = detect_visual_activity_holds(
                video_path=mp4,
                gaps=gaps,
                cursor_log=cursor_log,
                declared_holds=[(5.0, 5.9)],
            )
            self.assertEqual(len(holds), 3)
            self.assertEqual(holds[0].source, "video_motion")
            self.assertAlmostEqual(holds[0].start, 2.2, places=3)
            self.assertEqual(holds[1].source, "cursor")
            self.assertEqual(holds[1].cursor_events_count, 1)
            self.assertEqual(holds[2].source, "declared")

            # Cursor move-only (> 0.02 travel) also protects a gap
            move_only_log = CursorEventLog(
                width=320,
                height=240,
                events=[
                    CursorEvent(t=0.4, x=0.1, y=0.1, kind="move"),
                    CursorEvent(t=1.4, x=0.3, y=0.1, kind="move"),
                ],
            )
            move_holds = detect_visual_activity_holds(video_path=None, gaps=[(0.2, 1.8)], cursor_log=move_only_log)
            self.assertEqual(len(move_holds), 1)
            self.assertEqual(move_holds[0].source, "cursor")


class TestRetakesAndTieredFillers(unittest.TestCase):
    def test_all_five_retake_categories(self) -> None:
        segments = [
            TranscriptSegment(id=0, start=0.0, end=1.0, text="Welcome to the"),
            TranscriptSegment(id=1, start=1.2, end=1.8, text="scratch that"),
            TranscriptSegment(id=2, start=2.0, end=3.5, text="Welcome to the pipeline."),
            TranscriptSegment(id=3, start=4.0, end=5.5, text="Open the config file"),
            TranscriptSegment(id=4, start=5.8, end=7.3, text="Open the schema file."),
            TranscriptSegment(
                id=5,
                start=8.0,
                end=10.5,
                text="Today we deploy the audio processing service cleanly to staging.",
            ),
            TranscriptSegment(
                id=6,
                start=11.5,
                end=14.5,
                text="Today we deploy the audio processing service reliably to staging with monitoring.",
            ),
            TranscriptSegment(id=7, start=15.0, end=16.5, text="First we compute the baseline noise"),
            TranscriptSegment(id=8, start=16.8, end=18.5, text="We start by measuring the baseline noise."),
            TranscriptSegment(id=9, start=19.0, end=20.2, text="Tests give confidence."),
            TranscriptSegment(id=10, start=20.4, end=21.6, text="Tests catch regressions."),
            TranscriptSegment(id=11, start=22.0, end=23.5, text="We move step by step through the trace."),
        ]

        audits = classify_retakes(segments)
        by_id = {item.segment_id: item for item in audits}

        # 1. Repeats -> auto_cut
        self.assertEqual(by_id[0].category, "Repeats")
        self.assertEqual(by_id[0].status, "auto_cut")
        self.assertEqual(by_id[1].category, "Repeats")
        self.assertEqual(by_id[1].status, "auto_cut")

        # 2. Replacements -> proposed
        self.assertEqual(by_id[3].category, "Replacements")
        self.assertEqual(by_id[3].status, "proposed")

        # 3. Reopens -> proposed
        self.assertEqual(by_id[5].category, "Reopens")
        self.assertEqual(by_id[5].status, "proposed")

        # 4. Rephrases -> proposed
        self.assertEqual(by_id[7].category, "Rephrases")
        self.assertEqual(by_id[7].status, "proposed")

        # 5. Exceptions -> preserved (parallel rhetorical sentences + deliberate repetition)
        self.assertEqual(by_id[9].category, "Exceptions")
        self.assertEqual(by_id[9].status, "preserved")
        self.assertEqual(by_id[11].category, "Exceptions")
        self.assertEqual(by_id[11].status, "preserved")

        # Additional spoken retake cues + intra-segment replacement + rephrase bridge + callback
        extra_segs = [
            TranscriptSegment(id=20, start=0.0, end=1.0, text="In this module"),
            TranscriptSegment(id=21, start=1.1, end=1.6, text="take two"),
            TranscriptSegment(id=22, start=2.0, end=3.0, text="Let me restart."),
            TranscriptSegment(id=23, start=3.1, end=4.0, text="Cut cut."),
            TranscriptSegment(id=24, start=4.1, end=5.0, text="Start over."),
            TranscriptSegment(id=25, start=5.1, end=6.0, text="Retake."),
            TranscriptSegment(id=26, start=6.5, end=8.0, text="Set the port to 3000 sorry 8080."),
            TranscriptSegment(id=27, start=8.5, end=9.5, text="The query runs slowly."),
            TranscriptSegment(id=28, start=9.6, end=11.0, text="In other words, latency is high."),
            TranscriptSegment(id=29, start=11.5, end=13.0, text="As I mentioned, frames align."),
        ]
        extra_by_id = {item.segment_id: item for item in classify_retakes(extra_segs)}
        for cue_id in (20, 21, 22, 23, 24, 25):
            self.assertEqual(extra_by_id[cue_id].category, "Repeats")
            self.assertEqual(extra_by_id[cue_id].status, "auto_cut")
        self.assertEqual(extra_by_id[26].category, "Replacements")
        self.assertEqual(extra_by_id[26].status, "proposed")
        self.assertEqual(extra_by_id[27].category, "Rephrases")
        self.assertEqual(extra_by_id[27].status, "proposed")
        self.assertEqual(extra_by_id[29].category, "Exceptions")
        self.assertEqual(extra_by_id[29].status, "preserved")

    def test_exact_25_word_tier_ab_split_and_stutters(self) -> None:
        self.assertEqual(len(TIER_A_FILLERS), 12)
        self.assertEqual(len(TIER_B_FILLERS), 13)
        self.assertEqual(len(set(TIER_A_FILLERS) | set(TIER_B_FILLERS)), 25)

        words: list[WordTiming] = []
        t = 0.2
        for entry in (*TIER_A_FILLERS, *TIER_B_FILLERS):
            parts = entry.split()
            for part in parts:
                words.append(WordTiming(word=part, start=round(t, 3), end=round(t + 0.18, 3)))
                t += 0.25
            t += 0.15

        seg = TranscriptSegment(
            id=0,
            start=0.0,
            end=t,
            text=" ".join(w.word for w in words),
            words=words,
        )
        items, stutters = detect_tiered_fillers([seg], wav_path=None)
        self.assertEqual(stutters, [])

        tier_a_found = [i for i in items if i.tier == "A"]
        tier_b_found = [i for i in items if i.tier == "B"]
        self.assertEqual({i.normalized for i in tier_a_found}, set(TIER_A_FILLERS))
        self.assertEqual({i.normalized for i in tier_b_found}, set(TIER_B_FILLERS))
        self.assertTrue(all(i.status == "auto_cut" and i.isolated for i in tier_a_found))
        self.assertTrue(all(i.status == "proposed" for i in tier_b_found))

        # Test raw audio stutter detection + continuous non-isolated Tier A gating
        sr = 16000
        with tempfile.TemporaryDirectory() as tmp:
            wav_path = Path(tmp) / "stutter.wav"
            samples = _noise(4.0, -60.0, sr=sr, seed=11)
            # Continuous un-paused speech across 0.5..1.1s ("I um go" tightly jammed)
            samples[int(0.50 * sr) : int(1.10 * sr)] += _tone(0.60, 210.0, -18.0, sr=sr)
            # Short un-transcribed stutter burst at 2.00..2.12s
            samples[int(2.00 * sr) : int(2.12 * sr)] += _tone(0.12, 300.0, -20.0, sr=sr)
            # Transcribed next word at 2.60..3.00s
            samples[int(2.60 * sr) : int(3.00 * sr)] += _tone(0.40, 210.0, -18.0, sr=sr)
            _write_pcm_wav(wav_path, samples, sr)

            segs = [
                TranscriptSegment(
                    id=0,
                    start=0.5,
                    end=1.1,
                    text="I um go",
                    words=[
                        WordTiming(word="I", start=0.50, end=0.70),
                        WordTiming(word="um", start=0.70, end=0.90),
                        WordTiming(word="go", start=0.90, end=1.10),
                    ],
                ),
                TranscriptSegment(
                    id=1,
                    start=2.6,
                    end=3.0,
                    text="now",
                    words=[WordTiming(word="now", start=2.60, end=3.00)],
                ),
            ]
            f_items, detected_stutters = detect_tiered_fillers(segs, wav_path=wav_path)
            self.assertEqual(len(f_items), 1)
            self.assertFalse(f_items[0].isolated)
            self.assertEqual(f_items[0].status, "proposed")

            self.assertTrue(len(detected_stutters) >= 1)
            self.assertTrue(
                any(1.90 <= s["start"] <= 2.15 and s["status"] == "proposed" for s in detected_stutters)
            )

            # Direct audit_raw_audio_stutters call check
            prof = measure_adaptive_room_tone(wav_path)
            direct_stutters = audit_raw_audio_stutters(wav_path, segs, prof)
            self.assertEqual(len(direct_stutters), len(detected_stutters))


class TestUniqueRemovedSecondsAndOTIO(unittest.TestCase):
    def test_overlapping_cuts_not_double_counted(self) -> None:
        sr = 16000
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            wav_path = tmp_dir / "take.wav"
            samples = _noise(6.0, -60.0, sr=sr, seed=21)
            # Retake speech 0.5..2.0 with overlapping "um" at 1.0..1.3
            samples[int(0.5 * sr) : int(2.0 * sr)] += _tone(1.5, 220.0, -20.0, sr=sr)
            # Clean take speech 3.5..5.5
            samples[int(3.5 * sr) : int(5.5 * sr)] += _tone(2.0, 220.0, -20.0, sr=sr)
            _write_pcm_wav(wav_path, samples, sr)

            bundle = TranscriptBundle(
                source_path=str(tmp_dir / "missing_placeholder.mp4"),
                duration=6.0,
                fps=30.0,
                width=1280,
                height=720,
                segments=[
                    TranscriptSegment(
                        id=0,
                        start=0.5,
                        end=2.0,
                        text="So today um we",
                        words=[
                            WordTiming(word="So", start=0.5, end=0.8),
                            WordTiming(word="today", start=0.8, end=1.0),
                            WordTiming(word="um", start=1.05, end=1.35),
                            WordTiming(word="we", start=1.4, end=2.0),
                        ],
                    ),
                    TranscriptSegment(
                        id=1,
                        start=3.5,
                        end=5.5,
                        text="So today we build it.",
                        words=[
                            WordTiming(word="So", start=3.5, end=3.8),
                            WordTiming(word="today", start=3.8, end=4.2),
                            WordTiming(word="we", start=4.2, end=4.5),
                            WordTiming(word="build", start=4.5, end=5.0),
                            WordTiming(word="it.", start=5.0, end=5.5),
                        ],
                    ),
                ],
            )
            result = run_scientific_sift(
                video_path=tmp_dir / "missing_placeholder.mp4",
                wav_path=wav_path,
                bundle=bundle,
                out_dir=tmp_dir / "out",
                assemble_video=False,
            )

            self.assertEqual(
                result.steps_executed,
                ["sync", "dead_space", "retakes_and_mistakes", "filler_words"],
            )
            naive_sum = sum(c.duration for c in result.cut_items if c.status == "auto_cut")
            self.assertGreater(naive_sum, result.unique_removed_seconds)
            self.assertAlmostEqual(
                result.duration_before - result.duration_after,
                result.unique_removed_seconds,
                places=4,
            )
            self.assertTrue(Path(result.cut_audit_path).exists())
            self.assertTrue(Path(result.edl_path).exists())
            self.assertTrue(Path(result.otio_path).exists())

    def test_otio_tracks_mapping_and_nle_round_trips(self) -> None:
        edl = EditDecisionList(
            source_path="/tmp/lesson_screen.mp4",
            camera_path="/tmp/lesson_camera.mp4",
            fps=30.0,
            width=1280,
            height=720,
            kept_segments=[
                KeepSegment(id="seg_01", start=1.0, end=3.0, reason="intro"),
                KeepSegment(id="seg_02", start=5.0, end=8.0, reason="demo"),
            ],
            graphic_cues=[
                GraphicCue(id="gfx_01", type="lower_third", start=0.5, duration=1.5, title="Author"),
                GraphicCue(id="gfx_02", type="callout", start=2.5, duration=2.0, title="Key Step"),
            ],
            captions_enabled=True,
            summary="Test rough cut",
        )
        beats = [
            {"id": "b1", "start": 0.5, "duration": 1.5, "title": "Opening Panel", "layout": "Panel"},
            {"id": "m1", "start": 0.0, "duration": 5.0, "title": "Ambient Bed", "track": "Music", "asset_path": "/tmp/bed.wav"},
            {"id": "s1", "start": 2.5, "duration": 0.5, "title": "Whoosh", "track": "SFX", "asset_path": "/tmp/whoosh.wav"},
        ]

        tl = edl_to_otio(edl, storyboard_beats=beats, name="TestLesson")
        track_names = [t.name for t in tl.tracks]
        self.assertEqual(
            track_names,
            [
                TRACK_AROLL_VIDEO,
                TRACK_CAMERA,
                TRACK_MOTION_PLATES,
                TRACK_DIALOGUE,
                TRACK_MUSIC,
                TRACK_SFX,
            ],
        )
        self.assertGreaterEqual(len(tl.tracks.markers), 2)

        # Verify all RationalTime values are frame-quantized at rate=30.0
        for track in tl.tracks:
            for item in track:
                sr_range = item.source_range
                self.assertIsNotNone(sr_range)
                self.assertEqual(sr_range.start_time.rate, 30.0)
                self.assertEqual(sr_range.duration.rate, 30.0)
                self.assertEqual(sr_range.start_time.value, round(sr_range.start_time.value))
                self.assertEqual(sr_range.duration.value, round(sr_range.duration.value))

        # Verify piecewise source-to-edit mapping (including with an inner Gap)
        mapping = source_to_edit_map(tl)
        self.assertEqual(len(mapping), 2)
        self.assertEqual(
            mapping[0],
            {
                "clip_id": "seg_01",
                "source_start": 1.0,
                "source_end": 3.0,
                "edit_start": 0.0,
                "edit_end": 2.0,
                "duration": 2.0,
            },
        )
        self.assertEqual(
            mapping[1],
            {
                "clip_id": "seg_02",
                "source_start": 5.0,
                "source_end": 8.0,
                "edit_start": 2.0,
                "edit_end": 5.0,
                "duration": 3.0,
            },
        )

        tl_with_gap = edl_to_otio(edl)
        tl_with_gap.tracks[0].insert(1, otio.schema.Gap(duration=otio.opentime.RationalTime(30, 30.0)))
        gap_map = source_to_edit_map(tl_with_gap)
        self.assertEqual(gap_map[1]["edit_start"], 3.0)
        self.assertEqual(gap_map[1]["edit_end"], 6.0)

        # Round-trip otio_to_edl
        edl_back = otio_to_edl(tl)
        self.assertEqual(edl_back.width, 1280)
        self.assertEqual(edl_back.height, 720)
        self.assertEqual(edl_back.camera_path, "/tmp/lesson_camera.mp4")
        self.assertEqual(len(edl_back.kept_segments), 2)
        self.assertEqual(edl_back.kept_segments[0].start, 1.0)
        self.assertEqual(edl_back.kept_segments[1].end, 8.0)
        self.assertEqual(len(edl_back.graphic_cues), 2)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            p_otio = save_otio(tl, tmp_dir / "timeline.otio")
            loaded = load_otio(p_otio)
            self.assertEqual([t.name for t in loaded.tracks], track_names)

            # Export and import all 3 formats (.otio, .fcpxml, .kdenlive)
            out_otio = export_nle(tl, tmp_dir / "out.otio", "otio")
            self.assertEqual(tl.metadata["last_nle_export"]["adapter"], "otio_json")

            out_fcpxml = export_nle(tl, tmp_dir / "out.fcpxml", "fcpxml")
            self.assertEqual(tl.metadata["last_nle_export"]["adapter"], "otio_fcpx_xml_lite_adapter")
            self.assertEqual(ET.fromstring(out_fcpxml.read_text(encoding="utf-8")).tag, "fcpxml")

            out_kden = export_nle(tl, tmp_dir / "out.kdenlive", "kdenlive")
            self.assertEqual(tl.metadata["last_nle_export"]["adapter"], "kdenlive")
            self.assertEqual(ET.fromstring(out_kden.read_text(encoding="utf-8")).tag, "mlt")

            for exported in (out_otio, out_fcpxml, out_kden):
                self.assertTrue(exported.exists())
                self.assertGreater(exported.stat().st_size, 0)
                imported = import_nle(exported)
                imported_edl = otio_to_edl(imported)
                self.assertEqual(len(imported_edl.kept_segments), 2)
                self.assertAlmostEqual(imported_edl.kept_segments[0].start, 1.0, places=2)
                self.assertAlmostEqual(imported_edl.kept_segments[1].end, 8.0, places=2)
                self.assertGreaterEqual(len(imported_edl.graphic_cues), 2)
                overridden = otio_to_edl(imported, width=3840, height=2160)
                self.assertEqual((overridden.width, overridden.height), (3840, 2160))

            # Verify clean FCPXML fallback when otio_fcpx_xml_lite_adapter fails
            tl_no_start = edl_to_otio(edl)
            tl_no_start.global_start_time = None
            fb_path = export_nle(tl_no_start, tmp_dir / "fallback_no_start.fcpxml", "fcpxml")
            self.assertTrue(fb_path.exists())
            self.assertEqual(tl_no_start.metadata["last_nle_export"]["adapter"], "export_nle.export_fcpxml")
            self.assertTrue(tl_no_start.metadata["last_nle_export"]["fallback_used"])
            self.assertEqual(ET.fromstring(fb_path.read_text(encoding="utf-8")).tag, "fcpxml")

            with patch("timeline_otio.otio.adapters.write_to_file", side_effect=otio.exceptions.OTIOError("boom")):
                fb_mock_path = export_nle(tl, tmp_dir / "fallback_mock.fcpxml", "fcpxml")
                self.assertTrue(fb_mock_path.exists())
                self.assertEqual(tl.metadata["last_nle_export"]["adapter"], "export_nle.export_fcpxml")
                self.assertTrue(tl.metadata["last_nle_export"]["fallback_used"])


class TestScientificSiftEndToEnd(unittest.TestCase):
    def test_full_sift_end_to_end_synthetic_mp4_wav(self) -> None:
        sr = 16000
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            src_mp4 = tmp_dir / "screen.mp4"
            cam_mp4 = tmp_dir / "camera.mp4"
            wav_path = tmp_dir / "audio.wav"
            out_dir = tmp_dir / "workspace"

            # Synthesize 7s audio:
            # 0.5..1.4: aborted retake + spoken cue ("So cats" -> "scratch that")
            # 1.6..2.9: dead space gap WITH moving pixels on screen (protected hold!)
            # 3.1..4.2: "um" (3.1..3.4) + "cats" (3.6..4.1) with -40dBFS consonant tail [4.10..4.22]
            # 4.22..5.5: quiet dead space (no visual activity -> cut!)
            # 5.5..6.6: "run fast."
            samples = _noise(7.0, -58.0, sr=sr, seed=99)
            samples[int(0.5 * sr) : int(1.4 * sr)] += _tone(0.9, 210.0, -20.0, sr=sr)
            samples[int(3.1 * sr) : int(3.4 * sr)] += _tone(0.3, 180.0, -22.0, sr=sr)
            samples[int(3.6 * sr) : int(4.1 * sr)] += _tone(0.5, 240.0, -18.0, sr=sr)
            samples[int(4.1 * sr) : int(4.22 * sr)] += _tone(0.12, 3400.0, -40.0, sr=sr)
            samples[int(5.5 * sr) : int(6.6 * sr)] += _tone(1.1, 220.0, -18.0, sr=sr)
            _write_pcm_wav(wav_path, samples, sr)

            # Synthesize 7s screen MP4 with moving square ONLY during 1.6..2.9s + audio muxed
            cmd_screen = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:r=30:d=7",
                "-f",
                "lavfi",
                "-i",
                "color=c=white:s=36x36:r=30:d=7",
                "-i",
                str(wav_path),
                "-filter_complex",
                "[0:v][1:v]overlay=x='if(between(t,1.6,2.9), (t-1.6)*140, 10)':y=90[v]",
                "-map",
                "[v]",
                "-map",
                "2:a",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(src_mp4),
            ]
            subprocess.run(cmd_screen, check=True, capture_output=True)

            # Synthesize 7s camera MP4 (video-only)
            cmd_cam = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=30:duration=7",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(cam_mp4),
            ]
            subprocess.run(cmd_cam, check=True, capture_output=True)

            bundle = TranscriptBundle(
                source_path=str(src_mp4),
                duration=7.0,
                fps=30.0,
                width=320,
                height=240,
                segments=[
                    TranscriptSegment(
                        id=0,
                        start=0.5,
                        end=0.9,
                        text="So cats",
                        words=[
                            WordTiming(word="So", start=0.5, end=0.7),
                            WordTiming(word="cats", start=0.7, end=0.9),
                        ],
                    ),
                    TranscriptSegment(
                        id=1,
                        start=1.0,
                        end=1.4,
                        text="scratch that",
                        words=[
                            WordTiming(word="scratch", start=1.0, end=1.2),
                            WordTiming(word="that", start=1.2, end=1.4),
                        ],
                    ),
                    TranscriptSegment(
                        id=2,
                        start=3.1,
                        end=4.1,
                        text="um cats",
                        words=[
                            WordTiming(word="um", start=3.1, end=3.4),
                            WordTiming(word="cats", start=3.6, end=4.1),
                        ],
                    ),
                    TranscriptSegment(
                        id=3,
                        start=5.5,
                        end=6.6,
                        text="run fast.",
                        words=[
                            WordTiming(word="run", start=5.5, end=6.0),
                            WordTiming(word="fast.", start=6.0, end=6.6),
                        ],
                    ),
                ],
            )

            res = run_scientific_sift(
                video_path=src_mp4,
                wav_path=wav_path,
                bundle=bundle,
                out_dir=out_dir,
                camera_path=cam_mp4,
                assemble_video=True,
            )

            self.assertEqual(
                res.steps_executed,
                ["sync", "dead_space", "retakes_and_mistakes", "filler_words"],
            )
            self.assertGreater(res.unique_removed_seconds, 1.5)
            self.assertLess(res.duration_after, res.duration_before)

            # Moving-pixel gap 1.4..3.1 must be protected and preserved in kept_segments
            self.assertTrue(any(h.source == "video_motion" and h.start <= 1.6 and h.end >= 2.9 for h in res.protected_holds))
            self.assertTrue(any(seg.start <= 1.6 and seg.end >= 2.9 for seg in res.kept_segments))

            # Check emitted files on disk
            audit_data = json.loads(Path(res.cut_audit_path).read_text(encoding="utf-8"))
            self.assertEqual(audit_data["steps_executed"], ["sync", "dead_space", "retakes_and_mistakes", "filler_words"])

            rough_mp4 = Path(res.rough_cut_video_path or "")
            rough_cam = Path(res.rough_camera_video_path or "")
            manifest_path = Path(res.timeline_manifest_path or "")
            self.assertTrue(rough_mp4.exists())
            self.assertTrue(rough_cam.exists())
            self.assertTrue(manifest_path.exists())

            rough_meta = probe_video(rough_mp4)
            cam_meta = probe_video(rough_cam)
            self.assertAlmostEqual(rough_meta.duration, res.duration_after, delta=0.25)
            self.assertAlmostEqual(cam_meta.duration, res.duration_after, delta=0.25)

            manifest = TimelineManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(any("cats" in w.text for w in manifest.captions))
            self.assertFalse(any(w.text == "um" for w in manifest.captions))
            self.assertEqual(manifest.videoFile, "rough_cut.mp4")
            self.assertEqual(manifest.cameraFile, "rough_camera.mp4")

            otio_loaded = load_otio(Path(res.otio_path))
            self.assertEqual(otio_loaded.tracks[0].name, TRACK_AROLL_VIDEO)
            self.assertEqual(len(otio_to_edl(otio_loaded).kept_segments), len(res.kept_segments))


if __name__ == "__main__":
    unittest.main()
