"""Unit and FFmpeg smoke tests for video_pipeline."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from assemble import assemble_rough_cut, remap_timeline  # noqa: E402
from cursor_events import CursorEvent, CursorEventLog, cues_from_cursor_log  # noqa: E402
from export_nle import export_fcpxml  # noqa: E402
from ingest import extract_audio, probe_video  # noqa: E402
from planner import build_edl_heuristic, generate_edl, sanitize_edl  # noqa: E402
from schema import (  # noqa: E402
    EditDecisionList,
    GraphicCue,
    KeepSegment,
    SilenceRegion,
    TimelineManifest,
    TranscriptBundle,
    TranscriptSegment,
    WordTiming,
)
from transcribe import detect_fillers, detect_retakes, detect_silences  # noqa: E402


class TestTranscriptAndPlanning(unittest.TestCase):
    def _sample_bundle(self) -> TranscriptBundle:
        seg0 = TranscriptSegment(
            id=0,
            start=0.2,
            end=1.4,
            text="So today we are",
            words=[
                WordTiming(word="So", start=0.2, end=0.5),
                WordTiming(word="today", start=0.5, end=0.9),
                WordTiming(word="we", start=0.9, end=1.1),
                WordTiming(word="are", start=1.1, end=1.4),
            ],
        )
        seg1 = TranscriptSegment(
            id=1,
            start=2.5,
            end=5.2,
            text="So today we are um building a pipeline",
            words=[
                WordTiming(word="So", start=2.5, end=2.7),
                WordTiming(word="today", start=2.7, end=3.1),
                WordTiming(word="we", start=3.1, end=3.3),
                WordTiming(word="are", start=3.3, end=3.5),
                WordTiming(word="um", start=3.5, end=3.8),
                WordTiming(word="building", start=3.8, end=4.4),
                WordTiming(word="a", start=4.4, end=4.6),
                WordTiming(word="pipeline", start=4.6, end=5.2),
            ],
        )
        return TranscriptBundle(
            source_path="/tmp/sample.mp4",
            duration=6.0,
            fps=30.0,
            width=1280,
            height=720,
            segments=[seg0, seg1],
            silences=[SilenceRegion(start=1.4, end=2.5, duration=1.1)],
        )

    def test_filler_and_retake_detection(self) -> None:
        bundle = self._sample_bundle()
        fillers = detect_fillers(bundle.segments)
        self.assertEqual([f.word for f in fillers], ["um"])

        retakes = detect_retakes(bundle.segments)
        self.assertEqual(len(retakes), 1)
        self.assertEqual(retakes[0].segment_id, 0)

    def test_heuristic_edl_and_remap(self) -> None:
        bundle = self._sample_bundle()
        bundle.fillers = detect_fillers(bundle.segments)
        bundle.retakes = detect_retakes(bundle.segments)

        edl = build_edl_heuristic(bundle)
        self.assertTrue(len(edl.kept_segments) >= 1)
        # Retake segment (0.2..1.4) + silence (1.4..2.5) should be excluded
        self.assertGreaterEqual(edl.kept_segments[0].start, 2.3)

        manifest = remap_timeline(bundle, edl, video_file="rough_cut.mp4")
        self.assertGreater(manifest.durationInFrames, 0)
        self.assertTrue(any(w.text == "pipeline" for w in manifest.captions))
        self.assertTrue(all(w.startMs < w.endMs for w in manifest.captions))

    def test_sanitize_edl_clamps_and_orders(self) -> None:
        edl = EditDecisionList(
            source_path="/tmp/sample.mp4",
            fps=30.0,
            width=1280,
            height=720,
            kept_segments=[
                KeepSegment(id="b", start=3.0, end=8.0),
                KeepSegment(id="a", start=-1.0, end=3.5),
            ],
            graphic_cues=[
                GraphicCue(id="g1", type="callout", start=1.0, duration=2.0, title="Valid"),
                GraphicCue(id="g2", type="callout", start=99.0, duration=2.0, title="OutOfBounds"),
            ],
        )
        clean = sanitize_edl(edl, duration=5.0)
        self.assertEqual(clean.kept_segments[0].start, 0.0)
        self.assertEqual(clean.kept_segments[0].end, 3.5)
        self.assertEqual(clean.kept_segments[1].start, 3.5)
        self.assertEqual(clean.kept_segments[1].end, 5.0)
        self.assertEqual([c.id for c in clean.graphic_cues], ["g1"])

    def test_fcpxml_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_xml = Path(tmp) / "timeline.fcpxml"
            edl = EditDecisionList(
                source_path="/tmp/sample.mp4",
                fps=30.0,
                width=1920,
                height=1080,
                kept_segments=[
                    KeepSegment(id="seg_01", start=0.0, end=2.0),
                    KeepSegment(id="seg_02", start=3.5, end=5.5),
                ],
                graphic_cues=[
                    GraphicCue(id="gfx_01", type="lower_third", start=0.5, duration=1.5, title="Intro"),
                ],
            )
            export_fcpxml(edl, out_xml)
            tree = ET.parse(out_xml)
            root = tree.getroot()
            self.assertEqual(root.tag, "fcpxml")
            clips = root.findall(".//asset-clip")
            self.assertEqual(len(clips), 2)
            markers = root.findall(".//marker")
            self.assertEqual(len(markers), 1)

    def test_spoken_retake_marker_detection(self) -> None:
        segments = [
            TranscriptSegment(id=0, start=0.0, end=1.8, text="So today we query the wrong table retake"),
            TranscriptSegment(id=1, start=2.2, end=4.0, text="Here is the pipeline metric."),
            TranscriptSegment(id=2, start=4.3, end=5.1, text="Scratch that."),
            TranscriptSegment(id=3, start=6.2, end=8.5, text="Here is the verified pipeline metric."),
        ]
        retakes = detect_retakes(segments)
        self.assertEqual([r.segment_id for r in retakes], [0, 1, 2])
        self.assertIn("spoken retake marker", retakes[0].reason)
        self.assertIn("precedes spoken retake marker", retakes[1].reason)

        bundle = TranscriptBundle(
            source_path="/tmp/sample.mp4",
            duration=9.0,
            fps=30.0,
            width=1920,
            height=1080,
            segments=segments,
            retakes=retakes,
        )
        edl = build_edl_heuristic(bundle)
        self.assertEqual(len(edl.kept_segments), 1)
        self.assertGreaterEqual(edl.kept_segments[0].start, 5.0)
        self.assertAlmostEqual(edl.kept_segments[0].end, 9.0)

    def test_pause_restart_retake_detection(self) -> None:
        segments = [
            TranscriptSegment(id=0, start=0.5, end=1.3, text="How does a"),
            TranscriptSegment(id=1, start=2.5, end=4.8, text="How does a purchase become an answer"),
        ]
        retakes = detect_retakes(segments)
        self.assertEqual([r.segment_id for r in retakes], [0])
        self.assertIn("1.2s gap", retakes[0].reason)

    def test_new_graphic_cue_types(self) -> None:
        cues = [
            GraphicCue(
                id="gfx_slide",
                type="slide_card",
                start=0.5,
                duration=3.0,
                title="Four steps",
                subtitle="Transcribe to Render",
                value="01 / ARCHITECTURE",
            ),
            GraphicCue(
                id="gfx_code",
                type="code_card",
                start=4.0,
                duration=3.5,
                title="cli.py",
                subtitle="Post-production CLI",
                value="uv --project video_pipeline run python video_pipeline/src/cli.py run take.mp4",
            ),
            GraphicCue(
                id="gfx_cursor",
                type="cursor_highlight",
                start=8.0,
                duration=2.0,
                title="Run query",
                x=0.72,
                y=0.38,
            ),
        ]
        edl = EditDecisionList(
            source_path="/tmp/sample.mp4",
            fps=30.0,
            width=1920,
            height=1080,
            kept_segments=[KeepSegment(id="seg_01", start=0.0, end=12.0)],
            graphic_cues=cues,
        )
        clean = sanitize_edl(edl, duration=12.0)
        self.assertEqual([c.type for c in clean.graphic_cues], ["slide_card", "code_card", "cursor_highlight"])
        self.assertEqual(clean.graphic_cues[2].x, 0.72)
        self.assertEqual(clean.graphic_cues[2].y, 0.38)

        manifest = TimelineManifest.model_validate_json(
            TimelineManifest(
                videoFile="rough_cut.mp4",
                fps=30.0,
                width=1920,
                height=1080,
                durationInFrames=360,
                graphicCues=clean.graphic_cues,
            ).model_dump_json()
        )
        self.assertEqual(len(manifest.graphicCues), 3)
        self.assertEqual(manifest.graphicCues[2].y, 0.38)

    def test_cursor_events_to_highlight_cues(self) -> None:
        log = CursorEventLog(
            width=1920,
            height=1080,
            events=[
                CursorEvent(t=0.9, x=0.20, y=0.30, kind="click", title="Aborted click"),
                CursorEvent(t=3.0, x=0.40, y=0.40, kind="move", title="Move only"),
                CursorEvent(t=3.5, x=0.55, y=0.62, kind="click", title="Open model"),
                CursorEvent(t=8.0, x=0.78, y=0.25, kind="click", title="Run query"),
            ],
        )
        kept = [
            KeepSegment(id="seg_01", start=2.5, end=6.0),
            KeepSegment(id="seg_02", start=7.0, end=10.0),
        ]
        cues = cues_from_cursor_log(log, kept)
        self.assertEqual(len(cues), 2)
        self.assertTrue(all(c.type == "cursor_highlight" for c in cues))
        self.assertEqual([c.title for c in cues], ["Open model", "Run query"])
        self.assertAlmostEqual(cues[0].start, 1.0)
        self.assertAlmostEqual(cues[0].x, 0.55)
        self.assertAlmostEqual(cues[0].y, 0.62)
        self.assertAlmostEqual(cues[1].start, 4.5)
        self.assertAlmostEqual(cues[1].x, 0.78)
        self.assertAlmostEqual(cues[1].y, 0.25)

    def test_separate_camera_track_manifest(self) -> None:
        bundle = self._sample_bundle()
        edl = EditDecisionList(
            source_path=bundle.source_path,
            camera_path="/tmp/camera.mp4",
            fps=bundle.fps,
            width=bundle.width,
            height=bundle.height,
            kept_segments=[KeepSegment(id="seg_01", start=2.5, end=5.2)],
        )
        manifest = remap_timeline(
            bundle,
            edl,
            video_file="rough_cut.mp4",
            camera_file="rough_camera.mp4",
        )
        self.assertEqual(manifest.videoFile, "rough_cut.mp4")
        self.assertEqual(manifest.cameraFile, "rough_camera.mp4")
        reloaded = TimelineManifest.model_validate_json(manifest.model_dump_json())
        self.assertEqual(reloaded.cameraFile, "rough_camera.mp4")


class TestFFmpegPipelineSmoke(unittest.TestCase):
    def test_ingest_silence_and_assemble_synthetic_clip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            raw_mp4 = work / "raw.mp4"
            # 1s tone + 1.5s silence + 1.5s tone = 4.0s clip
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=navy:s=640x360:r=30:d=4",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1[a0];aevalsrc=0:d=1.5[a1];sine=frequency=523:duration=1.5[a2];[a0][a1][a2]concat=n=3:v=0:a=1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                str(raw_mp4),
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            meta = probe_video(raw_mp4)
            self.assertEqual(meta.width, 640)
            self.assertEqual(meta.height, 360)
            self.assertTrue(meta.has_audio)
            self.assertAlmostEqual(meta.duration, 4.0, delta=0.2)

            wav = extract_audio(raw_mp4, work / "audio.wav")
            silences = detect_silences(wav, noise_db=-35.0, min_duration=0.6)
            self.assertEqual(len(silences), 1)
            self.assertGreater(silences[0].duration, 1.0)

            edl = EditDecisionList(
                source_path=str(raw_mp4),
                fps=meta.fps,
                width=meta.width,
                height=meta.height,
                kept_segments=[
                    KeepSegment(id="seg_01", start=0.0, end=1.0),
                    KeepSegment(id="seg_02", start=2.5, end=4.0),
                ],
            )
            rough = assemble_rough_cut(raw_mp4, edl, work / "rough_cut.mp4", has_audio=True)
            rough_meta = probe_video(rough)
            self.assertAlmostEqual(rough_meta.duration, 2.5, delta=0.2)

    def test_rehearsal_take_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            screen_mp4 = work / "screen.mp4"
            camera_mp4 = work / "camera.mp4"

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=slategray:s=640x360:r=30:d=6",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=6",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(screen_mp4),
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=darkgreen:s=320x180:r=30:d=6",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(camera_mp4),
                ],
                check=True,
                capture_output=True,
            )

            segments = [
                TranscriptSegment(
                    id=0,
                    start=0.2,
                    end=1.4,
                    text="We open the wrong file",
                    words=[
                        WordTiming(word="We", start=0.2, end=0.4),
                        WordTiming(word="open", start=0.4, end=0.7),
                        WordTiming(word="the", start=0.7, end=0.9),
                        WordTiming(word="wrong", start=0.9, end=1.1),
                        WordTiming(word="file", start=1.1, end=1.4),
                    ],
                ),
                TranscriptSegment(
                    id=1,
                    start=1.6,
                    end=2.2,
                    text="Scratch that.",
                    words=[
                        WordTiming(word="Scratch", start=1.6, end=1.9),
                        WordTiming(word="that.", start=1.9, end=2.2),
                    ],
                ),
                TranscriptSegment(
                    id=2,
                    start=3.0,
                    end=5.6,
                    text="We open the right pipeline file.",
                    words=[
                        WordTiming(word="We", start=3.0, end=3.3),
                        WordTiming(word="open", start=3.3, end=3.6),
                        WordTiming(word="the", start=3.6, end=3.8),
                        WordTiming(word="right", start=3.8, end=4.2),
                        WordTiming(word="pipeline", start=4.2, end=4.9),
                        WordTiming(word="file.", start=4.9, end=5.6),
                    ],
                ),
            ]
            retakes = detect_retakes(segments)
            self.assertEqual([r.segment_id for r in retakes], [0, 1])

            bundle = TranscriptBundle(
                source_path=str(screen_mp4),
                duration=6.0,
                fps=30.0,
                width=640,
                height=360,
                segments=segments,
                silences=[SilenceRegion(start=2.2, end=3.0, duration=0.8)],
                retakes=retakes,
            )
            cursor_log = CursorEventLog(
                width=640,
                height=360,
                events=[
                    CursorEvent(t=0.8, x=0.15, y=0.20, kind="click", title="Wrong click"),
                    CursorEvent(t=4.2, x=0.68, y=0.42, kind="click", title="Run query"),
                ],
            )

            edl = generate_edl(bundle, heuristic=True, cursor_log=cursor_log)
            self.assertEqual(len(edl.kept_segments), 1)
            self.assertGreaterEqual(edl.kept_segments[0].start, 2.8)
            cursor_cues = [c for c in edl.graphic_cues if c.type == "cursor_highlight"]
            self.assertEqual([c.title for c in cursor_cues], ["Run query"])

            rough_cut = assemble_rough_cut(
                screen_mp4,
                edl,
                work / "rough_cut.mp4",
                has_audio=True,
                normalize_audio=True,
            )
            rough_camera = assemble_rough_cut(
                camera_mp4,
                edl,
                work / "rough_camera.mp4",
                has_audio=False,
                normalize_audio=False,
            )

            fcpxml_path = export_fcpxml(edl, work / "timeline.fcpxml")
            tree = ET.parse(fcpxml_path)
            self.assertEqual(tree.getroot().tag, "fcpxml")

            manifest = remap_timeline(
                bundle,
                edl,
                video_file=rough_cut.name,
                camera_file=rough_camera.name,
            )
            self.assertEqual(manifest.videoFile, "rough_cut.mp4")
            self.assertEqual(manifest.cameraFile, "rough_camera.mp4")
            self.assertTrue(any(w.text == "pipeline" for w in manifest.captions))
            self.assertFalse(any(w.text == "wrong" for w in manifest.captions))
            self.assertTrue(any(c.type == "cursor_highlight" for c in manifest.graphicCues))

            expected_dur = sum(s.end - s.start for s in edl.kept_segments)
            rough_meta = probe_video(rough_cut)
            cam_meta = probe_video(rough_camera)
            self.assertTrue(rough_meta.has_audio)
            self.assertEqual(rough_meta.width, 640)
            self.assertEqual(rough_meta.height, 360)
            self.assertAlmostEqual(rough_meta.duration, expected_dur, delta=0.25)
            self.assertFalse(cam_meta.has_audio)
            self.assertEqual(cam_meta.width, 320)
            self.assertEqual(cam_meta.height, 180)
            self.assertAlmostEqual(cam_meta.duration, expected_dur, delta=0.25)


if __name__ == "__main__":
    unittest.main()
