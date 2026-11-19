"""Static contract checks for the project-local producer skill."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / ".opencode/skills/post-production"


class PostProductionSkillTests(unittest.TestCase):
    def test_dispatch_table_resolves_all_specialists(self):
        text = (SKILL / "SKILL.md").read_text()
        routes = re.findall(r"\| `(\d{2}-[\w-]+)` \| `(post-[\w-]+)` \|", text)
        self.assertEqual(len(routes), 10)
        self.assertEqual(len({stage for stage, _ in routes}), 10)
        self.assertEqual(len({agent for _, agent in routes}), 10)
        for _, agent in routes:
            with self.subTest(agent=agent):
                profile = ROOT / ".opencode/agents" / f"{agent}.md"
                body = profile.read_text()
                self.assertRegex(body, r"\A---\n(?:.*\n)*?mode: subagent\n")
                self.assertIn("description:", body)
                self.assertIn(
                    ".opencode/skills/post-production/references/handoff.md", body
                )
                self.assertIn("report.md", body)
                self.assertIn("Done when", body)

    def test_local_markdown_links_resolve(self):
        docs = list(SKILL.rglob("*.md")) + [
            ROOT / "video_pipeline/README.md",
            ROOT / "experiments/post-production-video-editing.md",
        ]
        for doc in docs:
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", doc.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                path = target.split("#", 1)[0]
                with self.subTest(doc=doc, target=target):
                    self.assertTrue((doc.parent / path).exists())

    def test_review_and_backend_boundaries_remain_documented(self):
        producer = (SKILL / "SKILL.md").read_text()
        tools = (SKILL / "references/tools.md").read_text()
        for requirement in (
            "Rough-cut gate",
            "Final gate",
            "artifact hashes",
            "stale",
            "trim-only baseline",
        ):
            self.assertIn(requirement, producer)
        self.assertIn("serialize renders", tools)
        self.assertIn("actual import/reopen needs testing", tools.lower())
        self.assertIn("stage-local EDL copy", tools)
        self.assertIn("exactly one chosen speech/mix track", tools)


if __name__ == "__main__":
    unittest.main()
