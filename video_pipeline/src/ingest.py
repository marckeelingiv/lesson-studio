"""Media probing and 16 kHz mono WAV extraction via ffprobe/ffmpeg."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from schema import VideoMetadata


def _parse_fps(rate_str: str) -> float:
    """Parse ffprobe r_frame_rate strings like '30000/1001' or '30/1'."""
    if "/" in rate_str:
        num, den = rate_str.split("/", 1)
        den_val = float(den)
        return float(num) / den_val if den_val else 30.0
    return float(rate_str) if rate_str else 30.0


def probe_video(video_path: Path) -> VideoMetadata:
    """Extract resolution, FPS, duration, and audio presence using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(res.stdout)

    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream is None:
        raise ValueError(f"No video stream found in {video_path}")

    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    duration = float(data.get("format", {}).get("duration") or video_stream.get("duration") or 0.0)
    fps = _parse_fps(video_stream.get("r_frame_rate", "30/1"))

    return VideoMetadata(
        source_path=str(video_path.resolve()),
        duration=duration,
        fps=round(fps, 3),
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
        has_audio=has_audio,
    )


def extract_audio(video_path: Path, wav_path: Path) -> Path:
    """Extract 16 kHz mono PCM WAV for Whisper transcription and silence detection."""
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return wav_path
