"""Scientific Sifting (Stage 1): adaptive room tone, dead-space cuts, consonant tails, retakes, and fillers."""

from __future__ import annotations

from difflib import SequenceMatcher
import math
import re
import sys
import wave
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np
from pydantic import BaseModel, Field

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from assemble import assemble_rough_cut, remap_timeline  # noqa: E402
from cursor_events import CursorEventLog  # noqa: E402
from ingest import probe_video  # noqa: E402
from schema import (  # noqa: E402
    EditDecisionList,
    KeepSegment,
    TranscriptBundle,
    TranscriptSegment,
    WordTiming,
)
from timeline_otio import edl_to_otio, save_otio  # noqa: E402

SIFT_STEPS_ORDER: tuple[str, ...] = (
    "sync",
    "dead_space",
    "retakes_and_mistakes",
    "filler_words",
)

CONSONANT_TAIL_CHARS: frozenset[str] = frozenset({"s", "t", "d", "k", "p"})

SPOKEN_RETAKE_CUES: tuple[tuple[str, ...], ...] = (
    ("retake",),
    ("scratch", "that"),
    ("take", "two"),
    ("start", "over"),
    ("let", "me", "restart"),
    ("cut", "cut"),
)

TIER_A_FILLERS: tuple[str, ...] = (
    "um",
    "uh",
    "uhh",
    "umm",
    "er",
    "erm",
    "ah",
    "hmm",
    "eh",
    "mm",
    "mhm",
    "uh-huh",
)

TIER_B_FILLERS: tuple[str, ...] = (
    "like",
    "you know",
    "i mean",
    "so",
    "well",
    "actually",
    "basically",
    "literally",
    "right",
    "okay",
    "kind of",
    "sort of",
    "honestly",
)

_TIER_A_SET: frozenset[str] = frozenset(TIER_A_FILLERS)
_TIER_B_SET: frozenset[str] = frozenset(TIER_B_FILLERS)
_TWO_WORD_TIER_B: frozenset[tuple[str, str]] = frozenset(
    tuple(item.split()) for item in TIER_B_FILLERS if " " in item  # type: ignore[misc]
)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
_EDGE_PUNCT = ".,!?;:\"'()[]{}<>"

_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "so",
        "that",
        "the",
        "this",
        "to",
        "was",
        "we",
        "were",
        "will",
        "with",
        "you",
    }
)

_INCOMPLETE_TRAILING: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "if",
        "in",
        "into",
        "is",
        "of",
        "on",
        "or",
        "that",
        "the",
        "these",
        "this",
        "to",
        "was",
        "we",
        "were",
        "with",
        "you",
    }
)

_REPHRASE_CUES: tuple[tuple[str, ...], ...] = (
    ("in", "other", "words"),
    ("put", "differently"),
    ("to", "put", "it", "another", "way"),
    ("let", "me", "rephrase"),
    ("that", "is", "to", "say"),
)

_REPLACEMENT_CUES: tuple[tuple[str, ...], ...] = (
    ("wait", "no"),
    ("actually", "no"),
    ("no", "wait"),
    ("make", "that"),
    ("sorry",),
)

_EXCEPTION_CALLBACK_PHRASES: tuple[tuple[str, ...], ...] = (
    ("as", "i", "mentioned"),
    ("remember", "earlier"),
    ("like", "we", "saw"),
    ("as", "we", "saw"),
    ("to", "recap"),
    ("once", "more"),
    ("once", "again"),
    ("step", "by", "step"),
    ("line", "by", "line"),
    ("one", "by", "one"),
    ("day", "after", "day"),
    ("again", "and", "again"),
    ("more", "and", "more"),
    ("less", "and", "less"),
    ("over", "and", "over"),
)


class RoomToneProfile(BaseModel):
    """Per-recording Room Tone baseline measured via 10ms RMS window percentiles."""

    room_tone_dbfs: float
    speech_threshold_dbfs: float
    window_ms: float = 10.0
    quiet_percentile: float = 10.0
    sample_rate: int
    duration_sec: float
    window_count: int
    peak_dbfs: float = 0.0
    median_dbfs: float = -60.0


class ProtectedHold(BaseModel):
    """Non-speaking gap preserved because of screen motion, cursor activity, or declared reading hold."""

    start: float
    end: float
    duration: float
    reason: str
    source: Literal["video_motion", "cursor", "declared", "combined"]
    motion_score: float = 0.0
    cursor_events_count: int = 0


class RetakeAuditItem(BaseModel):
    """Classified retake, self-correction, or intentional rhetorical exception."""

    segment_id: int
    category: Literal["Repeats", "Reopens", "Replacements", "Rephrases", "Exceptions"]
    status: Literal["auto_cut", "proposed", "preserved"]
    start: float
    end: float
    text: str
    reason: str
    confidence: float
    prev_context: str = ""
    next_context: str = ""
    matched_cue: str | None = None


class FillerAuditItem(BaseModel):
    """Tier A hesitation or Tier B context-sensitive verbal filler."""

    word: str
    normalized: str
    tier: Literal["A", "B"]
    status: Literal["auto_cut", "proposed", "preserved"]
    start: float
    end: float
    segment_id: int
    confidence: float
    isolated: bool = False
    prev_word: str = ""
    next_word: str = ""
    context_note: str = ""


class CutAuditItem(BaseModel):
    """Unified cut/proposal/protection record emitted in cut_audit.json."""

    step: Literal["dead_space", "retakes_and_mistakes", "filler_words"]
    category: str
    status: Literal["auto_cut", "proposed", "preserved", "protected"]
    start: float
    end: float
    duration: float
    confidence: float
    reason: str
    prev_word: str = ""
    next_word: str = ""
    consonant_tail_extended: bool = False
    safety_frames_added: int = 0


class SiftResult(BaseModel):
    """Complete audit report and output paths from Stage 1 Scientific Sifting."""

    source_path: str
    camera_path: str | None = None
    wav_path: str
    fps: float
    steps_executed: list[str]
    sync_report: dict[str, Any] = Field(default_factory=dict)
    room_tone: RoomToneProfile
    duration_before: float
    duration_after: float
    unique_removed_seconds: float
    protected_holds: list[ProtectedHold] = Field(default_factory=list)
    retake_items: list[RetakeAuditItem] = Field(default_factory=list)
    filler_items: list[FillerAuditItem] = Field(default_factory=list)
    untranscribed_stutters: list[dict[str, Any]] = Field(default_factory=list)
    cut_items: list[CutAuditItem] = Field(default_factory=list)
    kept_segments: list[KeepSegment] = Field(default_factory=list)
    edl_path: str
    otio_path: str
    cut_audit_path: str
    rough_cut_video_path: str | None = None
    rough_camera_video_path: str | None = None
    timeline_manifest_path: str | None = None


