"""Picture-Lock-guarded audio mixing, music ducking, SFX layering, and SRT export (Rule 03)."""

from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:
    from .qc import GateResult, check_loudness
    from .schema import RemappedWord
except ImportError:
    from qc import GateResult, check_loudness
    from schema import RemappedWord


FORBIDDEN_SFX_TRIGGERS: frozenset[str] = frozenset({"hard_cut", "panel_cut", "dense_narration"})
MIN_SFX_SPACING_SEC: float = 2.0
MAX_SFX_GAIN_DB: float = -12.0
_SENTENCE_ENDINGS = (".", "?", "!")


class PictureLockRequiredError(RuntimeError):
    """Raised when audio mixing is attempted prior to Stage 3 Picture Lock confirmation."""


class AudioSfxCue(BaseModel):
    """Single rule-governed sound effect placement locked to timeline time."""

    path: Path
    start_sec: float
    trigger_type: str
    gain_db: float = -14.0
    reason: str


class AudioMixConfig(BaseModel):
    """Delivery audio mix parameters conforming to Rule 03."""

    target_lufs: float = -14.0
    true_peak_dbtp: float = -1.0
    sample_rate: int = 48000
    sound_design_level: int = 1
    min_sfx_spacing_sec: float = MIN_SFX_SPACING_SEC
    max_sfx_gain_db: float = MAX_SFX_GAIN_DB


class AudioMixResult(BaseModel):
    """Outputs and verified loudness metrics produced by mix_locked_audio."""

    picture_locked: bool
    dialogue_only_path: Path
    final_mixed_path: Path
    music_path: Path | None = None
    music_ducked: bool = False
    ducking_method: str = "none"
    applied_sfx_cues: list[AudioSfxCue] = Field(default_factory=list)
    measured_lufs: float
    measured_true_peak_dbtp: float
    loudness_gate: GateResult


def _probe_media(video_path: Path) -> tuple[float, bool]:
    res = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(res.stdout)
    streams = data.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if v_stream is None:
        raise ValueError(f"No video stream found in {video_path}")
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    duration = float(data.get("format", {}).get("duration") or v_stream.get("duration") or 0.0)
    return duration, has_audio


def validate_sfx_cues(
    sfx_cues: list[AudioSfxCue],
    min_spacing_sec: float = MIN_SFX_SPACING_SEC,
    max_gain_db: float = MAX_SFX_GAIN_DB,
) -> list[AudioSfxCue]:
    """Validate Rule 03 §4 SFX trigger, spacing (>= 2.0s), and gain (<= -12.0 dB) constraints."""
    ordered = sorted(sfx_cues, key=lambda c: c.start_sec)
    for idx, cue in enumerate(ordered):
        if cue.start_sec < 0.0:
            raise ValueError(f"SFX cue[{idx}] has negative start_sec: {cue.start_sec}.")
        if not cue.reason.strip():
            raise ValueError(f"SFX cue[{idx}] at {cue.start_sec:.2f}s must specify a non-empty reason.")
        trig = cue.trigger_type.strip().lower()
        if not trig or trig in FORBIDDEN_SFX_TRIGGERS:
            raise ValueError(
                f"SFX cue[{idx}] has disallowed trigger_type '{cue.trigger_type}' per Rule 03."
            )
        if cue.gain_db > max_gain_db:
            raise ValueError(
                f"SFX cue[{idx}] gain_db={cue.gain_db:.1f} dB exceeds max {max_gain_db:.1f} dB below voiceover."
            )
        if not cue.path.exists() or not cue.path.is_file():
            raise FileNotFoundError(f"SFX cue[{idx}] audio file not found: {cue.path}")
        if idx > 0:
            gap = cue.start_sec - ordered[idx - 1].start_sec
            if gap < min_spacing_sec - 1e-6:
                raise ValueError(
                    f"SFX cues at {ordered[idx - 1].start_sec:.2f}s and {cue.start_sec:.2f}s "
                    f"are {gap:.2f}s apart (< {min_spacing_sec:.1f}s minimum spacing)."
                )
    return ordered


def _parse_loudnorm_json(stderr: str) -> dict[str, Any] | None:
    matches = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr, flags=re.DOTALL)
    if not matches:
        return None
    try:
        return json.loads(matches[-1])
    except json.JSONDecodeError:
        return None


def _is_finite_loudnorm_stats(stats: dict[str, Any] | None) -> bool:
    if not stats:
        return False
    for key in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"):
        try:
            val = float(stats[key])
        except (KeyError, TypeError, ValueError):
            return False
        if not math.isfinite(val):
            return False
    return True


