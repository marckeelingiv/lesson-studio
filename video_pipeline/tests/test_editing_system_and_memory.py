"""Unit tests for Creative Brief, Asset Catalog, Storyboard, RunState, and Taste Profile memory."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from pydantic import ValidationError

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from editing_system import (  # noqa: E402
    DEFAULT_CATALOG_PATH,
    DEFAULT_PRESETS_DIR,
    EDITING_SYSTEM_DIR,
    REPO_ROOT,
    AssetCatalog,
    AssetEntry,
    CreativeBrief,
    DeliveryTarget,
    FeelSettings,
    ReferenceVideo,
    RunState,
    Storyboard,
    StoryboardBeat,
    compute_sha256,
    init_creative_brief,
    load_asset_catalog,
    load_creative_brief,
    validate_asset_catalog,
    validate_storyboard,
)
from taste_memory import (  # noqa: E402
    ReviewLogEntry,
    append_review_note,
    find_promotion_candidates,
    load_review_log,
    render_taste_profile_md,
)


def _make_beat(
    beat_id: str,
    start: float,
    duration: float,
    scene_layout: str = "Full Screen",
    transition: str | None = None,
    asset_ids: list[str] | None = None,
    reason: str = "Match spoken explanation.",
    purpose: str = "Clarify architecture decision.",
    intention: str = "Keep viewer focused on concrete evidence.",
) -> dict:
    return {
        "id": beat_id,
        "start": start,
        "duration": duration,
        "scene_layout": scene_layout,
        "title": f"Beat {beat_id}",
        "transition": transition,
        "asset_ids": asset_ids or [],
        "reason": reason,
        "purpose": purpose,
        "intention": intention,
    }


class TestCreativeBriefAndPresets(unittest.TestCase):
    def test_repo_constants_point_to_editing_system(self) -> None:
        self.assertTrue((REPO_ROOT / "GLOSSARY.md").is_file())
        self.assertEqual(EDITING_SYSTEM_DIR, REPO_ROOT / "editing_system")
        self.assertTrue(DEFAULT_CATALOG_PATH.is_file())
        self.assertTrue(DEFAULT_PRESETS_DIR.is_dir())

    def test_template_brief_loads_with_clean_editorial_preset(self) -> None:
        template_path = EDITING_SYSTEM_DIR / "briefs" / "creative-brief.template.yaml"
        brief = load_creative_brief(template_path)
        self.assertEqual(brief.entry_mode, "sift")
        self.assertEqual(brief.feel.animation, 2)
        self.assertEqual(brief.feel.visuals, 2)
        self.assertEqual(brief.feel.sound_design, 1)
        self.assertEqual(brief.feel.max_transitions, 3)
        self.assertEqual(brief.delivery_target.width, 1920)
        self.assertEqual(brief.delivery_target.loudness_lufs, -14.0)

    def test_more_than_two_references_rejected(self) -> None:
        refs = [
            ReferenceVideo(label="good", url_or_path="https://example.com/1", emulate=["b_roll"], notes="Good"),
            ReferenceVideo(label="not_good", url_or_path="https://example.com/2", emulate=["pacing"], notes="Too fast"),
            ReferenceVideo(label="good", url_or_path="https://example.com/3", emulate=["sound_design"], notes="Extra"),
        ]
        with self.assertRaises(ValidationError):
            CreativeBrief(video_id="v1", title="Test", references=refs)

    def test_feel_sliders_and_max_transitions_bounds(self) -> None:
        for bad_val in (0, 6, True):
            with self.subTest(bad_val=bad_val):
                with self.assertRaises(ValidationError):
                    FeelSettings(animation=bad_val)
                with self.assertRaises(ValidationError):
                    FeelSettings(visuals=bad_val)
                with self.assertRaises(ValidationError):
                    FeelSettings(sound_design=bad_val)

        with self.assertRaises(ValidationError):
            FeelSettings(max_transitions=4)
        with self.assertRaises(ValidationError):
            FeelSettings(max_transitions=-1)
        with self.assertRaises(ValidationError):
            FeelSettings(pacing="hyper")  # type: ignore[arg-type]

    def test_preset_merging_preserves_defaults_underneath_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            presets_dir = tmp_path / "presets"
            presets_dir.mkdir()
            (presets_dir / "custom-editorial.yaml").write_text(
                yaml.safe_dump(
                    {
                        "preset_id": "custom-editorial",
                        "description": "Custom defaults",
                        "feel": {
                            "animation": 1,
                            "visuals": 3,
                            "sound_design": 2,
                            "pacing": "deliberate",
                            "max_transitions": 2,
                            "allowed_transitions": ["subtle"],
                        },
                        "delivery_target": {
                            "aspect_ratio": "16:9",
                            "width": 1920,
                            "height": 1080,
                            "fps": 60,
                            "loudness_lufs": -14.0,
                            "true_peak_dbtp": -1.0,
                            "captions_enabled": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            brief_path = tmp_path / "brief.yaml"
            brief_path.write_text(
                yaml.safe_dump(
                    {
                        "video_id": "de-for-fun/demo",
                        "title": "Demo Lesson",
                        "entry_mode": "clean_a_roll",
                        "preset": "custom-editorial",
                        "feel": {"animation": 4},
                    }
                ),
                encoding="utf-8",
            )

            brief = load_creative_brief(brief_path, presets_dir=presets_dir)
            self.assertEqual(brief.entry_mode, "clean_a_roll")
            self.assertEqual(brief.feel.animation, 4)
            self.assertEqual(brief.feel.visuals, 3)
            self.assertEqual(brief.feel.sound_design, 2)
            self.assertEqual(brief.feel.pacing, "deliberate")
            self.assertEqual(brief.feel.max_transitions, 2)
            self.assertEqual(brief.feel.allowed_transitions, ["subtle"])
            self.assertEqual(brief.delivery_target.fps, 60)

    def test_missing_explicit_preset_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = Path(tmp) / "brief.yaml"
            brief_path.write_text(
                yaml.safe_dump({"video_id": "v1", "title": "T1", "preset": "does-not-exist"}),
                encoding="utf-8",
            )
            with self.assertRaises(FileNotFoundError):
                load_creative_brief(brief_path)

    def test_init_creative_brief_writes_loadable_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "run" / "creative-brief.yaml"
            out = init_creative_brief(dest, video_id="de-for-fun/unit-test", title="Unit Test Video")
            self.assertEqual(out, dest)
            self.assertTrue(out.is_file())
            loaded = load_creative_brief(out)
            self.assertEqual(loaded.video_id, "de-for-fun/unit-test")
            self.assertEqual(loaded.title, "Unit Test Video")
            self.assertEqual(loaded.preset, "clean-editorial")

    def test_unknown_key_rejected_and_null_preset_skips_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            brief_path = Path(tmp) / "brief.yaml"
            brief_path.write_text(
                yaml.safe_dump({"video_id": "v1", "title": "T1", "preset": None}),
                encoding="utf-8",
            )
            loaded = load_creative_brief(brief_path)
            self.assertIsNone(loaded.preset)
            self.assertEqual(loaded.feel.animation, 2)

            brief_path.write_text(
                yaml.safe_dump({"video_id": "v1", "title": "T1", "bogus_field": 123}),
                encoding="utf-8",
            )
            with self.assertRaises(ValidationError):
                load_creative_brief(brief_path)


class TestAssetCatalog(unittest.TestCase):
    def test_real_catalog_validates_cleanly(self) -> None:
        errors = validate_asset_catalog(DEFAULT_CATALOG_PATH)
        self.assertEqual(errors, [])
        catalog = load_asset_catalog(DEFAULT_CATALOG_PATH)
        self.assertTrue(catalog.has_id("tok-engineering-editorial"))
        self.assertTrue(catalog.has_id("gfx-browser-frame"))
        self.assertTrue(catalog.has_id("gfx-terminal-frame"))

    def test_missing_active_asset_path_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "assets": [
                            {
                                "id": "gfx-missing-frame",
                                "class": "graphics",
                                "subtype": "mockup",
                                "aspect_ratios": ["16:9"],
                                "tags": ["mockup"],
                                "license": "Original",
                                "attribution": "Lesson Studio",
                                "path": "graphics/mockups/nonexistent.svg",
                                "status": "active",
                                "usage_rules": "Test active missing file.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_asset_catalog(catalog_path)
            self.assertEqual(len(errors), 1)
            self.assertIn("active asset path missing", errors[0])

    def test_planned_asset_allows_missing_file_but_rejects_bad_class_or_duplicate_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "assets": [
                            {
                                "id": "lay-panel-v1",
                                "class": "layouts",
                                "subtype": "panel",
                                "aspect_ratios": ["16:9"],
                                "tags": ["panel"],
                                "license": "Original",
                                "attribution": "Lesson Studio",
                                "path": "layouts/panel.html",
                                "status": "planned",
                                "usage_rules": "Planned Panel layout.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(validate_asset_catalog(catalog_path), [])

            # Invalid asset class
            catalog_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "assets": [
                            {
                                "id": "bad-asset",
                                "class": "widgets",
                                "subtype": "panel",
                                "aspect_ratios": ["16:9"],
                                "tags": ["x"],
                                "license": "Original",
                                "attribution": "",
                                "path": "widgets/x.html",
                                "status": "planned",
                                "usage_rules": "Bad class.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            self.assertTrue(validate_asset_catalog(catalog_path))

            # Duplicate IDs
            entry = {
                "id": "dup-asset",
                "class": "graphics",
                "subtype": "icon",
                "aspect_ratios": ["any"],
                "tags": ["icon"],
                "license": "CC0",
                "attribution": "",
                "path": "graphics/icon.svg",
                "status": "planned",
                "usage_rules": "Icon.",
            }
            catalog_path.write_text(
                json.dumps({"schema_version": 1, "assets": [entry, entry]}),
                encoding="utf-8",
            )
            dup_errors = validate_asset_catalog(catalog_path)
            self.assertTrue(any("Duplicate asset IDs" in err for err in dup_errors))

    def test_asset_entry_alias_roundtrip(self) -> None:
        entry = AssetEntry(
            id="aud-soft-hit",
            class_="audio",
            subtype="sfx",
            aspect_ratios=["any"],
            tags=["sfx"],
            license="CC0",
            attribution="OpenAudio",
            path="audio/soft-hit.wav",
            status="planned",
            usage_rules="Use on major section reveal only.",
        )
        dumped = entry.model_dump(by_alias=True)
        self.assertEqual(dumped["class"], "audio")

    def test_catalog_missing_schema_version_and_path_traversal_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    {
                        "assets": [
                            {
                                "id": "gfx-escape",
                                "class": "graphics",
                                "subtype": "mockup",
                                "aspect_ratios": ["16:9"],
                                "tags": ["escape"],
                                "license": "Original",
                                "attribution": "",
                                "path": "../secret.svg",
                                "status": "planned",
                                "usage_rules": "Should fail traversal.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_asset_catalog(catalog_path)
            self.assertTrue(any("schema_version" in err for err in errors))
            self.assertTrue(any("escapes catalog directory" in err for err in errors))


class TestStoryboard(unittest.TestCase):
    def test_valid_storyboard_with_all_scene_layouts_and_catalog(self) -> None:
        catalog = load_asset_catalog(DEFAULT_CATALOG_PATH)
        brief = CreativeBrief(video_id="de-for-fun/test", title="Test")
        sb_payload = {
            "video_id": "de-for-fun/test",
            "theme": "dark",
            "token_kit": "tok-engineering-editorial",
            "beats": [
                _make_beat("b1", 0.0, 3.0, "Full Screen", transition=None),
                _make_beat("b2", 3.0, 4.0, "Panel", transition="subtle", asset_ids=["gfx-terminal-frame"]),
                _make_beat("b3", 7.0, 3.5, "Centre", transition="swipe"),
                _make_beat("b4", 10.5, 4.0, "Full Graphic", transition="zoom", asset_ids=["gfx-browser-frame"]),
                _make_beat("b5", 14.5, 3.0, "Circle", transition=None),
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            sb_path = Path(tmp) / "storyboard.json"
            sb_path.write_text(json.dumps(sb_payload), encoding="utf-8")
            sb = validate_storyboard(sb_path, brief=brief, catalog=catalog)
            self.assertEqual(len(sb.beats), 5)
            self.assertEqual(sb.transition_count, 3)

    def test_invalid_scene_layout_fails(self) -> None:
        with self.assertRaises(ValidationError):
            StoryboardBeat.model_validate(_make_beat("b1", 0.0, 2.0, scene_layout="Split Screen"))

    def test_empty_intentionality_filter_fails(self) -> None:
        for field_name in ("reason", "purpose", "intention"):
            with self.subTest(field_name=field_name):
                payload = _make_beat("b1", 0.0, 2.0)
                payload[field_name] = "   "
                with self.assertRaises(ValidationError):
                    StoryboardBeat.model_validate(payload)

    def test_overlapping_and_unordered_beats_fail(self) -> None:
        with self.assertRaises(ValidationError):
            Storyboard(
                video_id="v1",
                beats=[
                    StoryboardBeat.model_validate(_make_beat("b1", 0.0, 3.0)),
                    StoryboardBeat.model_validate(_make_beat("b2", 2.5, 2.0)),
                ],
            )
        with self.assertRaises(ValidationError):
            Storyboard(
                video_id="v1",
                beats=[
                    StoryboardBeat.model_validate(_make_beat("b1", 5.0, 2.0)),
                    StoryboardBeat.model_validate(_make_beat("b2", 1.0, 2.0)),
                ],
            )

    def test_more_than_three_transitions_fails(self) -> None:
        with self.assertRaises(ValidationError):
            Storyboard(
                video_id="v1",
                beats=[
                    StoryboardBeat.model_validate(_make_beat("b1", 0.0, 1.0, transition="subtle")),
                    StoryboardBeat.model_validate(_make_beat("b2", 1.0, 1.0, transition="swipe")),
                    StoryboardBeat.model_validate(_make_beat("b3", 2.0, 1.0, transition="zoom")),
                    StoryboardBeat.model_validate(_make_beat("b4", 3.0, 1.0, transition="film_burn")),
                ],
            )

    def test_validate_storyboard_checks_brief_caps_and_catalog_ids(self) -> None:
        catalog = load_asset_catalog(DEFAULT_CATALOG_PATH)
        brief = CreativeBrief(
            video_id="v1",
            title="Test",
            feel=FeelSettings(max_transitions=1, allowed_transitions=["subtle"]),
        )
        with tempfile.TemporaryDirectory() as tmp:
            sb_path = Path(tmp) / "storyboard.json"

            # Exceeds brief.feel.max_transitions (2 > 1)
            sb_path.write_text(
                json.dumps(
                    {
                        "video_id": "v1",
                        "beats": [
                            _make_beat("b1", 0.0, 2.0, transition="subtle"),
                            _make_beat("b2", 2.0, 2.0, transition="subtle"),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "exceeding brief cap 1"):
                validate_storyboard(sb_path, brief=brief, catalog=catalog)

            # Disallowed transition type per brief
            sb_path.write_text(
                json.dumps(
                    {
                        "video_id": "v1",
                        "beats": [_make_beat("b1", 0.0, 2.0, transition="film_burn")],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "disallowed transition"):
                validate_storyboard(sb_path, brief=brief, catalog=catalog)

            # Unknown asset_id against catalog
            sb_path.write_text(
                json.dumps(
                    {
                        "video_id": "v1",
                        "beats": [_make_beat("b1", 0.0, 2.0, asset_ids=["gfx-unknown"])],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unknown asset_ids"):
                validate_storyboard(sb_path, brief=brief, catalog=catalog)


class TestRunState(unittest.TestCase):
    def test_hash_mark_stale_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_file = tmp_path / "source.mp4"
            storyboard_file = tmp_path / "storyboard.json"
            tokens_file = tmp_path / "tokens.css"
            source_file.write_bytes(b"raw-video-v1")
            storyboard_file.write_text('{"beats": []}', encoding="utf-8")
            tokens_file.write_text(":root { --bg: #000; }", encoding="utf-8")

            state = RunState(run_id="run-001", video_id="de-for-fun/test")
            self.assertEqual(set(state.gates.keys()), {"rough_cut", "contact_sheet", "picture_lock", "final_delivery"})

            rec = state.record_input_hash("source", source_file)
            self.assertEqual(rec.sha256, compute_sha256(source_file))
            state.record_input_hash("storyboard", storyboard_file)
            state.record_input_hash("tokens", tokens_file)

            state.approve_gate("rough_cut", approved_by="marc", artifact_paths={"source": source_file})
            state.approve_gate("contact_sheet", approved_by="marc")
            state.approve_gate("picture_lock", approved_by="marc")
            state.approve_gate("final_delivery", approved_by="marc")

            # Storyboard change invalidates contact_sheet, picture_lock, final_delivery, keeping rough_cut
            stale = state.mark_stale("storyboard")
            self.assertIn("contact_sheet", stale)
            self.assertIn("visual_plates", stale)
            self.assertEqual(state.gates["rough_cut"].status, "approved")
            self.assertEqual(state.gates["contact_sheet"].status, "pending")
            self.assertEqual(state.gates["picture_lock"].status, "pending")
            self.assertEqual(state.gates["final_delivery"].status, "pending")

            # Re-approve all, then verify changing tokens file via record_input_hash auto-invalidates
            state.approve_gate("contact_sheet", approved_by="marc")
            state.approve_gate("picture_lock", approved_by="marc")
            state.approve_gate("final_delivery", approved_by="marc")
            self.assertNotIn("contact_sheet", state.stale_artifacts)

            tokens_file.write_text(":root { --bg: #fff; }", encoding="utf-8")
            state.record_input_hash("tokens", tokens_file)
            self.assertEqual(state.gates["rough_cut"].status, "approved")
            self.assertEqual(state.gates["contact_sheet"].status, "pending")
            self.assertEqual(state.gates["picture_lock"].status, "pending")
            self.assertEqual(state.gates["final_delivery"].status, "pending")
            self.assertIn("visual_plates", state.stale_artifacts)

            run_json = tmp_path / "run.json"
            state.save(run_json)
            loaded = RunState.load(run_json)
            self.assertEqual(loaded, state)

            # Upstream otio/transcript/source changes invalidate all 4 gates
            for upstream in ("otio", "transcript", "source"):
                state.approve_gate("rough_cut", approved_by="marc")
                state.approve_gate("contact_sheet", approved_by="marc")
                state.mark_stale(upstream)
                self.assertEqual(state.gates["rough_cut"].status, "pending")
                self.assertEqual(state.gates["contact_sheet"].status, "pending")

            with self.assertRaises(ValueError):
                state.mark_stale("unknown_upstream")
            with self.assertRaises(ValueError):
                state.approve_gate("unknown_gate")


class TestTasteMemory(unittest.TestCase):
    def test_empty_log_and_append_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "review_log.jsonl"
            self.assertEqual(load_review_log(log_path), [])
            log_path.write_text("", encoding="utf-8")
            self.assertEqual(load_review_log(log_path), [])

            entry = ReviewLogEntry(
                date="2026-11-23",
                video_id="de-for-fun/purchase-evidence",
                timestamp="00:14.200",
                category="layout",
                tag="DON'T",
                note="Avoid covering chart axis labels with callout cards in Panel mode.",
            )
            append_review_note(log_path, entry)
            loaded = load_review_log(log_path)
            self.assertEqual(loaded, [entry])

    def test_render_taste_profile_preserves_sections_1_and_2(self) -> None:
        real_profile = EDITING_SYSTEM_DIR / "memory" / "taste_profile.md"
        original_text = real_profile.read_text(encoding="utf-8")
        section_3_marker = "## 3. Active Taste Profile"
        expected_prefix = original_text[: original_text.index(section_3_marker)].rstrip()

        with tempfile.TemporaryDirectory() as tmp:
            temp_profile = Path(tmp) / "taste_profile.md"
            shutil.copy2(real_profile, temp_profile)

            entries = [
                ReviewLogEntry(
                    date="2026-11-20",
                    video_id="lesson-1",
                    timestamp="00:10.000",
                    category="captions",
                    tag="NON-NEGOTIABLE",
                    note="Keep caption anchor fixed at lower center.",
                ),
                ReviewLogEntry(
                    date="2026-11-21",
                    video_id="lesson-2",
                    timestamp="01:05.500",
                    category="layout",
                    tag="DON'T",
                    note="Never overlap SQL table headers with PiP circle.",
                ),
                ReviewLogEntry(
                    date="2026-11-22",
                    video_id="lesson-3",
                    timestamp="02:30.000",
                    category="sifting",
                    tag="DO",
                    note="Leave 3 frames before plosive consonant starts.",
                ),
                ReviewLogEntry(
                    date="2026-11-23",
                    video_id="lesson-3",
                    timestamp="03:15.000",
                    category="pacing",
                    tag="PREFERENCE",
                    note="Prefer hard cuts over swipe between Panel views.",
                ),
            ]
            rendered = render_taste_profile_md(entries, temp_profile)
            self.assertTrue(rendered.startswith(expected_prefix))
            self.assertIn("### NON-NEGOTIABLE", rendered)
            self.assertIn("### DON'T", rendered)
            self.assertIn("### DO", rendered)
            self.assertIn("### PREFERENCE", rendered)
            self.assertIn("Keep caption anchor fixed at lower center.", rendered)
            self.assertEqual(temp_profile.read_text(encoding="utf-8"), rendered)

            # Verify tag order in Section 3
            s3 = rendered[rendered.index(section_3_marker) :]
            self.assertLess(s3.index("### NON-NEGOTIABLE\n"), s3.index("### DON'T\n"))
            self.assertLess(s3.index("### DON'T\n"), s3.index("### DO\n"))
            self.assertLess(s3.index("### DO\n"), s3.index("### PREFERENCE\n"))

    def test_render_taste_profile_empty_and_mixed_category_promotion(self) -> None:
        real_profile = EDITING_SYSTEM_DIR / "memory" / "taste_profile.md"
        with tempfile.TemporaryDirectory() as tmp:
            temp_profile = Path(tmp) / "taste_profile.md"
            shutil.copy2(real_profile, temp_profile)
            empty_rendered = render_taste_profile_md([], temp_profile)
            self.assertIn("*(none recorded yet)*", empty_rendered)

            log_path = Path(tmp) / "review_log.jsonl"
            log_path.write_text("", encoding="utf-8")
            entries = [
                ReviewLogEntry(
                    date="2026-11-20",
                    video_id="vid-1",
                    timestamp="00:08.000",
                    category="captions",
                    tag="DON'T",
                    note="Do not shift caption height.",
                ),
                ReviewLogEntry(
                    date="2026-11-21",
                    video_id="vid-2",
                    timestamp="00:12.000",
                    category="captions",
                    tag="NON-NEGOTIABLE",
                    note="Keep captions anchored at bottom center.",
                ),
                ReviewLogEntry(
                    date="2026-11-22",
                    video_id="vid-3",
                    timestamp="00:18.000",
                    category="captions",
                    tag="DON'T",
                    note="Avoid drifting captions in Panel layout.",
                ),
            ]
            for idx, entry in enumerate(entries):
                append_review_note(log_path, entry)
                if idx == 0:
                    # Simulate external writer leaving no trailing newline
                    log_path.write_text(log_path.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")

            loaded = load_review_log(log_path)
            self.assertEqual(loaded, entries)
            proposals = find_promotion_candidates(loaded, min_videos=3)
            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0].category, "captions")
            self.assertEqual(proposals[0].tag, "NON-NEGOTIABLE")
            self.assertEqual(proposals[0].video_ids, ["vid-1", "vid-2", "vid-3"])

    def test_invalid_review_entry_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ReviewLogEntry(
                date="not-a-date",
                video_id="v1",
                timestamp="00:01.000",
                category="layout",
                tag="DO",
                note="Valid note",
            )
        with self.assertRaises(ValidationError):
            ReviewLogEntry(
                date="2026-11-23",
                video_id="v1",
                timestamp="00:01.000",
                category="unknown",  # type: ignore[arg-type]
                tag="DO",
                note="Valid note",
            )

    def test_promotion_proposals_require_three_distinct_videos_and_never_mutate_rules(self) -> None:
        rules_dir = EDITING_SYSTEM_DIR / "rules"
        before_rules = {p.name: p.read_bytes() for p in sorted(rules_dir.glob("*.md"))}

        entries = [
            # Already promoted across 3 videos -> must be ignored
            ReviewLogEntry(
                date="2026-11-01",
                video_id="v1",
                timestamp="00:05.000",
                category="audio",
                tag="DON'T",
                note="Keep SFX quieter than dialogue.",
                promoted_rule_id="R03-sfx-level",
            ),
            ReviewLogEntry(
                date="2026-11-02",
                video_id="v2",
                timestamp="00:06.000",
                category="audio",
                tag="DON'T",
                note="Keep SFX quieter than dialogue.",
                promoted_rule_id="R03-sfx-level",
            ),
            ReviewLogEntry(
                date="2026-11-03",
                video_id="v3",
                timestamp="00:07.000",
                category="audio",
                tag="DON'T",
                note="Keep SFX quieter than dialogue.",
                promoted_rule_id="R03-sfx-level",
            ),
            # Same video repeated 3 times -> only 1 distinct video -> must NOT propose
            ReviewLogEntry(
                date="2026-11-10",
                video_id="v-single",
                timestamp="00:10.000",
                category="motion",
                tag="PREFERENCE",
                note="Slow down chart entrance.",
            ),
            ReviewLogEntry(
                date="2026-11-10",
                video_id="v-single",
                timestamp="00:20.000",
                category="motion",
                tag="PREFERENCE",
                note="Slow down card entrance.",
            ),
            ReviewLogEntry(
                date="2026-11-10",
                video_id="v-single",
                timestamp="00:30.000",
                category="motion",
                tag="PREFERENCE",
                note="Slow down diagram entrance.",
            ),
            # 3 distinct videos in layout/DON'T -> MUST propose
            ReviewLogEntry(
                date="2026-11-11",
                video_id="vid-a",
                timestamp="00:14.200",
                category="layout",
                tag="DON'T",
                note="Avoid covering chart axis labels in Panel mode.",
            ),
            ReviewLogEntry(
                date="2026-11-15",
                video_id="vid-b",
                timestamp="01:02.000",
                category="layout",
                tag="DON'T",
                note="Keep callout cards clear of chart axes.",
            ),
            ReviewLogEntry(
                date="2026-11-20",
                video_id="vid-c",
                timestamp="02:18.500",
                category="layout",
                tag="DON'T",
                note="Do not obscure Y-axis labels with overlay cards.",
            ),
        ]

        proposals = find_promotion_candidates(entries, min_videos=3)
        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertEqual(proposal.category, "layout")
        self.assertEqual(proposal.tag, "DON'T")
        self.assertEqual(proposal.video_ids, ["vid-a", "vid-b", "vid-c"])
        self.assertEqual(proposal.count, 3)
        self.assertEqual(len(proposal.supporting_entries), 3)

        after_rules = {p.name: p.read_bytes() for p in sorted(rules_dir.glob("*.md"))}
        self.assertEqual(before_rules, after_rules)


if __name__ == "__main__":
    unittest.main()
