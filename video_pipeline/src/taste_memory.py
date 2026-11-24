"""Compounding Taste Profile memory log, synthesis, and rule promotion proposals."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as dt_date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReviewCategory = Literal["sifting", "layout", "motion", "captions", "audio", "pacing"]
ReviewTag = Literal["DO", "DON'T", "PREFERENCE", "NON-NEGOTIABLE"]

TAG_ORDER: tuple[ReviewTag, ...] = ("NON-NEGOTIABLE", "DON'T", "DO", "PREFERENCE")
SECTION_3_HEADER = "## 3. Active Taste Profile"

_DEFAULT_PROFILE_HEADER = """# Taste Profile (Creative Engine Room Memory)

Persistent editorial guidance synthesized from timestamped human review feedback across completed videos. Agents read this file during Stage 2 (Storyboard) and Stage 3 (Visual Build & Revision Passes).
"""


def _require_non_empty(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty.")
    return value


class ReviewLogEntry(BaseModel):
    """Single timestamped human review note stored in review_log.jsonl."""

    model_config = ConfigDict(extra="forbid")

    date: str
    video_id: str
    timestamp: str
    category: ReviewCategory
    tag: ReviewTag
    note: str
    promoted_rule_id: str | None = None

    @field_validator("date")
    @classmethod
    def _validate_iso_date(cls, value: str) -> str:
        _require_non_empty(value, "date")
        dt_date.fromisoformat(value)
        return value

    @field_validator("video_id", "timestamp", "note")
    @classmethod
    def _validate_non_empty(cls, value: str, info: Any) -> str:
        return _require_non_empty(value, info.field_name)


class PromotionProposal(BaseModel):
    """Read-only proposal to promote a recurring pattern to editing_system/rules/."""

    category: ReviewCategory
    tag: ReviewTag
    video_ids: list[str]
    count: int = Field(..., ge=1)
    proposed_rule_summary: str
    supporting_entries: list[ReviewLogEntry]


def append_review_note(log_path: Path, entry: ReviewLogEntry) -> None:
    """Append a single validated ReviewLogEntry line to review_log.jsonl."""
    validated = ReviewLogEntry.model_validate(entry)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    needs_leading_newline = False
    if log_path.exists() and log_path.stat().st_size > 0:
        with log_path.open("rb") as reader:
            reader.seek(-1, 2)
            needs_leading_newline = reader.read(1) != b"\n"

    with log_path.open("a", encoding="utf-8") as handle:
        if needs_leading_newline:
            handle.write("\n")
        handle.write(validated.model_dump_json() + "\n")


def load_review_log(log_path: Path) -> list[ReviewLogEntry]:
    """Load review_log.jsonl entries, handling missing or empty files gracefully."""
    if not log_path.exists():
        return []
    raw = log_path.read_text(encoding="utf-8")
    if not raw.strip():
        return []

    entries: list[ReviewLogEntry] = []
    for line_no, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            entries.append(ReviewLogEntry.model_validate_json(stripped))
        except ValueError as exc:
            raise ValueError(f"Invalid review log entry at {log_path}:{line_no}: {exc}") from exc
    return entries


def _summarize_proposal(
    category: ReviewCategory,
    tag: ReviewTag,
    video_ids: list[str],
    entries: list[ReviewLogEntry],
) -> str:
    unique_notes = list(dict.fromkeys(entry.note.strip() for entry in entries))
    examples = "; ".join(unique_notes[:3])
    return (
        f"Promote {tag} pattern in '{category}' across {len(video_ids)} videos "
        f"({', '.join(video_ids)}): {examples}"
    )


def find_promotion_candidates(
    entries: list[ReviewLogEntry],
    min_videos: int = 3,
) -> list[PromotionProposal]:
    """Detect unpromoted patterns recurring across >= min_videos distinct video_ids.

    Never mutates editing_system/rules/ files; returns read-only proposals for human approval.
    """
    if min_videos < 1:
        raise ValueError("min_videos must be at least 1.")

    unpromoted = [entry for entry in entries if not entry.promoted_rule_id]
    by_category_tag: dict[tuple[ReviewCategory, ReviewTag], list[ReviewLogEntry]] = defaultdict(list)
    by_category: dict[ReviewCategory, list[ReviewLogEntry]] = defaultdict(list)

    for entry in unpromoted:
        by_category_tag[(entry.category, entry.tag)].append(entry)
        by_category[entry.category].append(entry)

    proposals: list[PromotionProposal] = []
    covered_categories: set[ReviewCategory] = set()

    for (category, tag), bucket in by_category_tag.items():
        video_ids = list(dict.fromkeys(item.video_id for item in bucket))
        if len(video_ids) >= min_videos:
            covered_categories.add(category)
            proposals.append(
                PromotionProposal(
                    category=category,
                    tag=tag,
                    video_ids=video_ids,
                    count=len(video_ids),
                    proposed_rule_summary=_summarize_proposal(category, tag, video_ids, bucket),
                    supporting_entries=list(bucket),
                )
            )

    tag_priority = {tag: idx for idx, tag in enumerate(TAG_ORDER)}
    for category, bucket in by_category.items():
        if category in covered_categories:
            continue
        video_ids = list(dict.fromkeys(item.video_id for item in bucket))
        if len(video_ids) >= min_videos:
            dominant_tag = min((item.tag for item in bucket), key=lambda t: tag_priority[t])
            proposals.append(
                PromotionProposal(
                    category=category,
                    tag=dominant_tag,
                    video_ids=video_ids,
                    count=len(video_ids),
                    proposed_rule_summary=_summarize_proposal(
                        category, dominant_tag, video_ids, bucket
                    ),
                    supporting_entries=list(bucket),
                )
            )

    return proposals


def _format_entry_bullet(entry: ReviewLogEntry) -> str:
    promoted = f" [promoted: {entry.promoted_rule_id}]" if entry.promoted_rule_id else ""
    return (
        f"- **[{entry.category}]** {entry.note} "
        f"_({entry.video_id} @ {entry.timestamp}, {entry.date})_{promoted}"
    )


def _extract_profile_prefix(profile_path: Path) -> str:
    if not profile_path.exists():
        return _DEFAULT_PROFILE_HEADER.rstrip()
    existing = profile_path.read_text(encoding="utf-8")
    idx = existing.find(SECTION_3_HEADER)
    if idx == -1:
        return existing.rstrip()
    return existing[:idx].rstrip()


def render_taste_profile_md(entries: list[ReviewLogEntry], profile_path: Path) -> str:
    """Preserve Sections 1 and 2 of taste_profile.md and rewrite Section 3 grouped by tag."""
    prefix = _extract_profile_prefix(profile_path)
    grouped: dict[ReviewTag, list[ReviewLogEntry]] = {tag: [] for tag in TAG_ORDER}
    for entry in entries:
        grouped[entry.tag].append(entry)

    lines: list[str] = [prefix, "", SECTION_3_HEADER, ""]
    if not entries:
        lines.append(
            "*No historical video reviews recorded yet. "
            "Entries synthesized from `review_log.jsonl` will populate below by tag:*"
        )
    else:
        video_count = len({entry.video_id for entry in entries})
        lines.append(
            f"*Synthesized from {len(entries)} review note(s) across {video_count} video(s):*"
        )

    for tag in TAG_ORDER:
        lines.extend(["", f"### {tag}"])
        bucket = grouped[tag]
        if not bucket:
            lines.append("- *(none recorded yet)*")
        else:
            for entry in bucket:
                lines.append(_format_entry_bullet(entry))

    rendered = "\n".join(lines).rstrip() + "\n"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(rendered, encoding="utf-8")
    return rendered
