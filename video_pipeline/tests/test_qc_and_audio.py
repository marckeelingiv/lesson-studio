"""Synthetic defect & unit tests for Automated QC (qc.py) and Audio Mix / SRT (audio_mix.py)."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import cv2
import numpy as np

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from audio_mix import (  # noqa: E402
    AudioSfxCue,
    PictureLockRequiredError,
    export_srt,
    mix_locked_audio,
)
from qc import (  # noqa: E402
    ALLOWED_WAIVER_GATES,
    QCReport,
    QCWaiver,
    check_blank,
    check_captions,
    check_decode,
    check_eyes_mouth,
    check_fit,
    check_flash,
    check_frames_and_boxes,
    check_freeze,
    check_hold_sentence,
    check_loudness,
    check_margins,
    check_stability,
    check_stale,
    check_tail,
    run_qc,
    validate_waivers,
)
from schema import (  # noqa: E402
    KeepSegment,
    RemappedWord,
    TranscriptBundle,
    TranscriptSegment,
    WordTiming,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_textured_frame(
    width: int,
    height: int,
    frame_idx: int,
    base_bgr: tuple[int, int, int] = (62, 46, 36),
    animate: bool = True,
    with_face: bool = False,
    jitter_px: int = 0,
) -> np.ndarray:
    """Build deterministic textured BGR frame with high spatial variance (non-blank)."""
    frame = np.full((height, width, 3), base_bgr, dtype=np.uint8)
    shift_x = jitter_px if (jitter_px and frame_idx % 2 == 1) else 0
    for x in range(0, width, 40):
        cv2.line(frame, (x + shift_x, 0), (x + shift_x, height), (75, 88, 105), 1)
    for y in range(0, height, 40):
        cv2.line(frame, (0, y), (width, y), (70, 82, 98), 1)

    if animate:
        # Moving indicator bar prevents unintended freezedetect during clean clips
        bar_x = 40 + ((frame_idx * 9) % max(40, width - 120))
        cv2.rectangle(frame, (bar_x + shift_x, 30), (bar_x + 60 + shift_x, 70), (80, 190, 230), -1)

    if with_face:
        cx, cy = width // 2 + shift_x, height // 2
        # Peach skin oval (BGR)
        cv2.ellipse(frame, (cx, cy), (65, 82), 0, 0, 360, (160, 190, 230), -1)
        # Two dark eyes in upper half
        cv2.circle(frame, (cx - 24, cy - 18), 9, (35, 30, 28), -1)
        cv2.circle(frame, (cx + 24, cy - 18), 9, (35, 30, 28), -1)
        # Darker mouth in lower half
        cv2.ellipse(frame, (cx, cy + 28), (22, 8), 0, 0, 360, (60, 60, 130), -1)

    return frame


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int = 48000) -> Path:
    pcm16 = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())
    return path


def _sine_wave(duration_sec: float, freq: float = 330.0, amp: float = 0.25, sr: int = 48000) -> np.ndarray:
    t = np.arange(int(round(duration_sec * sr)), dtype=np.float64) / sr
    return (amp * np.sin(2.0 * math.pi * freq * t)).astype(np.float32)


def _encode_frames_and_audio(
    frames: list[np.ndarray],
    out_mp4: Path,
    fps: float = 30.0,
    audio_wav: Path | None = None,
) -> Path:
    h, w = frames[0].shape[:2]
    raw_bytes = b"".join(f.tobytes() for f in frames)
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{w}x{h}",
        "-r",
        f"{fps}",
        "-i",
        "pipe:0",
    ]
    if audio_wav is not None:
        cmd.extend(["-i", str(audio_wav)])
    cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-r", f"{fps}"])
    if audio_wav is not None:
        cmd.extend(["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest"])
    cmd.append(str(out_mp4))
    subprocess.run(cmd, input=raw_bytes, check=True, capture_output=True)
    return out_mp4


class TestCoreQCGates(unittest.TestCase):
    def test_flash_gate_clean_cut_vs_flash_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            fps = 30.0
            # Clean hard cut at t = 1.0s (frame 30): Scene A -> Scene B
            clean_frames = [
                _make_textured_frame(320, 180, i, base_bgr=(35, 45, 70), animate=True)
                for i in range(30)
            ] + [
                _make_textured_frame(320, 180, i, base_bgr=(65, 90, 80), animate=True)
                for i in range(30, 60)
            ]
            clean_mp4 = _encode_frames_and_audio(clean_frames, work / "clean_cut.mp4", fps=fps)
            res_pass = check_flash(clean_mp4, cut_timestamps=[1.0])
            self.assertTrue(res_pass.passed, res_pass.summary)

            # Forced fail 1: 1-frame white flash inserted at cut frame 30
            flash_frames = list(clean_frames)
            flash_frames[30] = np.full((180, 320, 3), 255, dtype=np.uint8)
            flash_mp4 = _encode_frames_and_audio(flash_frames, work / "flash_cut.mp4", fps=fps)
            res_fail = check_flash(flash_mp4, cut_timestamps=[1.0])
            self.assertFalse(res_fail.passed)
            self.assertGreaterEqual(len(res_fail.findings), 1)

            # Forced fail 2: 2-frame stray flash detected across full clip when cut_timestamps=[]
            flash2_frames = list(clean_frames)
            flash2_frames[15] = np.full((180, 320, 3), 245, dtype=np.uint8)
            flash2_frames[16] = np.full((180, 320, 3), 245, dtype=np.uint8)
            flash2_mp4 = _encode_frames_and_audio(flash2_frames, work / "flash2.mp4", fps=fps)
            res_fail_full = check_flash(flash2_mp4, cut_timestamps=[])
            self.assertFalse(res_fail_full.passed)

    def test_blank_gate_pass_and_forced_fail_black_and_white(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            clean_frames = [_make_textured_frame(320, 180, i) for i in range(30)]
            clean_mp4 = _encode_frames_and_audio(clean_frames, work / "clean.mp4")
            self.assertTrue(check_blank(clean_mp4).passed)

            # Forced fail A: 3 black frames (blackdetect + std < 2.0)
            black_frames = list(clean_frames)
            for idx in (10, 11, 12):
                black_frames[idx] = np.zeros((180, 320, 3), dtype=np.uint8)
            black_mp4 = _encode_frames_and_audio(black_frames, work / "black.mp4")
            res_black = check_blank(black_mp4)
            self.assertFalse(res_black.passed)

            # Forced fail B: solid gray/white non-black blank frames caught by variance check
            white_frames = list(clean_frames)
            for idx in (14, 15):
                white_frames[idx] = np.full((180, 320, 3), 235, dtype=np.uint8)
            white_mp4 = _encode_frames_and_audio(white_frames, work / "white_blank.mp4")
            res_white = check_blank(white_mp4)
            self.assertFalse(res_white.passed)
            self.assertTrue(any("variance" in str(f.details.get("source")) for f in res_white.findings))

    def test_fit_gate_pass_and_clipped_fail(self) -> None:
        ok_report = {"passed": True, "errors": [], "findings": [{"rule": "fit", "status": "pass"}]}
        ok_dom = {
            "width": 1920,
            "height": 1080,
            "elements": [
                {"id": "title", "x": 140, "y": 120, "width": 600, "height": 80, "scrollWidth": 580, "clientWidth": 600}
            ],
        }
        self.assertTrue(check_fit(ok_report, ok_dom).passed)

        bad_report = {"passed": False, "errors": [{"message": "Text overflow in card-1", "timestamp": 1.2}]}
        bad_dom = {
            "width": 1920,
            "height": 1080,
            "elements": [
                {"id": "card-1", "x": 120, "y": 120, "width": 300, "height": 60, "clipped": True},
                {"id": "code-box", "x": 120, "y": 240, "width": 400, "height": 80, "scrollWidth": 510, "clientWidth": 400},
            ],
        }
        res_fail = check_fit(bad_report, bad_dom)
        self.assertFalse(res_fail.passed)
        self.assertGreaterEqual(len(res_fail.findings), 3)

    def test_margin_gate_pass_and_safe_zone_violation(self) -> None:
        safe_dom = {
            "overlays": [
                {"id": "bg", "role": "background", "full_bleed": True, "x": 0, "y": 0, "width": 1920, "height": 1080},
                {"id": "lower_third", "x": 96, "y": 860, "width": 640, "height": 120},
            ],
            "captions": [
                {"id": "cap_1", "x": 360, "y": 920, "width": 1200, "height": 90},
            ],
        }
        self.assertTrue(check_margins(safe_dom, width=1920, height=1080, margin_ratio=0.05).passed)

        bad_dom = {
            "overlays": [{"id": "edge_card", "x": 20, "y": 80, "width": 400, "height": 120}],
            "captions": [{"id": "low_cap", "x": 360, "y": 960, "width": 1200, "height": 100}],
        }
        res_fail = check_margins(bad_dom, width=1920, height=1080, margin_ratio=0.05)
        self.assertFalse(res_fail.passed)
        self.assertEqual(len(res_fail.findings), 2)

    def test_eyes_mouth_gate_overlap_and_legal_waiver(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            face_frames = [
                _make_textured_frame(640, 360, i, animate=True, with_face=True)
                for i in range(30)
            ]
            face_mp4 = _encode_frames_and_audio(face_frames, work / "speaker.mp4", fps=30.0)

            # Face is centered at (320, 180) with bbox ~ (255, 98, 130, 164)
            safe_overlays = [{"id": "corner_badge", "x": 40, "y": 40, "width": 140, "height": 50, "start": 0.0, "end": 1.0}]
            res_pass = check_eyes_mouth(face_mp4, safe_overlays)
            self.assertTrue(res_pass.passed, res_pass.summary)
            self.assertGreater(res_pass.metrics["faces_detected"], 0)

            # Overlapping eyes/mouth fails without waiver
            covering_overlays = [{"id": "center_card", "x": 260, "y": 110, "width": 120, "height": 140, "start": 0.0, "end": 1.0}]
            res_fail = check_eyes_mouth(face_mp4, covering_overlays)
            self.assertFalse(res_fail.passed)

            # Same overlap with valid eyes_mouth_check waiver passes
            waiver = QCWaiver(
                gate="eyes_mouth_check",
                start=0.0,
                end=1.0,
                reason="Intentional full-frame diagram focus",
                approved_by="marc",
                timestamp="2026-11-23T23:00:00Z",
            )
            res_waived = check_eyes_mouth(face_mp4, covering_overlays, waivers=[waiver])
            self.assertTrue(res_waived.passed)
            self.assertGreater(len(res_waived.waived_findings), 0)

            # Non-face screen capture frame with center overlay passes (no face visible)
            screen_frames = [_make_textured_frame(640, 360, i, animate=True, with_face=False) for i in range(15)]
            screen_mp4 = _encode_frames_and_audio(screen_frames, work / "screen.mp4", fps=30.0)
            res_no_face = check_eyes_mouth(screen_mp4, covering_overlays)
            self.assertTrue(res_no_face.passed)
            self.assertEqual(res_no_face.metrics["faces_detected"], 0)

    def test_stale_gate_matching_vs_tampered_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            transcript = work / "transcript.json"
            otio = work / "timeline.otio"
            tokens = work / "tokens.css"
            transcript.write_text('{"text": "hello"}', encoding="utf-8")
            otio.write_text('{"OTIO_SCHEMA": "Timeline.1"}', encoding="utf-8")
            tokens.write_text(":root { --bg: #0f172a; }", encoding="utf-8")

            run_json = work / "run.json"
            payload = {
                "run_id": "run-001",
                "video_id": "lesson-01",
                "input_hashes": {
                    "transcript": {"path": str(transcript), "sha256": _sha256(transcript)},
                    "otio": {"path": str(otio), "sha256": _sha256(otio)},
                    "tokens": {"path": "tokens.css", "sha256": _sha256(tokens)},
                },
                "waivers": [],
            }
            run_json.write_text(json.dumps(payload), encoding="utf-8")
            self.assertTrue(check_stale(run_json).passed)

            # Tamper transcript without updating run.json -> must fail
            transcript.write_text('{"text": "edited transcript"}', encoding="utf-8")
            res_tampered = check_stale(run_json)
            self.assertFalse(res_tampered.passed)
            self.assertEqual(res_tampered.metrics["mismatches"], 1)

            # Delete tokens -> missing dependency must fail
            tokens.unlink()
            res_missing = check_stale(run_json)
            self.assertFalse(res_missing.passed)
            self.assertEqual(res_missing.metrics["missing"], 1)

    def test_hold_sentence_gate_clean_vs_mid_word_and_mid_sentence(self) -> None:
        bundle = TranscriptBundle(
            source_path="/tmp/src.mp4",
            duration=6.0,
            fps=30.0,
            width=1920,
            height=1080,
            segments=[
                TranscriptSegment(
                    id=0,
                    start=0.2,
                    end=1.5,
                    text="Open the table.",
                    words=[
                        WordTiming(word="Open", start=0.2, end=0.5),
                        WordTiming(word="the", start=0.55, end=0.75),
                        WordTiming(word="table.", start=0.80, end=1.40),
                    ],
                ),
                TranscriptSegment(
                    id=1,
                    start=1.50,
                    end=2.20,
                    text="Retake",
                    words=[WordTiming(word="Retake", start=1.50, end=2.10)],
                ),
                TranscriptSegment(
                    id=2,
                    start=2.80,
                    end=4.50,
                    text="Check the schema",
                    words=[
                        WordTiming(word="Check", start=2.80, end=3.10),
                        WordTiming(word="the", start=3.15, end=3.35),
                        WordTiming(word="schema", start=3.40, end=4.00),
                        WordTiming(word="now.", start=4.05, end=4.45),
                    ],
                ),
            ],
        )

        # Clean cuts: seg 0 ends after terminal '.', seg 1 starts after 0.70s pause gap
        clean_segs = [
            KeepSegment(id="k1", start=0.15, end=1.45),
            KeepSegment(id="k2", start=2.75, end=4.50),
        ]
        self.assertTrue(check_hold_sentence(clean_segs, bundle).passed)

        # Forced fail 1: mid-word slice inside 'table.' [0.80, 1.40]
        mid_word_segs = [
            KeepSegment(id="k1", start=0.15, end=1.10),
            KeepSegment(id="k2", start=2.75, end=4.50),
        ]
        res_mid_word = check_hold_sentence(mid_word_segs, bundle)
        self.assertFalse(res_mid_word.passed)

        # Forced fail 2: mid-sentence cut between 'the' [3.15..3.35] and 'schema' [3.40..4.00] (gap 0.05s < 0.25s, no '.')
        mid_sent_segs = [
            KeepSegment(id="k1", start=0.15, end=1.45),
            KeepSegment(id="k2", start=2.75, end=3.37),
        ]
        res_mid_sent = check_hold_sentence(mid_sent_segs, bundle)
        self.assertFalse(res_mid_sent.passed)

    def test_stability_gate_caption_drift_and_pixel_jitter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            # Video with static window [0.0..1.0] and jittered window [1.0..2.0]
            frames = [
                _make_textured_frame(320, 180, 0, animate=False, jitter_px=0)
                for _ in range(30)
            ] + [
                _make_textured_frame(320, 180, i, animate=False, jitter_px=4)
                for i in range(30, 60)
            ]
            vid_mp4 = _encode_frames_and_audio(frames, work / "stability.mp4", fps=30.0)

            # Fixed caption bottom-center anchor across variable width beats -> PASS
            stable_dom = {
                "captions": [
                    {"id": "c1", "x": 760, "y": 900, "width": 400, "height": 80},
                    {"id": "c2", "x": 660, "y": 900, "width": 600, "height": 80},
                ]
            }
            self.assertTrue(check_stability(vid_mp4, dom_manifest=stable_dom, plate_windows=[(0.05, 0.90)]).passed)

            # Forced fail A: drifting caption vertical anchor (jumps 24px)
            drifting_dom = {
                "captions": [
                    {"id": "c1", "x": 760, "y": 900, "width": 400, "height": 80},
                    {"id": "c2", "x": 760, "y": 924, "width": 400, "height": 80},
                ]
            }
            res_drift = check_stability(vid_mp4, dom_manifest=drifting_dom)
            self.assertFalse(res_drift.passed)

            # Forced fail B: static window with oscillating 4px pixel jitter
            res_jitter = check_stability(vid_mp4, dom_manifest=stable_dom, plate_windows=[(1.05, 1.95)])
            self.assertFalse(res_jitter.passed)

    def test_waiver_policy_rejects_illegal_gate_waivers(self) -> None:
        self.assertEqual(ALLOWED_WAIVER_GATES, frozenset({"eyes_mouth_check", "freeze_check"}))
        legal = [
            QCWaiver(
                gate="eyes_mouth_check",
                start=1.0,
                end=2.0,
                reason="Diagram reveal",
                approved_by="marc",
                timestamp="2026-11-23T23:00:00Z",
            ),
            QCWaiver(
                gate="freeze_check",
                start=2.0,
                end=4.0,
                reason="SQL reading hold",
                approved_by="marc",
                timestamp="2026-11-23T23:00:00Z",
            ),
        ]
        self.assertTrue(validate_waivers(legal).passed)

        illegal = [
            QCWaiver(
                gate="flash",
                start=1.0,
                end=1.1,
                reason="Try waiving flash",
                approved_by="agent",
                timestamp="2026-11-23T23:00:00Z",
            )
        ]
        res = validate_waivers(illegal)
        self.assertFalse(res.passed)


class TestDeliveryAndAudioMix(unittest.TestCase):
    def test_delivery_checks_and_run_qc_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            sr = 48000
            # 2.5s animated video + clean faded speech-like audio at ~-14 LUFS
            n_frames = 75
            frames = [_make_textured_frame(640, 360, i, animate=True) for i in range(n_frames)]

            audio = _sine_wave(2.5, freq=320.0, amp=0.28, sr=sr)
            # Apply clean 40ms fade-out before a cut at t=1.25s and at end
            cut_idx = int(1.25 * sr)
            fade_len = int(0.04 * sr)
            audio[cut_idx - fade_len : cut_idx] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
            audio[cut_idx : cut_idx + int(0.06 * sr)] = 0.0
            audio[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
            wav_path = _write_wav(work / "clean.wav", audio, sample_rate=sr)
            clean_mp4 = _encode_frames_and_audio(frames, work / "clean_delivery.mp4", fps=30.0, audio_wav=wav_path)

            # Mix via Picture-Locked audio_mix to hit exact -14 LUFS / <= -1.0 dBTP
            mixed_dir = work / "mixed"
            mix_res = mix_locked_audio(clean_mp4, mixed_dir, picture_locked=True)
            locked_mp4 = mix_res.final_mixed_path

            # Valid SRT matching timeline [0, 2.5]
            srt_path = export_srt(
                [
                    RemappedWord(text="Clean", startMs=100, endMs=450),
                    RemappedWord(text="delivery", startMs=460, endMs=900),
                    RemappedWord(text="audio.", startMs=910, endMs=1200),
                    RemappedWord(text="Ready.", startMs=1400, endMs=2100),
                ],
                work / "captions.srt",
            )

            run_json = work / "run.json"
            run_json.write_text(
                json.dumps(
                    {
                        "run_id": "deliv-1",
                        "video_id": "v1",
                        "input_hashes": {"video": {"path": str(locked_mp4), "sha256": _sha256(locked_mp4)}},
                        "waivers": [],
                    }
                ),
                encoding="utf-8",
            )

            qc_out = work / "qc_out"
            report = run_qc(
                locked_mp4,
                qc_out,
                delivery_mode=True,
                cut_timestamps=[1.25],
                run_json_path=run_json,
                srt_path=srt_path,
                sample_timestamps=[0.1, 1.25, 2.3],
            )
            self.assertTrue(report.passed, f"Failed gates: {report.failed_gates} -> {report.gates}")
            self.assertTrue((qc_out / "qc_report.json").exists())
            reloaded = QCReport.model_validate_json((qc_out / "qc_report.json").read_text(encoding="utf-8"))
            self.assertTrue(reloaded.passed)
            self.assertEqual(len(reloaded.gates["frames_and_boxes"].evidence), 3)
            for p in reloaded.gates["frames_and_boxes"].evidence:
                self.assertTrue(Path(p).exists())

            # Illegal waiver in run.json for `flash` MUST fail run_qc even on clean video
            bad_run_json = work / "bad_run.json"
            bad_run_json.write_text(
                json.dumps(
                    {
                        "run_id": "deliv-2",
                        "video_id": "v1",
                        "input_hashes": {"video": {"path": str(locked_mp4), "sha256": _sha256(locked_mp4)}},
                        "waivers": [
                            {
                                "gate": "flash",
                                "start": 0.5,
                                "end": 0.6,
                                "reason": "Illegal waiver test",
                                "approved_by": "test",
                                "timestamp": "2026-11-23T23:00:00Z",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            bad_report = run_qc(locked_mp4, work / "qc_bad", delivery_mode=False, run_json_path=bad_run_json)
            self.assertFalse(bad_report.passed)
            self.assertIn("waiver_policy", bad_report.failed_gates)

    def test_delivery_forced_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            sr = 48000

            # 1. Decode fail: video-only stream (no audio)
            frames = [_make_textured_frame(320, 180, i, animate=True) for i in range(30)]
            no_audio_mp4 = _encode_frames_and_audio(frames, work / "no_audio.mp4")
            self.assertFalse(check_decode(no_audio_mp4).passed)

            # 2. Tail check fail: abrupt -8 dBFS un-faded cut right at 1.0s
            abrupt_audio = _sine_wave(2.0, freq=400.0, amp=0.55, sr=sr)
            abrupt_wav = _write_wav(work / "abrupt.wav", abrupt_audio, sample_rate=sr)
            abrupt_mp4 = _encode_frames_and_audio(
                [_make_textured_frame(320, 180, i, animate=True) for i in range(60)],
                work / "abrupt.mp4",
                audio_wav=abrupt_wav,
            )
            res_tail = check_tail(abrupt_mp4, cut_timestamps=[1.0], max_tail_dbfs=-18.0)
            self.assertFalse(res_tail.passed)

            # 3. Freeze check fail vs freeze_check waiver pass
            frozen_frames = [_make_textured_frame(320, 180, 0, animate=False) for _ in range(75)]
            frozen_mp4 = _encode_frames_and_audio(frozen_frames, work / "frozen.mp4", fps=30.0, audio_wav=abrupt_wav)
            res_freeze_fail = check_freeze(frozen_mp4)
            self.assertFalse(res_freeze_fail.passed)
            freeze_waiver = QCWaiver(
                gate="freeze_check",
                start=0.0,
                end=2.5,
                reason="Intentional reading hold on SQL diagram",
                approved_by="marc",
                timestamp="2026-11-23T23:00:00Z",
            )
            self.assertTrue(check_freeze(frozen_mp4, waivers=[freeze_waiver]).passed)

            # 4. Captions check fails on overlapping timestamps and oversized line
            bad_srt = work / "bad.srt"
            bad_srt.write_text(
                "1\n00:00:00,000 --> 00:00:01,500\nThis line is definitely way too long for clean captions and exceeds forty-eight characters.\n\n"
                "2\n00:00:01,000 --> 00:00:03,500\nOverlapping cue\n",
                encoding="utf-8",
            )
            res_cap = check_captions(bad_srt, duration_sec=2.5)
            self.assertFalse(res_cap.passed)
            self.assertGreaterEqual(len(res_cap.findings), 3)

            # 5. Loudness fail: very quiet -36 LUFS audio
            quiet_audio = _sine_wave(2.0, freq=300.0, amp=0.02, sr=sr)
            quiet_wav = _write_wav(work / "quiet.wav", quiet_audio, sample_rate=sr)
            quiet_mp4 = _encode_frames_and_audio(
                [_make_textured_frame(320, 180, i, animate=True) for i in range(60)],
                work / "quiet.mp4",
                audio_wav=quiet_wav,
            )
            self.assertFalse(check_loudness(quiet_mp4, target_lufs=-14.0, max_true_peak=-1.0).passed)

            # 6. frames_and_boxes extracts evidence PNGs
            res_fb = check_frames_and_boxes(quiet_mp4, [0.2, 1.5], work / "fb_out")
            self.assertTrue(res_fb.passed)
            self.assertEqual(len(res_fb.evidence), 2)

    def test_audio_mix_guards_ducking_sfx_and_srt_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            sr = 48000
            frames = [_make_textured_frame(640, 360, i, animate=True) for i in range(120)]  # 4.0s
            dlg_audio = _sine_wave(4.0, freq=260.0, amp=0.12, sr=sr)
            dlg_wav = _write_wav(work / "dlg.wav", dlg_audio, sample_rate=sr)
            src_mp4 = _encode_frames_and_audio(frames, work / "locked_visuals.mp4", fps=30.0, audio_wav=dlg_wav)

            music_wav = _write_wav(work / "music.wav", _sine_wave(2.0, freq=140.0, amp=0.35, sr=sr), sample_rate=sr)
            sfx_wav = _write_wav(work / "pop.wav", _sine_wave(0.15, freq=880.0, amp=0.40, sr=sr), sample_rate=sr)

            # 1. Picture Lock guard rejects unlocked mixes before creating outputs
            unlocked_out = work / "unlocked_mix"
            with self.assertRaises(PictureLockRequiredError):
                mix_locked_audio(src_mp4, unlocked_out, picture_locked=False, music_path=music_wav)
            self.assertFalse(unlocked_out.exists())

            # 2. Reject dense <2s consecutive SFX cues
            dense_cues = [
                AudioSfxCue(path=sfx_wav, start_sec=0.5, trigger_type="motion_plate_reveal", gain_db=-14.0, reason="Reveal 1"),
                AudioSfxCue(path=sfx_wav, start_sec=1.9, trigger_type="ui_focus_click", gain_db=-14.0, reason="Too close"),
            ]
            with self.assertRaises(ValueError):
                mix_locked_audio(src_mp4, work / "dense", picture_locked=True, sfx_cues=dense_cues)

            # 3. Reject SFX louder than -12 dB below nominal voiceover
            loud_cues = [
                AudioSfxCue(path=sfx_wav, start_sec=0.5, trigger_type="motion_plate_reveal", gain_db=-6.0, reason="Too loud"),
            ]
            with self.assertRaises(ValueError):
                mix_locked_audio(src_mp4, work / "loud_sfx", picture_locked=True, sfx_cues=loud_cues)

            # 4. Reject forbidden trigger_type
            bad_trig = [
                AudioSfxCue(path=sfx_wav, start_sec=0.5, trigger_type="hard_cut", gain_db=-14.0, reason="Bad trigger"),
            ]
            with self.assertRaises(ValueError):
                mix_locked_audio(src_mp4, work / "bad_trig", picture_locked=True, sfx_cues=bad_trig)

            # 5. Valid locked mix with ducked music + spaced SFX hits -14 LUFS and retains dialogue_only.mp4
            valid_cues = [
                AudioSfxCue(path=sfx_wav, start_sec=0.6, trigger_type="section_boundary", gain_db=-14.0, reason="Chapter 1"),
                AudioSfxCue(path=sfx_wav, start_sec=2.8, trigger_type="motion_plate_reveal", gain_db=-15.0, reason="Architecture card"),
            ]
            mix_out = work / "valid_mix"
            res = mix_locked_audio(
                src_mp4,
                mix_out,
                picture_locked=True,
                music_path=music_wav,
                sfx_cues=valid_cues,
                target_lufs=-14.0,
                true_peak_dbtp=-1.0,
                sound_design_level=1,
            )
            self.assertTrue(res.dialogue_only_path.exists())
            self.assertTrue(res.final_mixed_path.exists())
            self.assertTrue(res.music_ducked)
            self.assertEqual(res.ducking_method, "sidechaincompress")
            self.assertTrue(res.loudness_gate.passed)
            self.assertAlmostEqual(res.measured_lufs, -14.0, delta=1.5)
            self.assertLessEqual(res.measured_true_peak_dbtp, -0.8)
            self.assertTrue(check_loudness(res.dialogue_only_path, target_lufs=-14.0, max_true_peak=-1.0).passed)

            # 6. export_srt produces clean zero-based SRT passing check_captions
            words = [
                RemappedWord(text="Today", startMs=100, endMs=380),
                RemappedWord(text="we", startMs=390, endMs=540),
                RemappedWord(text="verify", startMs=550, endMs=900),
                RemappedWord(text="deterministic", startMs=910, endMs=1450),
                RemappedWord(text="quality", startMs=1460, endMs=1850),
                RemappedWord(text="gates.", startMs=1860, endMs=2200),
                RemappedWord(text="Every", startMs=2300, endMs=2600),
                RemappedWord(text="caption", startMs=2610, endMs=3000),
                RemappedWord(text="stays", startMs=3010, endMs=3350),
                RemappedWord(text="anchored.", startMs=3360, endMs=3850),
            ]
            srt_file = export_srt(words, work / "out.srt", max_words_per_cue=6, max_chars_per_line=42)
            self.assertTrue(check_captions(srt_file, duration_sec=4.0, max_chars_per_line=42).passed)

            # Verify output sample rate is 48000 Hz via ffprobe
            probe_json = json.loads(
                subprocess.run(
                    ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(res.final_mixed_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            audio_streams = [s for s in probe_json["streams"] if s.get("codec_type") == "audio"]
            self.assertEqual(int(audio_streams[0]["sample_rate"]), 48000)

            # Corrupt MP4 must fail decode gate
            corrupt_mp4 = work / "corrupt.mp4"
            corrupt_mp4.write_bytes(b"not-a-valid-mp4-stream")
            self.assertFalse(check_decode(corrupt_mp4).passed)

            # Verify Haar cascade code path when cv2.CascadeClassifier is present (mocked)
            from unittest import mock

            class _FakeCascade:
                def __init__(self, path: str) -> None:
                    self.path = path

                def empty(self) -> bool:
                    return False

                def detectMultiScale(self, gray: np.ndarray, **kwargs: object) -> np.ndarray:
                    if "eye" in self.path:
                        return np.array([[15, 20, 18, 14], [55, 20, 18, 14]])
                    return np.array([[260, 110, 110, 140]])

            face_frames = [_make_textured_frame(640, 360, i, animate=True, with_face=True) for i in range(15)]
            face_mp4 = _encode_frames_and_audio(face_frames, work / "haar_face.mp4", fps=30.0)
            with mock.patch("qc._find_haarcascade_path", side_effect=lambda name: Path(name)), mock.patch.object(
                cv2, "CascadeClassifier", _FakeCascade, create=True
            ):
                res_haar_fail = check_eyes_mouth(
                    face_mp4,
                    overlay_boxes=[{"id": "occluding_box", "x": 270, "y": 125, "width": 80, "height": 50, "start": 0.0, "end": 0.5}],
                )
                self.assertFalse(res_haar_fail.passed)
                self.assertEqual(res_haar_fail.metrics["detector"], "haar_cascade")


if __name__ == "__main__":
    unittest.main()