def _two_pass_loudnorm_to_wav(
    input_wav: Path,
    output_wav: Path,
    target_lufs: float,
    true_peak_dbtp: float,
    sample_rate: int = 48000,
) -> None:
    """Apply two-pass linear EBU R128 loudnorm onto a stereo 48 kHz WAV."""
    base_filter = f"loudnorm=I={target_lufs:.2f}:TP={true_peak_dbtp:.2f}:LRA=11"
    pass1 = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "info",
            "-i",
            str(input_wav),
            "-af",
            f"{base_filter}:print_format=json",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    stats = _parse_loudnorm_json(pass1.stderr)
    if _is_finite_loudnorm_stats(stats):
        assert stats is not None
        ln_filter = (
            f"{base_filter}"
            f":measured_I={float(stats['input_i']):.2f}"
            f":measured_TP={float(stats['input_tp']):.2f}"
            f":measured_LRA={float(stats['input_lra']):.2f}"
            f":measured_thresh={float(stats['input_thresh']):.2f}"
            f":offset={float(stats['target_offset']):.2f}"
            f":linear=true,aresample={sample_rate}"
        )
    else:
        ln_filter = f"{base_filter},aresample={sample_rate}"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(input_wav),
            "-af",
            ln_filter,
            "-acodec",
            "pcm_s24le",
            "-ar",
            str(sample_rate),
            "-ac",
            "2",
            str(output_wav),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _music_bed_params(sound_design_level: int) -> tuple[float, float]:
    """Return (music_base_db, sidechain_ratio) scaled by Creative Brief sound_design dial (1..5)."""
    table = {
        1: (-26.0, 8.0),
        2: (-22.0, 6.0),
        3: (-18.0, 4.0),
        4: (-15.0, 3.0),
        5: (-13.0, 2.5),
    }
    return table.get(sound_design_level, (-26.0, 8.0))


def _render_mixed_raw_wav(
    dialogue_wav: Path,
    duration_sec: float,
    out_raw_wav: Path,
    music_path: Path | None,
    sfx_cues: list[AudioSfxCue],
    sound_design_level: int,
    sample_rate: int,
    use_sidechain: bool,
) -> str:
    """Mix dialogue + optional ducked music + delayed SFX into an un-normalized 48 kHz WAV."""
    cmd: list[str] = ["ffmpeg", "-y", "-v", "error", "-i", str(dialogue_wav)]
    filter_parts: list[str] = [
        f"[0:a]aformat=sample_fmts=fltp:sample_rates={sample_rate}:channel_layouts=stereo[dlg_in]"
    ]

    active_music = music_path is not None and sound_design_level > 0
    input_idx = 1
    mix_labels: list[str] = []
    ducking_method = "none"

    if active_music:
        assert music_path is not None
        cmd.extend(["-stream_loop", "-1", "-i", str(music_path)])
        mus_idx = input_idx
        input_idx += 1
        music_db, ratio = _music_bed_params(sound_design_level)
        trim_dur = max(0.1, duration_sec)
        filter_parts.append(
            f"[{mus_idx}:a]aformat=sample_fmts=fltp:sample_rates={sample_rate}:channel_layouts=stereo,"
            f"atrim=0:{trim_dur:.4f},asetpts=PTS-STARTPTS,volume={music_db:.1f}dB[mus_lvl]"
        )
        if use_sidechain:
            filter_parts.append("[dlg_in]asplit=2[dlg_mix][dlg_sc]")
            filter_parts.append(
                f"[mus_lvl][dlg_sc]sidechaincompress=threshold=0.02:ratio={ratio:.1f}:attack=20:release=350[mus_ducked]"
            )
            mix_labels.extend(["[dlg_mix]", "[mus_ducked]"])
            ducking_method = "sidechaincompress"
        else:
            filter_parts.append("[mus_lvl]volume=-10.0dB[mus_ducked]")
            mix_labels.extend(["[dlg_in]", "[mus_ducked]"])
            ducking_method = "attenuation_fallback"
    else:
        mix_labels.append("[dlg_in]")

    for idx, cue in enumerate(sfx_cues):
        cmd.extend(["-i", str(cue.path)])
        sfx_idx = input_idx
        input_idx += 1
        delay_ms = max(0, int(round(cue.start_sec * 1000.0)))
        delay_filter = f"adelay={delay_ms}:all=1," if delay_ms > 0 else ""
        filter_parts.append(
            f"[{sfx_idx}:a]aformat=sample_fmts=fltp:sample_rates={sample_rate}:channel_layouts=stereo,"
            f"{delay_filter}volume={cue.gain_db:.2f}dB[sfx_{idx}]"
        )
        mix_labels.append(f"[sfx_{idx}]")

    if len(mix_labels) == 1:
        filter_parts.append(f"{mix_labels[0]}anull[mixed]")
    else:
        filter_parts.append(
            f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=first:dropout_transition=0:normalize=0[mixed]"
        )

    cmd.extend(
        [
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            "[mixed]",
            "-acodec",
            "pcm_s24le",
            "-ar",
            str(sample_rate),
            "-ac",
            "2",
            str(out_raw_wav),
        ]
    )
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return ducking_method


