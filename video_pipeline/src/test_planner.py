"""Run with: uv run --project video_pipeline python video_pipeline/src/test_planner.py"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from planner import generate_edl
from schema import TranscriptBundle


class OpenCodePlannerTest(unittest.TestCase):
    def test_authenticated_cli_plan(self):
        bundle = TranscriptBundle(source_path="input.mp4", duration=5, fps=30, width=1920, height=1080)
        plan = {"kept_segments": [{"id": "s1", "start": 0, "end": 4}], "graphic_cues": []}
        event = {"type": "text", "part": {"text": json.dumps(plan)}}
        with patch("planner.subprocess.run", return_value=SimpleNamespace(stdout="mise startup\n" + json.dumps(event))) as run:
            edl = generate_edl(bundle, model="opencode/openai/example")
        self.assertEqual(edl.kept_segments[0].end, 4)
        self.assertEqual(run.call_args.args[0], ["opencode", "run", "--format", "json", "--model", "openai/example"])
        self.assertIn("Transcript bundle", run.call_args.kwargs["input"])

    def test_empty_output_is_an_error(self):
        bundle = TranscriptBundle(source_path="input.mp4", duration=5, fps=30, width=1920, height=1080)
        with patch("planner.subprocess.run", return_value=SimpleNamespace(stdout="")):
            with self.assertRaisesRegex(RuntimeError, "no editorial plan"):
                generate_edl(bundle, model="opencode")

    def test_invalid_plan_is_not_silently_accepted(self):
        bundle = TranscriptBundle(source_path="input.mp4", duration=5, fps=30, width=1920, height=1080)
        for text in ("{}", "not json"):
            event = {"type": "text", "part": {"text": text}}
            with self.subTest(text=text), patch("planner.subprocess.run", return_value=SimpleNamespace(stdout=json.dumps(event))):
                with self.assertRaises(ValueError):
                    generate_edl(bundle, model="opencode")


if __name__ == "__main__":
    unittest.main()
