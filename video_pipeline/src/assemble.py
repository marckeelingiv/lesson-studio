"""FFmpeg rough-cut assembly and timeline timestamp remapping."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from schema import (
    EditDecisionList,
    RemappedWord,
    TimelineManifest,
    TranscriptBundle,
)


def assemble_rough_cut(
    source_path: Path,
    edl: EditDecisionList,
    output_video: Path,
    has_audio: bool = True,
    normalize_audio: bool = True,
    audio_fade_sec: float = 0.02,
) -> Path:
    """Trim and concatenate kept segments into a single normalized rough-cut MP4."""
    if not edl.kept_segments:
        raise ValueError("EDL contains no kept_segments to assemble.")

    output_video.parent.mkdir(parents=True, exist_ok=True)

    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    for idx, seg in enumerate(edl.kept_segments):
        filter_parts.append(
            f"[0:v]trim=start={seg.start}:end={seg.end},setpts=PTS-STARTPTS[v{idx}]"
        )
        if has_audio:
            seg_dur = max(0.05, seg.end - seg.start)
            fade_d = min(audio_fade_sec, seg_dur / 4.0)
            if fade_d > 0.002:
                filter_parts.append(
                    f"[0:a]atrim=start={seg.start}:end={seg.end},asetpts=PTS-STARTPTS,"
                    f"afade=t=in:st=0:d={fade_d:.4f},"
                    f"afade=t=out:st={max(0.0, seg_dur - fade_d):.4f}:d={fade_d:.4f}[a{idx}]"
                )
            else:
                filter_parts.append(
                    f"[0:a]atrim=start={seg.start}:end={seg.end},asetpts=PTS-STARTPTS[a{idx}]"
                )
            concat_inputs.append(f"[v{idx}][a{idx}]")
        else:
            concat_inputs.append(f"[v{idx}]")

    n = len(edl.kept_segments)
    if has_audio:
        if normalize_audio:
            filter_parts.append(
                f"{''.join(concat_inputs)}concat=n={n}:v=1:a=1[outv][raw_a];"
                "[raw_a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[outa]"
            )
        else:
            filter_parts.append(f"{''.join(concat_inputs)}concat=n={n}:v=1:a=1[outv][outa]")
        maps = ["-map", "[outv]", "-map", "[outa]"]
    else:
        filter_parts.append(f"{''.join(concat_inputs)}concat=n={n}:v=1:a=0[outv]")
        maps = ["-map", "[outv]"]

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-filter_complex",
        ";".join(filter_parts),
        *maps,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
    ]
    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
    cmd.append(str(output_video))

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_video


def remap_timeline(
    bundle: TranscriptBundle,
    edl: EditDecisionList,
    video_file: str,
    camera_file: str | None = None,
) -> TimelineManifest:
    """Map source word timings onto the concatenated rough-cut timeline."""
    captions: list[RemappedWord] = []
    timeline_offset = 0.0

    for seg in edl.kept_segments:
        seg_dur = seg.end - seg.start
        for t_seg in bundle.segments:
            for word in t_seg.words:
                # Include words whose midpoint falls inside this kept segment
                midpoint = (word.start + word.end) / 2.0
                if seg.start <= midpoint <= seg.end:
                    rel_start = max(0.0, word.start - seg.start) + timeline_offset
                    rel_end = min(seg_dur, word.end - seg.start) + timeline_offset
                    if rel_end <= rel_start:
                        rel_end = rel_start + 0.05
                    captions.append(
                        RemappedWord(
                            text=word.word,
                            startMs=int(round(rel_start * 1000)),
                            endMs=int(round(rel_end * 1000)),
                        )
                    )
        timeline_offset += seg_dur

    duration_in_frames = max(1, int(round(timeline_offset * edl.fps)))

    kwargs: dict[str, Any] = {
        "videoFile": video_file,
        "fps": edl.fps,
        "width": edl.width,
        "height": edl.height,
        "durationInFrames": duration_in_frames,
        "captionsEnabled": edl.captions_enabled,
        "captions": captions,
        "graphicCues": edl.graphic_cues,
    }
    if "cameraFile" in TimelineManifest.model_fields:
        kwargs["cameraFile"] = camera_file

    return TimelineManifest(**kwargs)
