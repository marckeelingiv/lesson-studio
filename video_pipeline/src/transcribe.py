"""Word-level transcription (faster-whisper) and silence, filler, and retake detection."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from schema import (
    FillerCandidate,
    RetakeCandidate,
    SilenceRegion,
    TranscriptBundle,
    TranscriptSegment,
    VideoMetadata,
    WordTiming,
)

FILLER_WORDS = frozenset({"um", "uh", "uhh", "umm", "er", "erm", "ah", "hmm"})
SPOKEN_RETAKE_PHRASES: tuple[tuple[str, ...], ...] = (
    ("retake",),
    ("scratch", "that"),
    ("take", "two"),
    ("start", "over"),
    ("let", "me", "restart"),
    ("cut", "cut"),
)
_SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)")
_PUNCT_RE = re.compile(r"[^\w\s']")


def _normalize_text(text: str) -> list[str]:
    return _PUNCT_RE.sub("", text.lower()).split()


def _contains_retake_phrase(tokens: list[str]) -> str | None:
    """Return matched spoken retake marker phrase if present in normalized tokens."""
    for phrase in SPOKEN_RETAKE_PHRASES:
        size = len(phrase)
        for i in range(len(tokens) - size + 1):
            if tuple(tokens[i : i + size]) == phrase:
                return " ".join(phrase)
    return None


def detect_silences(
    wav_path: Path,
    noise_db: float = -35.0,
    min_duration: float = 0.6,
) -> list[SilenceRegion]:
    """Run ffmpeg silencedetect filter on WAV audio and return silence intervals."""
    cmd = [
        "ffmpeg",
        "-i",
        str(wav_path),
        "-af",
        f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f",
        "null",
        "-",
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)

    silences: list[SilenceRegion] = []
    pending_start: float | None = None
    for line in res.stderr.splitlines():
        if m_start := _SILENCE_START_RE.search(line):
            pending_start = float(m_start.group(1))
        elif m_end := _SILENCE_END_RE.search(line):
            end = float(m_end.group(1))
            dur = float(m_end.group(2))
            start = pending_start if pending_start is not None else max(0.0, end - dur)
            silences.append(SilenceRegion(start=round(start, 3), end=round(end, 3), duration=round(dur, 3)))
            pending_start = None
    return silences


def detect_fillers(segments: list[TranscriptSegment]) -> list[FillerCandidate]:
    """Identify filler words from word-level transcript timings."""
    fillers: list[FillerCandidate] = []
    for seg in segments:
        for w in seg.words:
            clean = _PUNCT_RE.sub("", w.word.strip().lower())
            if clean in FILLER_WORDS:
                fillers.append(
                    FillerCandidate(
                        word=w.word.strip(),
                        start=w.start,
                        end=w.end,
                        segment_id=seg.id,
                    )
                )
    return fillers


def detect_retakes(segments: list[TranscriptSegment]) -> list[RetakeCandidate]:
    """Flag spoken retake markers, pause-bounded restarts, and overlapping false starts."""
    candidates: dict[int, RetakeCandidate] = {}

    def _add(seg: TranscriptSegment, reason: str) -> None:
        if seg.id not in candidates:
            candidates[seg.id] = RetakeCandidate(
                segment_id=seg.id,
                reason=reason,
                start=seg.start,
                end=seg.end,
                text=seg.text,
            )

    tokenized = [_normalize_text(seg.text) for seg in segments]

    for idx, curr in enumerate(segments):
        curr_tokens = tokenized[idx]
        if not curr_tokens:
            continue

        phrase = _contains_retake_phrase(curr_tokens)
        if phrase is not None:
            if len(curr_tokens) <= 3 and idx > 0:
                _add(segments[idx - 1], f"precedes spoken retake marker ('{phrase}')")
            _add(curr, f"spoken retake marker ('{phrase}')")
            continue

        if idx + 1 >= len(segments):
            continue

        nxt = segments[idx + 1]
        nxt_tokens = tokenized[idx + 1]
        if not nxt_tokens:
            continue

        # Short aborted sentence followed by a longer restart with shared prefix
        prefix_len = 0
        for a, b in zip(curr_tokens, nxt_tokens):
            if a == b:
                prefix_len += 1
            else:
                break

        overlap_ratio = len(set(curr_tokens) & set(nxt_tokens)) / max(1, len(set(curr_tokens)))
        pause_sec = nxt.start - curr.end
        if (
            (prefix_len >= 2 and len(curr_tokens) <= len(nxt_tokens))
            or overlap_ratio >= 0.75
            or (prefix_len >= 1 and len(curr_tokens) <= 5 and pause_sec >= 1.0)
        ):
            _add(
                curr,
                f"overlaps next segment ({prefix_len}-word prefix, {overlap_ratio:.0%} tokens, {pause_sec:.1f}s gap)",
            )

    return [candidates[seg.id] for seg in segments if seg.id in candidates]


def transcribe_audio(
    wav_path: Path,
    model_size: str = "base",
    device: str = "auto",
    compute_type: str = "auto",
) -> tuple[str, list[TranscriptSegment]]:
    """Transcribe WAV audio with word-level timestamps using faster-whisper."""
    from faster_whisper import WhisperModel

    resolved_device = device
    resolved_compute = compute_type
    if resolved_device == "auto":
        try:
            import ctranslate2

            resolved_device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            resolved_device = "cpu"
    if resolved_compute == "auto":
        resolved_compute = "float16" if resolved_device == "cuda" else "int8"

    model = WhisperModel(model_size, device=resolved_device, compute_type=resolved_compute)
    raw_segments, info = model.transcribe(str(wav_path), word_timestamps=True, vad_filter=True)

    segments: list[TranscriptSegment] = []
    for idx, seg in enumerate(raw_segments):
        words = [
            WordTiming(
                word=w.word,
                start=round(float(w.start), 3),
                end=round(float(w.end), 3),
                probability=round(float(w.probability), 3),
            )
            for w in (seg.words or [])
        ]
        segments.append(
            TranscriptSegment(
                id=idx,
                start=round(float(seg.start), 3),
                end=round(float(seg.end), 3),
                text=seg.text.strip(),
                words=words,
            )
        )
    return info.language, segments


def build_transcript_bundle(
    meta: VideoMetadata,
    wav_path: Path,
    model_size: str = "base",
    device: str = "auto",
    noise_db: float = -35.0,
    min_silence_sec: float = 0.6,
) -> TranscriptBundle:
    """Run transcription plus silence, filler, and retake detection."""
    language, segments = transcribe_audio(wav_path, model_size=model_size, device=device)
    silences = detect_silences(wav_path, noise_db=noise_db, min_duration=min_silence_sec)
    fillers = detect_fillers(segments)
    retakes = detect_retakes(segments)

    return TranscriptBundle(
        source_path=meta.source_path,
        duration=meta.duration,
        fps=meta.fps,
        width=meta.width,
        height=meta.height,
        language=language,
        segments=segments,
        silences=silences,
        fillers=fillers,
        retakes=retakes,
    )