def _load_wav_mono(wav_path: Path) -> tuple[np.ndarray, int]:
    """Read a PCM WAV file using stdlib wave into normalized mono float64 samples [-1, 1]."""
    with wave.open(str(wav_path), "rb") as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if not raw or n_frames == 0:
        return np.zeros(0, dtype=np.float64), sample_rate

    if sampwidth == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    elif sampwidth == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif sampwidth == 3:
        raw_u8 = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        signed = (
            raw_u8[:, 0].astype(np.int32)
            | (raw_u8[:, 1].astype(np.int32) << 8)
            | (raw_u8[:, 2].astype(np.int32) << 16)
        )
        signed = np.where(signed & 0x800000, signed - 0x1000000, signed)
        samples = signed.astype(np.float64) / 8388608.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sampwidth} bytes")

    if n_channels > 1:
        usable = (len(samples) // n_channels) * n_channels
        samples = samples[:usable].reshape(-1, n_channels).mean(axis=1)

    return samples, sample_rate


def _window_rms_dbfs(samples: np.ndarray, sample_rate: int, window_ms: float = 10.0) -> np.ndarray:
    """Compute per-window RMS levels in dBFS for fixed millisecond slices."""
    if len(samples) == 0:
        return np.array([-120.0], dtype=np.float64)

    win_samples = max(1, int(round(sample_rate * (window_ms / 1000.0))))
    n_full = len(samples) // win_samples
    eps = 1e-6

    if n_full == 0:
        rms = float(np.sqrt(np.mean(samples**2)))
        return np.array([20.0 * math.log10(max(rms, eps))], dtype=np.float64)

    trimmed = samples[: n_full * win_samples].reshape(n_full, win_samples)
    rms_vals = np.sqrt(np.mean(trimmed**2, axis=1))
    dbfs = 20.0 * np.log10(np.maximum(rms_vals, eps))

    rem = len(samples) - n_full * win_samples
    if rem >= max(1, win_samples // 2):
        tail_rms = float(np.sqrt(np.mean(samples[n_full * win_samples :] ** 2)))
        dbfs = np.append(dbfs, 20.0 * math.log10(max(tail_rms, eps)))

    return dbfs


def measure_adaptive_room_tone(
    wav_path: Path,
    window_ms: float = 10.0,
    quiet_percentile: float = 10.0,
) -> RoomToneProfile:
    """Measure per-recording Room Tone from the quietest percentile of 10ms RMS windows."""
    samples, sample_rate = _load_wav_mono(Path(wav_path))
    duration_sec = len(samples) / sample_rate if sample_rate > 0 else 0.0
    window_dbfs = _window_rms_dbfs(samples, sample_rate, window_ms=window_ms)

    room_tone_dbfs = float(np.percentile(window_dbfs, quiet_percentile))
    speech_threshold_dbfs = min(-12.0, max(room_tone_dbfs + 10.0, -50.0))

    return RoomToneProfile(
        room_tone_dbfs=round(room_tone_dbfs, 3),
        speech_threshold_dbfs=round(speech_threshold_dbfs, 3),
        window_ms=window_ms,
        quiet_percentile=quiet_percentile,
        sample_rate=sample_rate,
        duration_sec=round(duration_sec, 6),
        window_count=int(len(window_dbfs)),
        peak_dbfs=round(float(np.max(window_dbfs)), 3),
        median_dbfs=round(float(np.median(window_dbfs)), 3),
    )


def snap_to_frame(
    seconds: float,
    fps: float,
    mode: Literal["nearest", "floor", "ceil"] = "nearest",
) -> float:
    """Quantize a timestamp in seconds onto the exact source video frame grid."""
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")

    exact_frames = seconds * fps
    if mode == "nearest":
        frame_idx = int(round(exact_frames))
    elif mode == "floor":
        frame_idx = math.floor(exact_frames + 1e-9)
    elif mode == "ceil":
        frame_idx = math.ceil(exact_frames - 1e-9)
    else:
        raise ValueError(f"Unsupported snap mode: {mode!r}")

    frame_idx = max(0, frame_idx)
    return frame_idx / fps


def _trailing_alpha_char(word_text: str) -> str:
    """Return the final alphabetic character ignoring trailing punctuation, or ''."""
    for ch in reversed(word_text.strip()):
        if ch.isalpha():
            return ch.lower()
    return ""


def _protect_consonant_tail_detail(
    samples: np.ndarray,
    sample_rate: int,
    word: WordTiming,
    next_word: WordTiming | None,
    room_tone_dbfs: float,
    fps: float,
) -> tuple[float, float, bool, int]:
    """Compute consonant-tail-safe cut boundaries plus audit flags."""
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")

    audio_dur = len(samples) / sample_rate if sample_rate > 0 else word.end
    if next_word is not None:
        raw_in = max(0.0, next_word.start - 1.0 / fps)
        cut_in = snap_to_frame(raw_in, fps, mode="floor")
    else:
        cut_in = snap_to_frame(audio_dur, fps, mode="floor")

    tail_char = _trailing_alpha_char(word.word)
    if tail_char not in CONSONANT_TAIL_CHARS or sample_rate <= 0 or len(samples) == 0:
        cut_out = min(cut_in, snap_to_frame(word.end, fps, mode="ceil"))
        return cut_out, cut_in, False, 0

    tail_floor_dbfs = max(-50.0, room_tone_dbfs + 2.0)
    upper_bound = word.end + 0.35
    if next_word is not None:
        upper_bound = min(upper_bound, max(word.end, next_word.start - 1.0 / fps))
    upper_bound = min(upper_bound, audio_dur)

    win_sec = 0.01
    win_samples = max(1, int(round(sample_rate * win_sec)))
    eps = 1e-6

    t = max(0.0, word.end)
    last_active_end = word.end
    saw_tail_energy = False
    decayed_cleanly = False
    quiet_streak = 0

    while t + win_sec * 0.5 <= upper_bound:
        idx0 = int(round(t * sample_rate))
        idx1 = min(len(samples), idx0 + win_samples)
        if idx1 <= idx0:
            break
        rms = float(np.sqrt(np.mean(samples[idx0:idx1] ** 2)))
        win_dbfs = 20.0 * math.log10(max(rms, eps))
        w_end = min(upper_bound, t + win_sec)
        if win_dbfs > tail_floor_dbfs:
            last_active_end = w_end
            saw_tail_energy = True
            quiet_streak = 0
        else:
            quiet_streak += 1
            if quiet_streak >= 2:
                decayed_cleanly = True
                break
        t += win_sec

    safety_frames = 0
    if saw_tail_energy and not decayed_cleanly:
        # Energy remained ambiguous up to the scan cap; add 3 safety frames.
        safety_frames = 3
        raw_out = last_active_end + (safety_frames / fps)
        cut_out = snap_to_frame(raw_out, fps, mode="ceil")
    elif saw_tail_energy:
        cut_out = snap_to_frame(last_active_end, fps, mode="ceil")
    else:
        cut_out = snap_to_frame(word.end, fps, mode="ceil")

    extended = cut_out > snap_to_frame(word.end, fps, mode="ceil") + 1e-9 or safety_frames > 0
    cut_out = min(cut_out, cut_in)
    return cut_out, cut_in, extended, safety_frames


def protect_consonant_tail(
    samples: np.ndarray,
    sample_rate: int,
    word: WordTiming,
    next_word: WordTiming | None,
    room_tone_dbfs: float,
    fps: float,
) -> tuple[float, float]:
    """Protect S/T/D/K/P consonant tails and snap cut boundaries to the frame grid."""
    cut_out, cut_in, _, _ = _protect_consonant_tail_detail(
        samples=samples,
        sample_rate=sample_rate,
        word=word,
        next_word=next_word,
        room_tone_dbfs=room_tone_dbfs,
        fps=fps,
    )
    return cut_out, cut_in


def _measure_video_gap_motion(
    cap: cv2.VideoCapture,
    fps: float,
    total_frames: int,
    gap_start: float,
    gap_end: float,
) -> tuple[bool, float]:
    """Sample downscaled grayscale frames across a gap and detect visual activity."""
    if gap_end <= gap_start:
        return False, 0.0

    sample_times = np.linspace(gap_start, gap_end, num=8)
    prev_gray: np.ndarray | None = None
    max_mean_diff = 0.0
    max_active_frac = 0.0

    for t in sample_times:
        if total_frames > 0:
            frame_idx = min(total_frames - 1, max(0, int(round(float(t) * fps))))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        else:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000.0)

        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
        if prev_gray is not None:
            diff = np.abs(small.astype(np.float32) - prev_gray.astype(np.float32))
            mean_diff = float(np.mean(diff))
            active_frac = float(np.mean(diff > 15.0))
            max_mean_diff = max(max_mean_diff, mean_diff)
            max_active_frac = max(max_active_frac, active_frac)
        prev_gray = small

    has_motion = max_mean_diff >= 1.5 or max_active_frac >= 0.002
    return has_motion, round(max_mean_diff, 4)


def detect_visual_activity_holds(
    video_path: Path | None,
    gaps: list[tuple[float, float]],
    cursor_log: CursorEventLog | None = None,
    declared_holds: list[tuple[float, float]] | None = None,
) -> list[ProtectedHold]:
    """Identify gaps that hold screen motion, cursor activity, or declared reading holds."""
    if not gaps:
        return []

    cap: cv2.VideoCapture | None = None
    cap_fps = 30.0
    cap_frames = 0
    if video_path is not None and Path(video_path).exists():
        candidate_cap = cv2.VideoCapture(str(video_path))
        if candidate_cap.isOpened():
            cap = candidate_cap
            cap_fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
            if cap_fps <= 0:
                cap_fps = 30.0
            cap_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        else:
            candidate_cap.release()

    holds: list[ProtectedHold] = []
    try:
        for g_start, g_end in sorted(gaps):
            if g_end <= g_start:
                continue

            reasons: list[str] = []
            sources: list[str] = []
            motion_score = 0.0
            cursor_count = 0

            if declared_holds:
                for h_start, h_end in declared_holds:
                    if min(g_end, h_end) > max(g_start, h_start):
                        reasons.append(f"declared reading hold ({h_start:.2f}s..{h_end:.2f}s)")
                        sources.append("declared")
                        break

            if cursor_log is not None and cursor_log.events:
                in_gap = [ev for ev in cursor_log.events if g_start <= ev.t <= g_end]
                cursor_count = len(in_gap)
                clicks = [ev for ev in in_gap if ev.kind == "click"]
                move_dist = 0.0
                if len(in_gap) >= 2:
                    for a, b in zip(in_gap, in_gap[1:]):
                        move_dist += math.hypot(b.x - a.x, b.y - a.y)
                if clicks:
                    reasons.append(f"cursor click activity ({len(clicks)} click(s))")
                    sources.append("cursor")
                elif move_dist >= 0.02:
                    reasons.append(f"cursor movement ({move_dist:.3f} normalized travel)")
                    sources.append("cursor")

            if cap is not None:
                has_motion, motion_score = _measure_video_gap_motion(
                    cap,
                    cap_fps,
                    cap_frames,
                    g_start,
                    g_end,
                )
                if has_motion:
                    reasons.append(f"screen motion (mean_abs_diff={motion_score:.2f})")
                    sources.append("video_motion")

            if sources:
                unique_sources = set(sources)
                src_label: Literal["video_motion", "cursor", "declared", "combined"]
                if len(unique_sources) > 1:
                    src_label = "combined"
                else:
                    src_label = sources[0]  # type: ignore[assignment]
                holds.append(
                    ProtectedHold(
                        start=round(g_start, 6),
                        end=round(g_end, 6),
                        duration=round(g_end - g_start, 6),
                        reason="; ".join(reasons),
                        source=src_label,
                        motion_score=motion_score,
                        cursor_events_count=cursor_count,
                    )
                )
    finally:
        if cap is not None:
            cap.release()

    return holds


def _normalize_tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _find_phrase(tokens: list[str], phrases: tuple[tuple[str, ...], ...]) -> str | None:
    for phrase in phrases:
        size = len(phrase)
        for i in range(len(tokens) - size + 1):
            if tuple(tokens[i : i + size]) == phrase:
                return " ".join(phrase)
    return None


def _has_deliberate_repetition(tokens: list[str]) -> str | None:
    if phrase := _find_phrase(tokens, _EXCEPTION_CALLBACK_PHRASES):
        return phrase
    for a, b in zip(tokens, tokens[1:]):
        if a == b and a in {"no", "yes", "very", "really", "never", "always", "more"}:
            return f"{a} {b}"
    return None


def _has_intra_replacement(tokens: list[str]) -> str | None:
    if phrase := _find_phrase(tokens, _REPLACEMENT_CUES):
        return phrase
    for i in range(len(tokens) - 2):
        if tokens[i] == "i" and tokens[i + 1] == "mean" and i > 0:
            after_count = len(tokens) - (i + 2)
            if 1 <= after_count <= 3:
                return "i mean"
    return None


def _shared_prefix_len(a: list[str], b: list[str]) -> int:
    count = 0
    for ta, tb in zip(a, b):
        if ta == tb:
            count += 1
        else:
            break
    return count


def _shared_suffix_len(a: list[str], b: list[str]) -> int:
    count = 0
    for ta, tb in zip(reversed(a), reversed(b)):
        if ta == tb:
            count += 1
        else:
            break
    return count


def _content_tokens(tokens: list[str]) -> list[str]:
    return [tok for tok in tokens if tok not in _STOPWORDS and len(tok) >= 3]


def _content_overlap(a: list[str], b: list[str]) -> tuple[int, float]:
    ca = set(_content_tokens(a))
    cb = set(_content_tokens(b))
    if not ca or not cb:
        return 0, 0.0
    shared = len(ca & cb)
    return shared, shared / max(1, min(len(ca), len(cb)))


def classify_retakes(segments: list[TranscriptSegment]) -> list[RetakeAuditItem]:
    """Classify retake candidates into Repeats, Reopens, Replacements, Rephrases, and Exceptions."""
    items_by_id: dict[int, RetakeAuditItem] = {}
    tokenized = [_normalize_tokens(seg.text) for seg in segments]
    cmp_tokenized = [[tok for tok in toks if tok not in _TIER_A_SET] for toks in tokenized]
    terminal = [seg.text.strip().endswith((".", "!", "?")) for seg in segments]

    def _add(
        idx: int,
        category: Literal["Repeats", "Reopens", "Replacements", "Rephrases", "Exceptions"],
        status: Literal["auto_cut", "proposed", "preserved"],
        reason: str,
        confidence: float,
        matched_cue: str | None = None,
    ) -> None:
        seg = segments[idx]
        if seg.id in items_by_id:
            return
        prev_ctx = segments[idx - 1].text if idx > 0 else ""
        next_ctx = segments[idx + 1].text if idx + 1 < len(segments) else ""
        items_by_id[seg.id] = RetakeAuditItem(
            segment_id=seg.id,
            category=category,
            status=status,
            start=seg.start,
            end=seg.end,
            text=seg.text,
            reason=reason,
            confidence=round(confidence, 3),
            prev_context=prev_ctx,
            next_context=next_ctx,
            matched_cue=matched_cue,
        )

    for idx, curr in enumerate(segments):
        curr_tokens = tokenized[idx]
        if not curr_tokens or curr.id in items_by_id:
            continue

        # 1. Explicit spoken retake cue ("retake", "scratch that", "take two", etc.)
        if cue := _find_phrase(curr_tokens, SPOKEN_RETAKE_CUES):
            if idx > 0 and len(curr_tokens) <= 4:
                _add(
                    idx - 1,
                    "Repeats",
                    "auto_cut",
                    f"Aborted take preceding spoken retake cue '{cue}'",
                    0.96,
                    matched_cue=cue,
                )
            _add(
                idx,
                "Repeats",
                "auto_cut",
                f"Spoken retake cue '{cue}'",
                0.98,
                matched_cue=cue,
            )
            continue

        # 2. Intra-segment deliberate callbacks / rhetorical emphasis -> Exceptions
        if exc_phrase := _has_deliberate_repetition(curr_tokens):
            _add(
                idx,
                "Exceptions",
                "preserved",
                f"Deliberate rhetorical callback/repetition ('{exc_phrase}')",
                0.9,
                matched_cue=exc_phrase,
            )
            continue

        # 3. Intra-segment self-correction cue -> Replacements
        if rep_cue := _has_intra_replacement(curr_tokens):
            _add(
                idx,
                "Replacements",
                "proposed",
                f"Mid-sentence self-correction ('{rep_cue}')",
                0.84,
                matched_cue=rep_cue,
            )
            continue

        if idx + 1 >= len(segments):
            continue

        nxt = segments[idx + 1]
        nxt_tokens = tokenized[idx + 1]
        curr_cmp = cmp_tokenized[idx] or curr_tokens
        nxt_cmp = cmp_tokenized[idx + 1] or nxt_tokens
        if not nxt_tokens:
            continue

        prefix_len = _shared_prefix_len(curr_cmp, nxt_cmp)
        suffix_len = _shared_suffix_len(curr_cmp, nxt_cmp)
        seq_ratio = SequenceMatcher(None, curr_cmp, nxt_cmp).ratio()
        overlap_ratio = len(set(curr_cmp) & set(nxt_cmp)) / max(1, len(set(curr_cmp)))
        shared_content, content_ov = _content_overlap(curr_cmp, nxt_cmp)
        pause_sec = max(0.0, nxt.start - curr.end)

        # 4. Cross-segment rhetorical parallel sentences -> Exceptions (preserved)
        if (
            terminal[idx]
            and terminal[idx + 1]
            and len(curr_cmp) >= 3
            and len(nxt_cmp) >= 3
            and 1 <= prefix_len <= 3
            and curr_cmp != nxt_cmp
            and curr_cmp[-1] not in _INCOMPLETE_TRAILING
            and content_ov < 0.45
            and seq_ratio < 0.65
        ):
            _add(
                idx,
                "Exceptions",
                "preserved",
                f"Parallel rhetorical sentence structure (shared {prefix_len}-word opener, distinct content)",
                0.85,
            )
            continue

        # 5. Exact duplicate or aborted prefix restart -> Repeats (auto_cut)
        is_exact_repeat = curr_cmp == nxt_cmp
        is_exact_prefix_stub = (
            prefix_len >= 2
            and prefix_len == len(curr_cmp)
            and len(curr_cmp) < len(nxt_cmp)
        )
        is_aborted_fragment = (
            prefix_len >= 2
            and len(curr_cmp) + 2 <= len(nxt_cmp)
            and (not terminal[idx] or curr_cmp[-1] in _INCOMPLETE_TRAILING)
        )
        is_short_pause_abort = (
            prefix_len >= 1
            and len(curr_cmp) <= 4
            and not terminal[idx]
            and pause_sec >= 0.8
            and len(nxt_cmp) >= len(curr_cmp) + 2
        )
        if is_exact_repeat or is_exact_prefix_stub or is_aborted_fragment or is_short_pause_abort:
            _add(
                idx,
                "Repeats",
                "auto_cut",
                f"Repeated/aborted take ({prefix_len}-word shared prefix, {overlap_ratio:.0%} token overlap)",
                0.93 if (is_exact_repeat or is_exact_prefix_stub) else 0.88,
            )
            continue

        # 6. Word swap / substitution across adjacent segments -> Replacements (proposed)
        len_diff = abs(len(curr_cmp) - len(nxt_cmp))
        sym_diff = set(curr_cmp) ^ set(nxt_cmp)
        if (
            len(curr_cmp) >= 3
            and len_diff <= 2
            and seq_ratio >= 0.65
            and (prefix_len >= 2 or (prefix_len >= 1 and suffix_len >= 1))
            and 1 <= len(sym_diff) <= 4
            and (len(curr_cmp) < 6 or len_diff <= 1)
        ):
            _add(
                idx,
                "Replacements",
                "proposed",
                f"Swapped-word self-correction across adjacent takes (similarity {seq_ratio:.0%})",
                0.8,
            )
            continue

        # 7. Full passage reopened & re-delivered -> Reopens (proposed)
        reopen_match = False
        for lookahead in (idx + 1, idx + 2):
            if lookahead >= len(segments):
                continue
            cand_tokens = cmp_tokenized[lookahead] or tokenized[lookahead]
            if not cand_tokens or len(curr_cmp) < 5:
                continue
            cand_prefix = _shared_prefix_len(curr_cmp, cand_tokens)
            cand_seq = SequenceMatcher(None, curr_cmp, cand_tokens).ratio()
            _, cand_content_ov = _content_overlap(curr_cmp, cand_tokens)
            if cand_seq >= 0.65 or (cand_prefix >= 2 and cand_content_ov >= 0.65) or (
                lookahead > idx + 1 and cand_content_ov >= 0.65
            ):
                reopen_match = True
                break
        if reopen_match:
            _add(
                idx,
                "Reopens",
                "proposed",
                f"Passage re-opened and re-delivered ({len(curr_cmp)} words, {overlap_ratio:.0%} overlap)",
                0.78,
            )
            continue

        # 8. Restating the same thought with different phrasing -> Rephrases (proposed)
        if rephrase_cue := _find_phrase(nxt_cmp[:5], _REPHRASE_CUES):
            _add(
                idx,
                "Rephrases",
                "proposed",
                f"Next segment opens with rephrase bridge '{rephrase_cue}'",
                0.82,
                matched_cue=rephrase_cue,
            )
            continue

        if shared_content >= 2 and content_ov >= 0.40 and seq_ratio < 0.70:
            _add(
                idx,
                "Rephrases",
                "proposed",
                f"Restated thought with altered phrasing ({shared_content} shared content terms, {content_ov:.0%} overlap)",
                0.72,
            )

    return [items_by_id[seg.id] for seg in segments if seg.id in items_by_id]


def _clean_word_token(raw: str) -> str:
    return raw.strip().lower().strip(_EDGE_PUNCT)


def _check_filler_acoustic_isolation(
    samples: np.ndarray,
    sample_rate: int,
    start: float,
    end: float,
    gap_before: float,
    gap_after: float,
) -> bool:
    """Verify whether a Tier A hesitation has clean acoustic margins around it."""
    if gap_before >= 0.02 and gap_after >= 0.02:
        return True
    if sample_rate <= 0 or len(samples) == 0:
        return gap_before >= -0.01 and gap_after >= -0.01

    eps = 1e-6
    i0 = max(0, int(round(start * sample_rate)))
    i1 = min(len(samples), int(round(end * sample_rate)))
    if i1 <= i0:
        return False

    word_rms = float(np.sqrt(np.mean(samples[i0:i1] ** 2)))
    word_db = 20.0 * math.log10(max(word_rms, eps))

    pad = max(1, int(round(0.015 * sample_rate)))
    left_ok = gap_before >= 0.015
    if not left_ok and i0 >= pad:
        left_rms = float(np.sqrt(np.mean(samples[i0 - pad : i0] ** 2)))
        left_db = 20.0 * math.log10(max(left_rms, eps))
        left_ok = left_db <= word_db - 4.0

    right_ok = gap_after >= 0.015
    if not right_ok and i1 + pad <= len(samples):
        right_rms = float(np.sqrt(np.mean(samples[i1 : i1 + pad] ** 2)))
        right_db = 20.0 * math.log10(max(right_rms, eps))
        right_ok = right_db <= word_db - 4.0

    # If transcript has no tight overlap and either side shows a pause/dip, treat as isolated.
    if gap_before >= -0.01 and gap_after >= -0.01 and (left_ok or right_ok):
        return True
    return left_ok and right_ok


def audit_raw_audio_stutters(
    wav_path: Path,
    segments: list[TranscriptSegment],
    room_tone: RoomToneProfile,
) -> list[dict[str, Any]]:
    """Detect short un-transcribed waveform energy bursts between words/segments."""
    samples, sample_rate = _load_wav_mono(Path(wav_path))
    if len(samples) == 0 or sample_rate <= 0:
        return []

    win_ms = room_tone.window_ms or 10.0
    win_sec = win_ms / 1000.0
    dbfs = _window_rms_dbfs(samples, sample_rate, window_ms=win_ms)
    burst_thresh = max(room_tone.speech_threshold_dbfs, room_tone.room_tone_dbfs + 10.0)

    transcribed_ranges: list[tuple[float, float]] = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                transcribed_ranges.append((max(0.0, w.start - 0.03), w.end + 0.03))
        else:
            transcribed_ranges.append((max(0.0, seg.start - 0.03), seg.end + 0.03))

    stutters: list[dict[str, Any]] = []
    active_start_idx: int | None = None

    def _emit_run(start_idx: int, end_idx: int) -> None:
        s_t = start_idx * win_sec
        e_t = end_idx * win_sec
        dur = e_t - s_t
        if not (0.03 <= dur <= 0.45):
            return
        overlap = 0.0
        for rs, re_ in transcribed_ranges:
            ov = min(e_t, re_) - max(s_t, rs)
            if ov > 0:
                overlap += ov
        if overlap > dur * 0.2:
            return

        run_slice = dbfs[start_idx:end_idx]
        nearest_seg_id: int | None = None
        if segments:
            mid = (s_t + e_t) / 2.0
            nearest_seg_id = min(
                segments,
                key=lambda seg: min(abs(mid - seg.start), abs(mid - seg.end)),
            ).id

        stutters.append(
            {
                "start": round(s_t, 4),
                "end": round(e_t, 4),
                "duration": round(dur, 4),
                "peak_dbfs": round(float(np.max(run_slice)), 3),
                "mean_dbfs": round(float(np.mean(run_slice)), 3),
                "reason": "untranscribed_waveform_burst",
                "nearest_segment_id": nearest_seg_id,
                "status": "proposed",
            }
        )

    for idx, val in enumerate(dbfs):
        if val > burst_thresh:
            if active_start_idx is None:
                active_start_idx = idx
        elif active_start_idx is not None:
            _emit_run(active_start_idx, idx)
            active_start_idx = None

    if active_start_idx is not None:
        _emit_run(active_start_idx, len(dbfs))

    return stutters


def _detect_tiered_fillers_with_audio(
    segments: list[TranscriptSegment],
    samples: np.ndarray | None,
    sample_rate: int,
    wav_path: Path | None,
    room_tone: RoomToneProfile | None,
) -> tuple[list[FillerAuditItem], list[dict[str, Any]]]:
    """Detect Tier A/B fillers and optional raw-audio stutters using preloaded audio."""
    flat_words: list[tuple[int, WordTiming]] = []
    for seg in segments:
        for w in seg.words:
            flat_words.append((seg.id, w))

    items: list[FillerAuditItem] = []
    idx = 0
    total = len(flat_words)
    while idx < total:
        seg_id, w = flat_words[idx]
        tok1 = _clean_word_token(w.word)
        prev_w = flat_words[idx - 1][1] if idx > 0 else None
        prev_label = prev_w.word.strip() if prev_w else ""

        # Check 2-word combinations first ("uh huh" -> "uh-huh", "you know", "i mean", "kind of", "sort of").
        if idx + 1 < total and flat_words[idx + 1][0] == seg_id:
            w2 = flat_words[idx + 1][1]
            tok2 = _clean_word_token(w2.word)
            next_w = flat_words[idx + 2][1] if idx + 2 < total else None
            next_label = next_w.word.strip() if next_w else ""

            if (tok1, tok2) == ("uh", "huh"):
                gap_before = w.start - prev_w.end if prev_w else w.start
                gap_after = next_w.start - w2.end if next_w else 1.0
                if samples is not None:
                    isolated = _check_filler_acoustic_isolation(
                        samples, sample_rate, w.start, w2.end, gap_before, gap_after
                    )
                else:
                    isolated = gap_before >= -0.01 and gap_after >= -0.01 and (w2.end - w.start) >= 0.05
                items.append(
                    FillerAuditItem(
                        word=f"{w.word.strip()} {w2.word.strip()}",
                        normalized="uh-huh",
                        tier="A",
                        status="auto_cut" if isolated else "proposed",
                        start=w.start,
                        end=w2.end,
                        segment_id=seg_id,
                        confidence=0.95 if isolated else 0.7,
                        isolated=isolated,
                        prev_word=prev_label,
                        next_word=next_label,
                        context_note="Pure hesitation sound (isolated)" if isolated else "Tight neighbor margins; verify before cutting",
                    )
                )
                idx += 2
                continue

            if (tok1, tok2) in _TWO_WORD_TIER_B:
                phrase = f"{tok1} {tok2}"
                items.append(
                    FillerAuditItem(
                        word=f"{w.word.strip()} {w2.word.strip()}",
                        normalized=phrase,
                        tier="B",
                        status="proposed",
                        start=w.start,
                        end=w2.end,
                        segment_id=seg_id,
                        confidence=0.68,
                        isolated=False,
                        prev_word=prev_label,
                        next_word=next_label,
                        context_note=f"Tier B context-sensitive filler ('{phrase}'); proposal-only pending grammar check",
                    )
                )
                idx += 2
                continue

        next_w = flat_words[idx + 1][1] if idx + 1 < total else None
        next_label = next_w.word.strip() if next_w else ""

        if tok1 in _TIER_A_SET:
            gap_before = w.start - prev_w.end if prev_w else w.start
            gap_after = next_w.start - w.end if next_w else 1.0
            if samples is not None:
                isolated = _check_filler_acoustic_isolation(
                    samples, sample_rate, w.start, w.end, gap_before, gap_after
                )
            else:
                isolated = gap_before >= -0.01 and gap_after >= -0.01 and (w.end - w.start) >= 0.05
            items.append(
                FillerAuditItem(
                    word=w.word.strip(),
                    normalized=tok1,
                    tier="A",
                    status="auto_cut" if isolated else "proposed",
                    start=w.start,
                    end=w.end,
                    segment_id=seg_id,
                    confidence=0.95 if isolated else 0.7,
                    isolated=isolated,
                    prev_word=prev_label,
                    next_word=next_label,
                    context_note="Pure hesitation sound (isolated)" if isolated else "Tight neighbor margins; verify before cutting",
                )
            )
        elif tok1 in _TIER_B_SET:
            note = f"Tier B context-sensitive filler ('{tok1}'); proposal-only pending grammar check"
            if tok1 in {"like", "so", "right", "well"} and prev_label.lower() in {"i", "we", "you", "they", "is", "are", "the", "a"}:
                note = f"Tier B discourse word ('{tok1}') may carry syntactic meaning; do not cut blindly"
            items.append(
                FillerAuditItem(
                    word=w.word.strip(),
                    normalized=tok1,
                    tier="B",
                    status="proposed",
                    start=w.start,
                    end=w.end,
                    segment_id=seg_id,
                    confidence=0.65,
                    isolated=False,
                    prev_word=prev_label,
                    next_word=next_label,
                    context_note=note,
                )
            )

        idx += 1

    stutters: list[dict[str, Any]] = []
    if wav_path is not None and room_tone is not None:
        stutters = audit_raw_audio_stutters(wav_path, segments, room_tone)

    return items, stutters


def detect_tiered_fillers(
    segments: list[TranscriptSegment],
    wav_path: Path | None = None,
) -> tuple[list[FillerAuditItem], list[dict[str, Any]]]:
    """Classify the 25-word Tier A/B filler list and audit raw audio for omitted stutters."""
    samples: np.ndarray | None = None
    sample_rate = 0
    room_tone: RoomToneProfile | None = None
    if wav_path is not None and Path(wav_path).exists():
        wav = Path(wav_path)
        samples, sample_rate = _load_wav_mono(wav)
        room_tone = measure_adaptive_room_tone(wav)

    return _detect_tiered_fillers_with_audio(
        segments=segments,
        samples=samples,
        sample_rate=sample_rate,
        wav_path=wav_path,
        room_tone=room_tone,
    )


def _flatten_spoken_units(bundle: TranscriptBundle) -> list[WordTiming]:
    """Return chronological word timings across segments, synthesizing from segment bounds if needed."""
    words: list[WordTiming] = []
    for seg in sorted(bundle.segments, key=lambda s: s.start):
        if seg.words:
            words.extend(sorted(seg.words, key=lambda w: w.start))
        elif seg.text.strip():
            words.append(WordTiming(word=seg.text.strip(), start=seg.start, end=seg.end))
    return sorted(words, key=lambda w: (w.start, w.end))


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Merge overlapping or contiguous intervals."""
    merged: list[tuple[float, float]] = []
    for s, e in sorted(intervals):
        if e <= s + 1e-9:
            continue
        if merged and s <= merged[-1][1] + 1e-9:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def run_scientific_sift(
    video_path: Path,
    wav_path: Path,
    bundle: TranscriptBundle,
    out_dir: Path,
    camera_path: Path | None = None,
    cursor_log: CursorEventLog | None = None,
    declared_holds: list[tuple[float, float]] | None = None,
    assemble_video: bool = True,
) -> SiftResult:
    """Execute strict 4-step Stage 1 Scientific Sifting and emit audit, OTIO, EDL, and optional rough cut."""
    video_path = Path(video_path)
    wav_path = Path(wav_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cam_resolved = Path(camera_path) if camera_path is not None else None

    # --- Step 1: sync ---
    has_audio = True
    if video_path.exists():
        meta = probe_video(video_path)
        fps = meta.fps if meta.fps > 0 else (bundle.fps or 30.0)
        width = meta.width
        height = meta.height
        video_duration = meta.duration if meta.duration > 0 else bundle.duration
        has_audio = meta.has_audio
    else:
        fps = bundle.fps if bundle.fps > 0 else 30.0
        width = bundle.width
        height = bundle.height
        video_duration = bundle.duration

    samples, sample_rate = _load_wav_mono(wav_path)
    room_tone = measure_adaptive_room_tone(wav_path)
    audio_duration = len(samples) / sample_rate if sample_rate > 0 else video_duration
    total_duration = max(0.0, video_duration if video_duration > 0 else audio_duration)

    sync_report: dict[str, Any] = {
        "step": "sync",
        "fps": fps,
        "video_duration_sec": round(video_duration, 6),
        "audio_duration_sec": round(audio_duration, 6),
        "sync_delta_sec": round(abs(video_duration - audio_duration), 6),
        "sample_rate": sample_rate,
        "has_audio_stream": has_audio,
    }

    if cam_resolved is not None and cam_resolved.exists():
        cam_meta = probe_video(cam_resolved)
        sync_report["camera_path"] = str(cam_resolved.resolve())
        sync_report["camera_fps"] = cam_meta.fps
        sync_report["camera_duration_sec"] = round(cam_meta.duration, 6)
        sync_report["camera_sync_delta_sec"] = round(abs(video_duration - cam_meta.duration), 6)

    # --- Step 2: dead_space ---
    spoken_words = _flatten_spoken_units(bundle)
    min_gap_sec = 3.0 / fps
    candidate_gaps: list[tuple[float, float, WordTiming | None, WordTiming | None]] = []

    if spoken_words:
        if spoken_words[0].start > min_gap_sec:
            candidate_gaps.append((0.0, spoken_words[0].start, None, spoken_words[0]))
        for w_prev, w_next in zip(spoken_words, spoken_words[1:]):
            if w_next.start - w_prev.end > min_gap_sec:
                candidate_gaps.append((w_prev.end, w_next.start, w_prev, w_next))
        if total_duration - spoken_words[-1].end > min_gap_sec:
            candidate_gaps.append((spoken_words[-1].end, total_duration, spoken_words[-1], None))
    else:
        for sil in bundle.silences:
            if sil.end - sil.start > min_gap_sec:
                candidate_gaps.append((sil.start, sil.end, None, None))

    gap_pairs = [(gs, ge) for gs, ge, _, _ in candidate_gaps]
    protected_holds = detect_visual_activity_holds(
        video_path=video_path if video_path.exists() else None,
        gaps=gap_pairs,
        cursor_log=cursor_log,
        declared_holds=declared_holds,
    )

    cut_items: list[CutAuditItem] = []
    auto_cut_intervals: list[tuple[float, float]] = []

    def _is_protected(gs: float, ge: float) -> ProtectedHold | None:
        for hold in protected_holds:
            if min(ge, hold.end) > max(gs, hold.start) + 1e-6:
                return hold
        return None

    for gs, ge, prev_w, next_w in candidate_gaps:
        hold = _is_protected(gs, ge)
        if hold is not None:
            s_snap = snap_to_frame(gs, fps, mode="floor")
            e_snap = min(total_duration, snap_to_frame(ge, fps, mode="ceil"))
            cut_items.append(
                CutAuditItem(
                    step="dead_space",
                    category="protected_hold",
                    status="protected",
                    start=round(s_snap, 6),
                    end=round(e_snap, 6),
                    duration=round(max(0.0, e_snap - s_snap), 6),
                    confidence=1.0,
                    reason=hold.reason,
                    prev_word=prev_w.word.strip() if prev_w else "",
                    next_word=next_w.word.strip() if next_w else "",
                )
            )
            continue

        tail_extended = False
        safety_frames = 0
        if prev_w is not None:
            cut_out, cut_in, tail_extended, safety_frames = _protect_consonant_tail_detail(
                samples=samples,
                sample_rate=sample_rate,
                word=prev_w,
                next_word=next_w,
                room_tone_dbfs=room_tone.room_tone_dbfs,
                fps=fps,
            )
            if not tail_extended:
                # Preserve 1 frame breathing room after non-consonant-tail words too.
                cut_out = min(cut_in, snap_to_frame(prev_w.end + 1.0 / fps, fps, mode="ceil"))
        else:
            cut_out = 0.0
            if next_w is not None:
                cut_in = snap_to_frame(max(0.0, next_w.start - 1.0 / fps), fps, mode="floor")
            else:
                cut_in = snap_to_frame(ge, fps, mode="floor")

        cut_in = min(total_duration, cut_in)
        if cut_in - cut_out > 2.0 / fps:
            auto_cut_intervals.append((cut_out, cut_in))
            cut_items.append(
                CutAuditItem(
                    step="dead_space",
                    category="dead_space",
                    status="auto_cut",
                    start=round(cut_out, 6),
                    end=round(cut_in, 6),
                    duration=round(cut_in - cut_out, 6),
                    confidence=0.95,
                    reason="Dead Space exceeding breathing room above Room Tone",
                    prev_word=prev_w.word.strip() if prev_w else "",
                    next_word=next_w.word.strip() if next_w else "",
                    consonant_tail_extended=tail_extended,
                    safety_frames_added=safety_frames,
                )
            )

    # --- Step 3: retakes_and_mistakes ---
    retake_items = classify_retakes(bundle.segments)
    for item in retake_items:
        s_snap = snap_to_frame(max(0.0, item.start), fps, mode="floor")
        e_snap = min(total_duration, snap_to_frame(min(total_duration, item.end), fps, mode="ceil"))
        if e_snap > s_snap and item.status == "auto_cut":
            auto_cut_intervals.append((s_snap, e_snap))
        cut_items.append(
            CutAuditItem(
                step="retakes_and_mistakes",
                category=item.category,
                status=item.status,
                start=round(s_snap, 6),
                end=round(e_snap, 6),
                duration=round(max(0.0, e_snap - s_snap), 6),
                confidence=item.confidence,
                reason=item.reason,
                prev_word=item.prev_context,
                next_word=item.next_context,
            )
        )

    # --- Step 4: filler_words ---
    filler_items, untranscribed_stutters = _detect_tiered_fillers_with_audio(
        segments=bundle.segments,
        samples=samples,
        sample_rate=sample_rate,
        wav_path=wav_path,
        room_tone=room_tone,
    )
    for f_item in filler_items:
        s_snap = snap_to_frame(max(0.0, f_item.start), fps, mode="floor")
        e_snap = min(total_duration, snap_to_frame(min(total_duration, f_item.end), fps, mode="ceil"))
        if e_snap > s_snap and f_item.status == "auto_cut":
            auto_cut_intervals.append((s_snap, e_snap))
        cut_items.append(
            CutAuditItem(
                step="filler_words",
                category=f"tier_{f_item.tier}_filler",
                status=f_item.status,
                start=round(s_snap, 6),
                end=round(e_snap, 6),
                duration=round(max(0.0, e_snap - s_snap), 6),
                confidence=f_item.confidence,
                reason=f_item.context_note,
                prev_word=f_item.prev_word,
                next_word=f_item.next_word,
            )
        )

    for stutter in untranscribed_stutters:
        s_snap = snap_to_frame(max(0.0, float(stutter["start"])), fps, mode="floor")
        e_snap = min(total_duration, snap_to_frame(min(total_duration, float(stutter["end"])), fps, mode="ceil"))
        cut_items.append(
            CutAuditItem(
                step="filler_words",
                category="untranscribed_stutter",
                status="proposed",
                start=round(s_snap, 6),
                end=round(e_snap, 6),
                duration=round(max(0.0, e_snap - s_snap), 6),
                confidence=0.75,
                reason="Short un-transcribed acoustic burst detected against raw waveform",
            )
        )

    # Merge overlapping auto-cut intervals so seconds are never double-counted.
    merged_cuts = _merge_intervals(
        [(max(0.0, s), min(total_duration, e)) for s, e in auto_cut_intervals]
    )

    min_keep_sec = max(0.15, 3.0 / fps)
    kept_ranges: list[tuple[float, float]] = []
    cursor = 0.0
    for cs, ce in merged_cuts:
        if cs - cursor >= min_keep_sec:
            kept_ranges.append((cursor, cs))
        cursor = max(cursor, ce)
    if total_duration - cursor >= min_keep_sec:
        kept_ranges.append((cursor, total_duration))

    # Fallback: if aggressive auto-cuts consumed everything, keep final segment/full span safely.
    if not kept_ranges and total_duration > 0:
        kept_ranges = [(0.0, total_duration)]

    # Recompute effective cuts from final kept_ranges so kept + removed == total_duration exactly.
    effective_cuts: list[tuple[float, float]] = []
    pos = 0.0
    for ks, ke in kept_ranges:
        if ks > pos + 1e-9:
            effective_cuts.append((pos, ks))
        pos = ke
    if total_duration > pos + 1e-9:
        effective_cuts.append((pos, total_duration))

    kept_segments = [
        KeepSegment(
            id=f"seg_{idx + 1:02d}",
            start=round(ks, 6),
            end=round(ke, 6),
            reason="sifted_keep",
        )
        for idx, (ks, ke) in enumerate(kept_ranges)
    ]

    duration_after = round(sum(seg.end - seg.start for seg in kept_segments), 6)
    unique_removed_seconds = round(sum(ce - cs for cs, ce in effective_cuts), 6)

    edl = EditDecisionList(
        source_path=str(video_path.resolve()),
        camera_path=str(cam_resolved.resolve()) if cam_resolved is not None else None,
        fps=round(fps, 3),
        width=width,
        height=height,
        kept_segments=kept_segments,
        graphic_cues=[],
        captions_enabled=True,
        summary=(
            f"Scientific sift ({' -> '.join(SIFT_STEPS_ORDER)}): "
            f"{len(kept_segments)} kept segments, {unique_removed_seconds:.2f}s unique removed."
        ),
    )

    edl_path = out_dir / "edl.json"
    edl_path.write_text(edl.model_dump_json(indent=2), encoding="utf-8")

    otio_timeline = edl_to_otio(edl)
    otio_path = save_otio(otio_timeline, out_dir / "rough_cut.otio")

    rough_cut_video_path: str | None = None
    rough_camera_video_path: str | None = None
    timeline_manifest_path: str | None = None

    if assemble_video:
        rough_mp4 = assemble_rough_cut(
            source_path=video_path,
            edl=edl,
            output_video=out_dir / "rough_cut.mp4",
            has_audio=has_audio,
        )
        rough_cut_video_path = str(rough_mp4)

        cam_file_for_manifest: str | None = None
        if cam_resolved is not None and cam_resolved.exists():
            cam_edl = edl.model_copy(update={"source_path": str(cam_resolved.resolve())})
            rough_cam_mp4 = assemble_rough_cut(
                source_path=cam_resolved,
                edl=cam_edl,
                output_video=out_dir / "rough_camera.mp4",
                has_audio=False,
                normalize_audio=False,
            )
            rough_camera_video_path = str(rough_cam_mp4)
            cam_file_for_manifest = rough_cam_mp4.name

        manifest = remap_timeline(
            bundle=bundle,
            edl=edl,
            video_file=rough_mp4.name,
            camera_file=cam_file_for_manifest,
        )
        manifest_path = out_dir / "timeline_manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        timeline_manifest_path = str(manifest_path)

    cut_audit_path = out_dir / "cut_audit.json"
    result = SiftResult(
        source_path=str(video_path.resolve()),
        camera_path=str(cam_resolved.resolve()) if cam_resolved is not None else None,
        wav_path=str(wav_path.resolve()),
        fps=round(fps, 3),
        steps_executed=list(SIFT_STEPS_ORDER),
        sync_report=sync_report,
        room_tone=room_tone,
        duration_before=round(total_duration, 6),
        duration_after=duration_after,
        unique_removed_seconds=unique_removed_seconds,
        protected_holds=protected_holds,
        retake_items=retake_items,
        filler_items=filler_items,
        untranscribed_stutters=untranscribed_stutters,
        cut_items=cut_items,
        kept_segments=kept_segments,
        edl_path=str(edl_path),
        otio_path=str(otio_path),
        cut_audit_path=str(cut_audit_path),
        rough_cut_video_path=rough_cut_video_path,
        rough_camera_video_path=rough_camera_video_path,
        timeline_manifest_path=timeline_manifest_path,
    )
    cut_audit_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result