def _mux_video_with_audio(video_path: Path, audio_wav: Path, out_mp4: Path, sample_rate: int) -> Path:
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(video_path),
            "-i",
            str(audio_wav),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            str(sample_rate),
            "-shortest",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return out_mp4


def mix_locked_audio(
    video_path: Path,
    out_dir: Path,
    picture_locked: bool,
    music_path: Path | None = None,
    sfx_cues: list[AudioSfxCue] | None = None,
    target_lufs: float = -14.0,
    true_peak_dbtp: float = -1.0,
    sound_design_level: int = 1,
) -> AudioMixResult:
    """Layer ducked music and rule-governed SFX after Picture Lock, emitting dialogue_only.mp4 + final_mixed.mp4."""
    if not picture_locked:
        raise PictureLockRequiredError(
            "Audio mixing refused: Picture Lock must be confirmed (picture_locked=True) at Stage 3 first."
        )
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not (0 <= sound_design_level <= 5):
        raise ValueError(f"sound_design_level must be between 0 and 5, got {sound_design_level}.")
    if music_path is not None and not music_path.exists():
        raise FileNotFoundError(f"Music file not found: {music_path}")

    cfg = AudioMixConfig(
        target_lufs=target_lufs,
        true_peak_dbtp=true_peak_dbtp,
        sound_design_level=sound_design_level,
    )
    validated_sfx = validate_sfx_cues(
        sfx_cues or [],
        min_spacing_sec=cfg.min_sfx_spacing_sec,
        max_gain_db=cfg.max_sfx_gain_db,
    )

    duration_sec, has_audio = _probe_media(video_path)
    if not has_audio:
        raise ValueError(f"Input video {video_path} has no dialogue audio stream to mix.")

    out_dir.mkdir(parents=True, exist_ok=True)
    dialogue_only_path = out_dir / "dialogue_only.mp4"
    final_mixed_path = out_dir / "final_mixed.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        raw_dlg_wav = tmp_dir / "raw_dialogue.wav"
        norm_dlg_wav = tmp_dir / "norm_dialogue.wav"
        raw_mix_wav = tmp_dir / "raw_mix.wav"
        norm_mix_wav = tmp_dir / "norm_mix.wav"

        # Extract base dialogue as 48 kHz stereo PCM
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(video_path),
                "-vn",
                "-acodec",
                "pcm_s24le",
                "-ar",
                str(cfg.sample_rate),
                "-ac",
                "2",
                str(raw_dlg_wav),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        # Normalize dialogue stem to target_lufs / true_peak_dbtp
        _two_pass_loudnorm_to_wav(
            raw_dlg_wav,
            norm_dlg_wav,
            target_lufs=cfg.target_lufs,
            true_peak_dbtp=cfg.true_peak_dbtp,
            sample_rate=cfg.sample_rate,
        )
        _mux_video_with_audio(video_path, norm_dlg_wav, dialogue_only_path, sample_rate=cfg.sample_rate)

        ducking_method = "none"
        has_active_layers = (music_path is not None and cfg.sound_design_level > 0) or bool(validated_sfx)
        if not has_active_layers:
            _mux_video_with_audio(video_path, norm_dlg_wav, final_mixed_path, sample_rate=cfg.sample_rate)
        else:
            try:
                ducking_method = _render_mixed_raw_wav(
                    dialogue_wav=norm_dlg_wav,
                    duration_sec=duration_sec,
                    out_raw_wav=raw_mix_wav,
                    music_path=music_path,
                    sfx_cues=validated_sfx,
                    sound_design_level=cfg.sound_design_level,
                    sample_rate=cfg.sample_rate,
                    use_sidechain=True,
                )
            except subprocess.CalledProcessError:
                ducking_method = _render_mixed_raw_wav(
                    dialogue_wav=norm_dlg_wav,
                    duration_sec=duration_sec,
                    out_raw_wav=raw_mix_wav,
                    music_path=music_path,
                    sfx_cues=validated_sfx,
                    sound_design_level=cfg.sound_design_level,
                    sample_rate=cfg.sample_rate,
                    use_sidechain=False,
                )

            _two_pass_loudnorm_to_wav(
                raw_mix_wav,
                norm_mix_wav,
                target_lufs=cfg.target_lufs,
                true_peak_dbtp=cfg.true_peak_dbtp,
                sample_rate=cfg.sample_rate,
            )
            _mux_video_with_audio(video_path, norm_mix_wav, final_mixed_path, sample_rate=cfg.sample_rate)

    loudness_gate = check_loudness(
        final_mixed_path,
        target_lufs=cfg.target_lufs,
        max_true_peak=cfg.true_peak_dbtp,
    )
    measured_lufs = float(loudness_gate.metrics.get("integrated_lufs") or 0.0)
    measured_tp = float(loudness_gate.metrics.get("true_peak_dbtp") or 0.0)
    if not loudness_gate.passed:
        raise RuntimeError(
            f"Final mix failed loudness verification ({measured_lufs:.2f} LUFS, "
            f"{measured_tp:.2f} dBTP): {loudness_gate.summary}"
        )

    return AudioMixResult(
        picture_locked=picture_locked,
        dialogue_only_path=dialogue_only_path,
        final_mixed_path=final_mixed_path,
        music_path=music_path,
        music_ducked=ducking_method != "none",
        ducking_method=ducking_method,
        applied_sfx_cues=validated_sfx,
        measured_lufs=measured_lufs,
        measured_true_peak_dbtp=measured_tp,
        loudness_gate=loudness_gate,
    )


