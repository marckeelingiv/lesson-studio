"""Integration and asset-contract tests for HyperFrames Starter Asset Pack v0.1."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "video_pipeline" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from hyperframes_bridge import (  # noqa: E402
    compile_hyperframes_project,
    render_contact_sheet,
    render_hyperframes_video,
    run_hyperframes_check,
    run_hyperframes_lint,
)

ASSETS_DIR = REPO_ROOT / "editing_system" / "assets"

EXPECTED_ASSET_FILES = [
    "layouts/layouts.css",
    "layouts/full-screen.html",
    "layouts/panel.html",
    "layouts/centre.html",
    "layouts/full-graphic.html",
    "layouts/circle.html",
    "frameworks/frameworks.css",
    "frameworks/linear-steps.html",
    "frameworks/non-linear-pillars.html",
    "frameworks/cyclical-loop.html",
    "frameworks/hierarchical-tree.html",
    "frameworks/matrix-2x2.html",
    "heroes/engineering-section-deck.css",
    "heroes/engineering-section-deck.html",
    "motion/mechanics.js",
    "motion/transitions.css",
]

HARDCODED_COLOR_RE = re.compile(r"(#[0-9a-fA-F]{3,8}\b|\brgba?\s*\(|\bhsla?\s*\()")
CSS_TRANSITION_RE = re.compile(r"\btransition(?:-property|-duration|-delay)?\s*:")
NEON_SLOP_RE = re.compile(r"radial-gradient\s*\(|box-shadow\s*:[^;]*(?:blur|glow|0\s+0\s+\d+px)", re.IGNORECASE)
NON_DETERMINISTIC_RE = re.compile(r"\b(?:Math\.random|Date\.now|performance\.now)\s*\(")


def _sample_manifest(duration_sec: float = 12.0, video_file: str = "rough_cut.mp4") -> dict:
    return {
        "videoFile": video_file,
        "cameraFile": None,
        "fps": 30.0,
        "width": 1920,
        "height": 1080,
        "durationInFrames": int(round(duration_sec * 30.0)),
        "captionsEnabled": True,
        "captions": [
            {"text": "First", "startMs": 100, "endMs": 450},
            {"text": "verify", "startMs": 460, "endMs": 850},
            {"text": "safe", "startMs": 860, "endMs": 1200},
            {"text": "zones.", "startMs": 1210, "endMs": 1700},
            {"text": "Then", "startMs": 2200, "endMs": 2600},
            {"text": "render", "startMs": 2610, "endMs": 3100},
            {"text": "the", "startMs": 3110, "endMs": 3350},
            {"text": "deck.", "startMs": 3360, "endMs": 4000},
        ],
        "graphicCues": [],
    }


def _dark_storyboard() -> dict:
    return {
        "title": "Lesson Studio Starter Asset Pack Integration",
        "theme": "dark",
        "beats": [
            {
                "id": "beat-01",
                "start": 0.0,
                "duration": 2.0,
                "scene_layout": "full-screen",
                "title": "Measure Before Tuning",
                "subtitle": "Traces show real bottlenecks.",
                "transition": "subtle",
                "asset_ids": ["lay-full-screen", "mot-starter-transitions"],
                "visual_data": {"kicker": "THESIS"},
            },
            {
                "id": "beat-02",
                "start": 2.0,
                "duration": 2.0,
                "scene_layout": "panel",
                "title": "Split Speaker and Evidence",
                "subtitle": "Keep panels clear of captions.",
                "items": ["Frame speaker cleanly", "Align evidence cards"],
                "transition": "swipe",
                "asset_ids": ["lay-panel"],
                "visual_data": {"speakerSide": "left"},
            },
            {
                "id": "beat-03",
                "start": 4.0,
                "duration": 2.0,
                "scene_layout": "centre",
                "title": "Ad-Hoc vs Gated",
                "items": ["Manual cuts clip tails", "Automated QC blocks drift"],
                "transition": "none",
                "asset_ids": ["lay-centre"],
            },
            {
                "id": "beat-04",
                "start": 6.0,
                "duration": 2.0,
                "scene_layout": "full-graphic",
                "title": "Four Stage Flow",
                "items": [
                    "Ingest:Probe streams",
                    "Sift:Guard tails",
                    "Storyboard:Map beats",
                    "Verify:Run QC",
                ],
                "transition": "zoom",
                "asset_ids": ["lay-full-graphic", "fw-linear-steps"],
                "visual_data": {"framework": "linear-steps", "activeStep": 2},
            },
            {
                "id": "beat-05",
                "start": 8.0,
                "duration": 2.0,
                "scene_layout": "full-graphic",
                "title": "Lesson Chapters",
                "transition": "none",
                "asset_ids": ["hero-engineering-section-deck"],
                "visual_data": {
                    "hero": "engineering-section-deck",
                    "activeIndex": 2,
                    "chapters": [
                        {"num": "01", "title": "Ingest", "summary": "Extract 16kHz audio."},
                        {"num": "02", "title": "Sift", "summary": "Trim dead pauses."},
                        {"num": "03", "title": "Compose", "summary": "Render HyperFrames."},
                        {"num": "04", "title": "Deliver", "summary": "Check LUFS and tails."},
                    ],
                },
            },
            {
                "id": "beat-06",
                "start": 10.0,
                "duration": 2.0,
                "scene_layout": "circle",
                "title": "Live Trace Walkthrough",
                "subtitle": "Corner PiP keeps stage clear.",
                "body": "Pipeline Telemetry View",
                "transition": "none",
                "asset_ids": ["lay-circle"],
                "visual_data": {"pipCorner": "bottom-right"},
            },
        ],
    }


def _light_frameworks_storyboard() -> dict:
    return {
        "title": "Light Theme Frameworks Verification",
        "theme": "light",
        "beats": [
            {
                "id": "fw-pillars",
                "start": 0.0,
                "duration": 2.0,
                "scene_layout": "full-graphic",
                "title": "Two Engine Rooms",
                "items": [
                    "Rules:Static craft invariants",
                    "Brief:Tone and anchors",
                    "Catalog:Reusable templates",
                ],
                "transition": "subtle",
                "asset_ids": ["fw-non-linear-pillars"],
                "visual_data": {"framework": "non-linear-pillars", "hubTitle": "Shared Core"},
            },
            {
                "id": "fw-cycle",
                "start": 2.0,
                "duration": 2.0,
                "scene_layout": "full-graphic",
                "title": "Review Feedback Cycle",
                "items": [
                    "Plan:Map beats",
                    "Stills:Inspect sheet",
                    "Check:Verify contrast",
                    "Log:Capture taste",
                ],
                "transition": "none",
                "asset_ids": ["fw-cyclical-loop"],
                "visual_data": {"framework": "cyclical-loop"},
            },
            {
                "id": "fw-tree",
                "start": 4.0,
                "duration": 2.0,
                "scene_layout": "full-graphic",
                "title": "OTIO Track Structure",
                "items": [
                    "Video:A-Roll stream",
                    "Overlay:Motion Plates",
                    "Audio:Speech + Bed",
                ],
                "transition": "none",
                "asset_ids": ["fw-hierarchical-tree"],
                "visual_data": {"framework": "hierarchical-tree", "rootLabel": "Timeline.otio"},
            },
            {
                "id": "fw-matrix",
                "start": 6.0,
                "duration": 2.0,
                "scene_layout": "full-graphic",
                "title": "Effort vs Reuse Matrix",
                "items": [
                    "Custom:Low reuse",
                    "Asset Moat:High reuse",
                    "Raw Cut:Quick notes",
                    "Slop:Avoid neon",
                ],
                "transition": "none",
                "asset_ids": ["fw-matrix-2x2"],
                "visual_data": {"framework": "matrix-2x2", "highlightIndex": 1},
            },
        ],
    }


class TestStarterAssetPackAndHyperFrames(unittest.TestCase):
    def test_asset_pack_files_tokens_and_anti_slop_invariants(self) -> None:
        for rel in EXPECTED_ASSET_FILES:
            path = ASSETS_DIR / rel
            self.assertTrue(path.exists(), f"Missing asset file: {path}")
            content = path.read_text(encoding="utf-8")

            self.assertIsNone(
                HARDCODED_COLOR_RE.search(content),
                f"Hardcoded color detected in {rel}",
            )
            self.assertIsNone(
                NEON_SLOP_RE.search(content),
                f"Prohibited gradient/glow pattern detected in {rel}",
            )
            self.assertIsNone(
                NON_DETERMINISTIC_RE.search(content),
                f"Non-deterministic API detected in {rel}",
            )
            if rel.endswith(".css"):
                self.assertIsNone(
                    CSS_TRANSITION_RE.search(content),
                    f"CSS transition property detected in {rel} (must animate via GSAP)",
                )

            if rel.endswith(".html"):
                self.assertIn("data-composition-id=", content, f"Missing data-composition-id in {rel}")
                self.assertIn('data-width="1920"', content, f"Missing data-width in {rel}")
                self.assertIn('data-height="1080"', content, f"Missing data-height in {rel}")
                self.assertIn("data-composition-variables=", content, f"Missing variables schema in {rel}")
                self.assertIn("window.__timelines", content, f"Missing timeline registration in {rel}")
                self.assertIn("LessonMotion.getVariables", content, f"Missing getVariables helper in {rel}")

        mechanics_js = (ASSETS_DIR / "motion" / "mechanics.js").read_text(encoding="utf-8")
        for helper in (
            "textEntrances",
            "slides",
            "liveNumbers",
            "circlesAndMarks",
            "cards",
            "applyTransition",
            "captions",
        ):
            self.assertIn(helper, mechanics_js, f"Missing motion mechanic helper: {helper}")
        self.assertIn("__hyperframes", mechanics_js)

    def test_standalone_templates_lint_clean_when_mounted(self) -> None:
        """Verify standalone templates in editing_system/assets can be mounted and linted cleanly."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tokens.css").write_text(
                (ASSETS_DIR / "tokens/engineering-editorial/tokens.css").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "transitions.css").write_text(
                (ASSETS_DIR / "motion/transitions.css").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "layouts.css").write_text(
                (ASSETS_DIR / "layouts/layouts.css").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "frameworks.css").write_text(
                (ASSETS_DIR / "frameworks/frameworks.css").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "engineering-section-deck.css").write_text(
                (ASSETS_DIR / "heroes/engineering-section-deck.css").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "mechanics.js").write_text(
                (ASSETS_DIR / "motion/mechanics.js").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "vendor").mkdir()
            shutil.copy2(
                REPO_ROOT / "video_pipeline/hyperframes/node_modules/gsap/dist/gsap.min.js",
                root / "vendor/gsap.min.js",
            )

            panel_html = (ASSETS_DIR / "layouts/panel.html").read_text(encoding="utf-8")
            rewritten = (
                panel_html.replace("../tokens/engineering-editorial/tokens.css", "tokens.css")
                .replace("../motion/transitions.css", "transitions.css")
                .replace("./layouts.css", "layouts.css")
                .replace("../../../video_pipeline/hyperframes/node_modules/gsap/dist/gsap.min.js", "vendor/gsap.min.js")
                .replace("../motion/mechanics.js", "mechanics.js")
            )
            (root / "index.html").write_text(rewritten, encoding="utf-8")
            lint_res = run_hyperframes_lint(root)
            self.assertTrue(lint_res.get("ok"), lint_res)
            self.assertEqual(lint_res.get("errorCount"), 0, lint_res)
            check_res = run_hyperframes_check(root)
            self.assertTrue(check_res.get("ok"), check_res)
            self.assertEqual(check_res["contrast"]["errorCount"], 0, check_res["contrast"])

    def test_compile_lint_check_and_contact_sheet_dark_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            sb_path = tmp_dir / "storyboard.json"
            mf_path = tmp_dir / "timeline_manifest.json"
            proj_dir = tmp_dir / "hf_project"
            sheet_dir = tmp_dir / "contact_sheet_out"

            sb_path.write_text(json.dumps(_dark_storyboard(), indent=2), encoding="utf-8")
            mf_path.write_text(json.dumps(_sample_manifest(12.0), indent=2), encoding="utf-8")

            compiled = compile_hyperframes_project(
                storyboard_path=sb_path,
                manifest_path=mf_path,
                out_project_dir=proj_dir,
                theme="dark",
            )
            self.assertEqual(compiled, proj_dir.resolve())
            self.assertTrue((proj_dir / "index.html").exists())
            self.assertTrue((proj_dir / "vendor" / "gsap.min.js").exists())
            self.assertTrue((proj_dir / "tokens.css").exists())
            self.assertTrue((proj_dir / "dom_layout_manifest.json").exists())

            dom_manifest = json.loads(
                (proj_dir / "dom_layout_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(dom_manifest["width"], 1920)
            self.assertEqual(dom_manifest["height"], 1080)
            self.assertEqual(dom_manifest["safe_margin_x"], 96)
            self.assertEqual(dom_manifest["safe_margin_y"], 54)
            cap = dom_manifest["caption_box"]
            self.assertGreaterEqual(cap["x"], dom_manifest["safe_margin_x"])
            self.assertLessEqual(cap["x"] + cap["w"], dom_manifest["width"] - dom_manifest["safe_margin_x"])
            for box in dom_manifest["overlay_boxes"]:
                self.assertGreaterEqual(box["x"], dom_manifest["safe_margin_x"])
                self.assertGreaterEqual(box["y"], dom_manifest["safe_margin_y"])
                self.assertLessEqual(box["x"] + box["w"], dom_manifest["width"] - dom_manifest["safe_margin_x"])
                self.assertLess(box["y"] + box["h"], cap["y"], f"Box {box} enters caption band")

            lint_report = run_hyperframes_lint(proj_dir)
            self.assertTrue(lint_report.get("ok"), lint_report)
            self.assertEqual(lint_report.get("errorCount"), 0, lint_report)

            check_report = run_hyperframes_check(proj_dir)
            self.assertTrue(check_report.get("ok"), check_report)
            self.assertEqual(check_report["lint"]["errorCount"], 0, check_report["lint"])
            self.assertEqual(check_report["runtime"]["errorCount"], 0, check_report["runtime"])
            self.assertEqual(check_report["layout"]["errorCount"], 0, check_report["layout"])
            self.assertEqual(check_report["contrast"]["errorCount"], 0, check_report["contrast"])

            cs_result = render_contact_sheet(proj_dir, sb_path, sheet_dir)
            self.assertTrue(cs_result.contact_sheet_path.exists())
            self.assertEqual(len(cs_result.stills), 6)
            for still in cs_result.stills:
                self.assertTrue(still.image_path.exists())
                with Image.open(still.image_path) as frame:
                    self.assertEqual(frame.size, (1920, 1080))
            with Image.open(cs_result.contact_sheet_path) as sheet_img:
                self.assertGreater(sheet_img.width, 1280)
                self.assertGreater(sheet_img.height, 800)
            with Image.open(cs_result.stills[0].image_path) as dark_still:
                margin_px = dark_still.convert("RGB").getpixel((20, 20))
                self.assertLess(max(margin_px), 60, f"Expected dark canvas margin, got {margin_px}")

    def test_light_theme_reskin_frameworks_and_wcag_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            sb_path = tmp_dir / "storyboard_light.json"
            mf_path = tmp_dir / "manifest_light.json"
            proj_dir = tmp_dir / "hf_project_light"
            sheet_dir = tmp_dir / "sheet_light"

            sb_path.write_text(json.dumps(_light_frameworks_storyboard(), indent=2), encoding="utf-8")
            mf_path.write_text(json.dumps(_sample_manifest(8.0), indent=2), encoding="utf-8")

            compile_hyperframes_project(
                storyboard_path=sb_path,
                manifest_path=mf_path,
                out_project_dir=proj_dir,
                theme="light",
            )
            index_text = (proj_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-theme="light"', index_text)

            lint_report = run_hyperframes_lint(proj_dir)
            self.assertTrue(lint_report.get("ok"), lint_report)
            self.assertEqual(lint_report.get("errorCount"), 0, lint_report)

            check_report = run_hyperframes_check(proj_dir)
            self.assertTrue(check_report.get("ok"), check_report)
            self.assertEqual(check_report["contrast"]["errorCount"], 0, check_report["contrast"])

            cs_result = render_contact_sheet(proj_dir, sb_path, sheet_dir)
            self.assertEqual(len(cs_result.stills), 4)
            with Image.open(cs_result.stills[0].image_path) as light_still:
                margin_px = light_still.convert("RGB").getpixel((20, 20))
                self.assertGreater(min(margin_px), 210, f"Expected light canvas margin, got {margin_px}")

    def test_render_hyperframes_video_with_real_media_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            media_dir = tmp_dir / "media_in"
            media_dir.mkdir()
            source_mp4 = media_dir / "rough_cut.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=1280x720:rate=30:duration=2.0",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=2.0",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(source_mp4),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            storyboard = {
                "title": "Short Render Verification",
                "beats": [
                    {
                        "id": "r1",
                        "start": 0.0,
                        "duration": 1.0,
                        "scene_layout": "full-screen",
                        "title": "Opening Frame",
                        "transition": "subtle",
                    },
                    {
                        "id": "r2",
                        "start": 1.0,
                        "duration": 1.0,
                        "scene_layout": "circle",
                        "title": "PiP Frame",
                        "body": "Live Signal",
                        "transition": "none",
                        "visual_data": {"pipCorner": "bottom-right"},
                    },
                ],
            }
            sb_path = tmp_dir / "sb.json"
            mf_path = tmp_dir / "mf.json"
            sb_path.write_text(json.dumps(storyboard), encoding="utf-8")
            mf_path.write_text(
                json.dumps(
                    {
                        "videoFile": "rough_cut.mp4",
                        "fps": 30.0,
                        "width": 1920,
                        "height": 1080,
                        "durationInFrames": 60,
                        "captionsEnabled": True,
                        "captions": [
                            {"text": "Short", "startMs": 100, "endMs": 600},
                            {"text": "check.", "startMs": 650, "endMs": 1400},
                        ],
                        "graphicCues": [],
                    }
                ),
                encoding="utf-8",
            )

            proj_dir = tmp_dir / "proj"
            compile_hyperframes_project(
                storyboard_path=sb_path,
                manifest_path=mf_path,
                out_project_dir=proj_dir,
                media_dir=media_dir,
                theme="dark",
            )

            lint_report = run_hyperframes_lint(proj_dir)
            self.assertTrue(lint_report.get("ok"), lint_report)
            self.assertEqual(lint_report.get("errorCount"), 0, lint_report)
            check_report = run_hyperframes_check(proj_dir)
            self.assertTrue(check_report.get("ok"), check_report)

            out_mp4 = tmp_dir / "rendered.mp4"
            rendered = render_hyperframes_video(proj_dir, out_mp4, fmt="mp4", quality="draft")
            self.assertTrue(rendered.exists())
            self.assertGreater(rendered.stat().st_size, 1024)

            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "json",
                    str(rendered),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            dur = float(json.loads(probe.stdout)["format"]["duration"])
            self.assertGreaterEqual(dur, 1.5)


if __name__ == "__main__":
    unittest.main()
