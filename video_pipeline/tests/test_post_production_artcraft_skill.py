"""Instruction contracts only; these checks do not verify native execution."""

import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".opencode/skills"
PIPELINE = SKILLS / "post-production"
ARTCRAFT = SKILLS / "post-production-artcraft"
AGENTS = ROOT / ".opencode/agents"
SPECIALISTS = {
    f"post-{name}"
    for name in (
        "media", "transcript", "story", "pacing", "visual",
        "audio", "color", "accessibility", "packaging", "qc",
    )
}
NATIVE_DOCS = [
    ARTCRAFT / "SKILL.md",
    *(ARTCRAFT / "references" / f"{name}.md" for name in (
        "handoff", "filmcraft-api", "timeline-api", "effectcraft-api", "soundcraft-api",
    )),
]


def operating_docs():
    """Downloaded research is evidence, not maintained operating guidance."""
    return sorted({
        *NATIVE_DOCS,
        *(
            doc
            for skill in (PIPELINE, ARTCRAFT)
            for doc in skill.rglob("*.md")
            if "research" not in doc.relative_to(skill).parts
        ),
        *(AGENTS / f"{agent}.md" for agent in SPECIALISTS),
        ROOT / "video_pipeline/README.md",
        ROOT / "experiments/post-production-video-editing.md",
    })


class PostProductionArtcraftSkillTests(unittest.TestCase):
    def test_both_dispatch_tables_reuse_the_existing_ten_specialists(self):
        tables = []
        for skill in (PIPELINE, ARTCRAFT):
            with self.subTest(skill=skill.name):
                routes = re.findall(
                    r"\|\s*`(\d{2}-[\w-]+)`\s*\|\s*`(post-[\w-]+)`\s*\|",
                    (skill / "SKILL.md").read_text(),
                )
                self.assertEqual(len(routes), 10)
                self.assertEqual(len({stage for stage, _ in routes}), 10)
                self.assertEqual({agent for _, agent in routes}, SPECIALISTS)
                tables.append(dict(routes))
        self.assertEqual(len(tables), 2, "Both producer dispatch tables must exist")
        self.assertEqual(tables[0], tables[1])
        for agent in sorted(SPECIALISTS):
            with self.subTest(agent=agent):
                body = (AGENTS / f"{agent}.md").read_text()
                self.assertRegex(body, r"\A---\n(?:.*\n)*?mode: subagent\n")
                self.assertIn(".opencode/skills/post-production/references/handoff.md", body)
                self.assertIn("report.md", body)
                self.assertIn("Done when", body)

    def test_permanent_local_markdown_links_resolve(self):
        for doc in operating_docs():
            with self.subTest(doc=doc.relative_to(ROOT)):
                text = doc.read_text()
                targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
                targets += re.findall(r"(?m)^\[[^\]]+\]:\s*(\S+)", text)
                for target in targets:
                    target = target.strip().split(maxsplit=1)[0].strip("<>")
                    url = urlsplit(target)
                    if url.scheme or url.netloc or not url.path:
                        continue
                    with self.subTest(target=target):
                        self.assertTrue(
                            (doc.parent / unquote(url.path)).is_file(),
                            f"{doc.relative_to(ROOT)}: unresolved link {target}",
                        )

    def test_operating_docs_do_not_depend_on_research_or_personal_paths(self):
        for doc in operating_docs():
            with self.subTest(doc=doc.relative_to(ROOT)):
                text = doc.read_text()
                self.assertNotRegex(text, r"(?:\.\.?/|[\w.-]/)research/")
                self.assertNotRegex(text, r"(?:/home/|/Users/|[A-Za-z]:\\Users\\)[^\s/\\]+")

    def test_native_producer_keeps_capability_and_review_gates(self):
        text = (ARTCRAFT / "SKILL.md").read_text().lower()
        # Coarse concepts, not prescribed headings or exact sentences.
        for concept in (
            r"capabilit", r"disposable", r"version",
            r"rough[- ]cut", r"final", r"approv", r"hash",
            r"independent", r"(?:fresh|single[- ]use)", r"\bqc\b",
            r"stale|invalidat", r"fallback|fall back", r"block",
            r"serial|single[- ]writer", r"promot|integrat", r"producer",
            r"publication|publish|upload", r"backend", r"artcraft",
        ):
            with self.subTest(concept=concept):
                self.assertRegex(text, concept)

    def test_shared_handoff_defaults_to_pipeline_and_requires_native_contract(self):
        text = (PIPELINE / "references/handoff.md").read_text().lower()
        for concept in (
            r"backend", r"pipeline", r"default|omitted|unspecified|absent",
            r"artcraft", r"backend_reference|post-production-artcraft/references/handoff\.md",
            r"suppl|dispatch",
            r"fallback|fall back|switch", r"block",
            r"parent", r"revision", r"hash", r"approv",
            r"source.to.edit", r"producer", r"assigned",
        ):
            with self.subTest(concept=concept):
                self.assertRegex(text, concept)
        for heading in ("Status", "Inputs", "Work performed", "Outputs", "Checks", "Open issues"):
            self.assertRegex(text, rf"\*\*{heading.lower()}:?\*\*")
        native = (ARTCRAFT / "references/handoff.md").read_text()
        self.assertIn("post-production/references/handoff.md", native)

    def test_story_and_pacing_preserve_pipeline_and_native_routes(self):
        for agent, legacy_artifacts in (
            ("post-story", ("story_edl.json",)),
            ("post-pacing", ("edl.json", "cut_audit.json", "rough_cut.mp4")),
        ):
            with self.subTest(agent=agent):
                text = (AGENTS / f"{agent}.md").read_text().lower()
                for concept in (
                    r"pipeline", r"artcraft", r"project",
                    r"mapping|source.map", r"candidate|proposal|copy",
                ):
                    self.assertRegex(text, concept)
                for artifact in legacy_artifacts:
                    self.assertIn(artifact, text)
                if agent == "post-pacing":
                    self.assertRegex(text, r"preview")
                    self.assertRegex(text, r"producer")
                    self.assertRegex(text, r"fallback|fall back|unapproved|rather than pipeline")

    def test_deferral_and_final_checkpoint_review_contracts(self):
        for agent in ("post-visual", "post-audio", "post-color"):
            with self.subTest(agent=agent):
                text = (AGENTS / f"{agent}.md").read_text().lower()
                self.assertIn("artcraft", text)
                self.assertRegex(text, r"deferr")
                self.assertRegex(text, r"assigned work|assigned scope")
        native = (ARTCRAFT / "references/handoff.md").read_text().lower()
        self.assertRegex(native, r"final.*(?:checkpoint|production)")
        self.assertRegex(native, r"fresh.*session")
        self.assertRegex(native, r"reopen")
        self.assertRegex(native, r"dependency.*hash|hash.*dependenc")
        self.assertRegex(native, r"qc.*pure read|pure read.*qc")

    def test_timeline_examples_preserve_targeting_safeguards(self):
        text = (ARTCRAFT / "references/timeline-api.md").read_text()
        self.assertRegex(text, r'graphics\.newShape[^\n]*"track":1')
        self.assertIn("zero-based video-track index", text)
        self.assertIn("expand linked audio targets", text)
        self.assertIn('sequence.linkedSelection {"on":false}', text)


if __name__ == "__main__":
    unittest.main()