def _format_srt_timestamp(ms: int) -> str:
    ms = max(0, int(ms))
    hours = ms // 3_600_000
    minutes = (ms % 3_600_000) // 60_000
    seconds = (ms % 60_000) // 1_000
    rem_ms = ms % 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{rem_ms:03d}"


def _wrap_cue_lines(words_text: list[str], max_chars_per_line: int) -> list[str] | None:
    """Wrap words into at most 2 lines each <= max_chars_per_line; return None if impossible."""
    lines: list[str] = []
    cur = ""
    for token in words_text:
        if len(token) > max_chars_per_line:
            return None
        candidate = token if not cur else f"{cur} {token}"
        if len(candidate) <= max_chars_per_line:
            cur = candidate
        else:
            lines.append(cur)
            cur = token
            if len(lines) >= 2:
                return None
    if cur:
        lines.append(cur)
    return lines if len(lines) <= 2 else None


def export_srt(
    captions: list[RemappedWord],
    out_srt: Path,
    max_words_per_cue: int = 6,
    max_chars_per_line: int = 42,
) -> Path:
    """Format RemappedWord captions into clean zero-based, non-overlapping SRT blocks."""
    cleaned = [
        RemappedWord(text=w.text.strip(), startMs=max(0, w.startMs), endMs=max(0, w.endMs))
        for w in captions
        if w.text.strip()
    ]
    cleaned.sort(key=lambda w: (w.startMs, w.endMs))

    cues: list[tuple[int, int, list[str]]] = []
    bucket: list[RemappedWord] = []

    def _flush_bucket(items: list[RemappedWord]) -> None:
        if not items:
            return
        words_text = [w.text for w in items]
        lines = _wrap_cue_lines(words_text, max_chars_per_line)
        if lines is None:
            # Handle oversized single token gracefully by truncating/splitting to max_chars_per_line
            joined = " ".join(words_text)
            lines = [joined[i : i + max_chars_per_line] for i in range(0, len(joined), max_chars_per_line)][:2]
        start_ms = max(0, items[0].startMs)
        end_ms = max(start_ms + 1, items[-1].endMs)
        if cues:
            prev_s, prev_e, prev_lines = cues[-1]
            if start_ms < prev_e:
                if prev_e < end_ms:
                    start_ms = prev_e
                else:
                    # Clamp prior end if tightly packed within millisecond rounding
                    new_prev_e = max(prev_s + 1, start_ms)
                    cues[-1] = (prev_s, new_prev_e, prev_lines)
                    start_ms = new_prev_e
                    end_ms = max(start_ms + 50, end_ms)
        cues.append((start_ms, end_ms, lines))

    for word in cleaned:
        candidate_texts = [w.text for w in bucket] + [word.text]
        can_fit = (
            len(candidate_texts) <= max_words_per_cue
            and _wrap_cue_lines(candidate_texts, max_chars_per_line) is not None
        )
        if bucket and not can_fit:
            _flush_bucket(bucket)
            bucket = [word]
        else:
            bucket.append(word)

        if bucket and bucket[-1].text.endswith(_SENTENCE_ENDINGS) and len(bucket) >= 2:
            _flush_bucket(bucket)
            bucket = []

    _flush_bucket(bucket)

    out_srt.parent.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    for idx, (start_ms, end_ms, lines) in enumerate(cues, start=1):
        ts_line = f"{_format_srt_timestamp(start_ms)} --> {_format_srt_timestamp(end_ms)}"
        blocks.append("\n".join([str(idx), ts_line, *lines]))

    out_srt.write_text("\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")
    return out_srt
