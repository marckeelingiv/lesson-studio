"""OpenTimelineIO canonical timeline construction and NLE interchange (.otio, .fcpxml, .kdenlive)."""

from __future__ import annotations

from collections.abc import Mapping
import logging
import sys
from pathlib import Path
from typing import Any, Literal, get_args
from urllib.parse import unquote, urlparse

import opentimelineio as otio

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from export_nle import export_fcpxml as fallback_export_fcpxml  # noqa: E402
from schema import EditDecisionList, GraphicCue, GraphicType, KeepSegment  # noqa: E402

logger = logging.getLogger(__name__)

TRACK_AROLL_VIDEO = "A-Roll Video"
TRACK_CAMERA = "Camera"
TRACK_MOTION_PLATES = "Motion Plates"
TRACK_DIALOGUE = "Dialogue"
TRACK_MUSIC = "Music"
TRACK_SFX = "SFX"

_VALID_GRAPHIC_TYPES: frozenset[str] = frozenset(get_args(GraphicType))
_BEAT_MARKER_PREFIXES: frozenset[str] = frozenset(
    {"motion", "music", "sfx", "storyboard", "full screen", "panel", "centre", "full graphic", "circle"}
)
_NLE_ADAPTER_BY_SUFFIX: dict[str, str] = {
    ".otio": "otio_json",
    ".fcpxml": "otio_fcpx_xml_lite_adapter",
    ".kdenlive": "kdenlive",
}


def _quantize_frames(seconds: float, fps: float) -> int:
    """Quantize seconds onto the integer source frame grid."""
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    return max(0, int(round(seconds * fps)))


def _rational_time(seconds: float, fps: float) -> otio.opentime.RationalTime:
    """Create a frame-quantized RationalTime at rate=fps."""
    return otio.opentime.RationalTime(_quantize_frames(seconds, fps), fps)


def _time_range_from_bounds(start_sec: float, end_sec: float, fps: float, min_frames: int = 1) -> otio.opentime.TimeRange:
    """Build a frame-quantized TimeRange from [start_sec, end_sec]."""
    start_frames = _quantize_frames(start_sec, fps)
    end_frames = _quantize_frames(end_sec, fps)
    dur_frames = max(min_frames, end_frames - start_frames)
    return otio.opentime.TimeRange(
        start_time=otio.opentime.RationalTime(start_frames, fps),
        duration=otio.opentime.RationalTime(dur_frames, fps),
    )


def _path_to_uri(path_or_url: str) -> str:
    """Convert a local filesystem path into a file:// URI without double-wrapping URIs."""
    parsed = urlparse(path_or_url)
    if parsed.scheme in {"file", "http", "https"}:
        return path_or_url
    return Path(path_or_url).resolve().as_uri()


def _uri_to_path(url: str) -> str:
    """Decode a file:// URI back to a local path string."""
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    return url


def _timeline_fps(timeline: otio.schema.Timeline) -> float:
    """Infer positive frame rate from global_start_time or first available clip."""
    if timeline.global_start_time is not None and timeline.global_start_time.rate > 0:
        return float(timeline.global_start_time.rate)
    for clip in timeline.find_clips():
        if clip.source_range is not None and clip.source_range.duration.rate > 0:
            return float(clip.source_range.duration.rate)
    return 30.0


def _primary_track(timeline: otio.schema.Timeline) -> otio.schema.Track | None:
    """Locate the primary editorial track ('A-Roll Video', fallback Video track, or Dialogue/Audio)."""
    for track in timeline.tracks:
        if track.name == TRACK_AROLL_VIDEO:
            return track
    for track in timeline.tracks:
        if track.kind == otio.schema.TrackKind.Video and track.name not in {TRACK_CAMERA, TRACK_MOTION_PLATES}:
            return track
    for track in timeline.tracks:
        if track.name == TRACK_DIALOGUE:
            return track
    for track in timeline.tracks:
        if track.kind == otio.schema.TrackKind.Audio:
            return track
    return timeline.tracks[0] if len(timeline.tracks) > 0 else None


def _build_source_clips_track(
    track_name: str,
    kind: otio.schema.TrackKind,
    media_url: str,
    kept_segments: list[KeepSegment],
    fps: float,
    available_range: otio.opentime.TimeRange,
    name_suffix: str = "",
) -> otio.schema.Track:
    """Create a Video or Audio track populated with frame-quantized Clips for kept segments."""
    track = otio.schema.Track(name=track_name, kind=kind)
    for seg in kept_segments:
        src_range = _time_range_from_bounds(seg.start, seg.end, fps, min_frames=1)
        media_ref = otio.schema.ExternalReference(
            target_url=media_url,
            available_range=otio.opentime.TimeRange(
                start_time=available_range.start_time,
                duration=available_range.duration,
            ),
        )
        clip = otio.schema.Clip(
            name=f"{seg.id}{name_suffix}",
            media_reference=media_ref,
            source_range=src_range,
            metadata={"keep_id": seg.id, "reason": seg.reason},
        )
        track.append(clip)
    return track


def _populate_timed_track(
    track_name: str,
    kind: otio.schema.TrackKind,
    items: list[tuple[float, float, otio.schema.Clip]],
    fps: float,
) -> otio.schema.Track:
    """Place timeline-positioned Clips on a Track separated by frame-quantized Gaps."""
    track = otio.schema.Track(name=track_name, kind=kind)
    cursor_frames = 0
    for start_sec, end_sec, clip in sorted(items, key=lambda item: item[0]):
        start_frames = _quantize_frames(start_sec, fps)
        end_frames = _quantize_frames(end_sec, fps)
        dur_frames = max(1, end_frames - start_frames)
        if start_frames < cursor_frames:
            # Clamp start forward to avoid invalid negative gaps on overlapping entries.
            start_frames = cursor_frames
        gap_frames = start_frames - cursor_frames
        if gap_frames > 0:
            track.append(
                otio.schema.Gap(
                    duration=otio.opentime.RationalTime(gap_frames, fps),
                )
            )
        clip.source_range = otio.opentime.TimeRange(
            start_time=clip.source_range.start_time if clip.source_range else otio.opentime.RationalTime(0, fps),
            duration=otio.opentime.RationalTime(dur_frames, fps),
        )
        track.append(clip)
        cursor_frames = start_frames + dur_frames
    return track


def _attach_marker_to_aroll(
    aroll_track: otio.schema.Track,
    marker_tl_start: otio.opentime.RationalTime,
    marker_duration: otio.opentime.RationalTime,
    marker_name: str,
    color: otio.schema.MarkerColor,
    metadata: dict[str, Any],
) -> None:
    """Attach a matching Marker in clip-local source time to the overlapping A-Roll clip."""
    fps = marker_tl_start.rate
    cursor_frames = 0
    target_frame = marker_tl_start.to_frames()
    for item in aroll_track:
        item_dur_frames = item.duration().to_frames()
        if isinstance(item, otio.schema.Clip) and cursor_frames <= target_frame < cursor_frames + item_dur_frames:
            offset_frames = target_frame - cursor_frames
            clip_start_frames = item.trimmed_range().start_time.to_frames()
            item.markers.append(
                otio.schema.Marker(
                    name=marker_name,
                    marked_range=otio.opentime.TimeRange(
                        start_time=otio.opentime.RationalTime(clip_start_frames + offset_frames, fps),
                        duration=marker_duration,
                    ),
                    color=color,
                    metadata=dict(metadata),
                )
            )
            return
        cursor_frames += item_dur_frames


def _beat_to_track_role(beat: dict[str, Any]) -> Literal["motion", "music", "sfx"]:
    """Determine which optional track a storyboard beat belongs to."""
    track = str(beat.get("track", "")).strip().lower()
    kind = str(beat.get("kind", "")).strip().lower()
    audio_type = str(beat.get("audio_type", "")).strip().lower()
    if track == "music" or kind == "music" or audio_type == "music":
        return "music"
    if track == "sfx" or audio_type == "sfx" or kind in {"sfx", "whoosh", "pop", "ui_click", "soft_hit", "riser"}:
        return "sfx"
    return "motion"


def edl_to_otio(
    edl: EditDecisionList,
    storyboard_beats: list[dict[str, Any]] | None = None,
    name: str | None = None,
) -> otio.schema.Timeline:
    """Convert an EditDecisionList and optional storyboard beats into a canonical OTIO Timeline."""
    fps = float(edl.fps)
    if fps <= 0:
        raise ValueError(f"EDL fps must be positive, got {edl.fps}")

    timeline_name = name or (Path(edl.source_path).stem if edl.source_path else "Lesson Timeline")
    timeline = otio.schema.Timeline(
        name=timeline_name,
        global_start_time=otio.opentime.RationalTime(0, fps),
    )

    max_end_sec = max((seg.end for seg in edl.kept_segments), default=0.0)
    avail_frames = max(1, _quantize_frames(max_end_sec, fps))
    available_range = otio.opentime.TimeRange(
        start_time=otio.opentime.RationalTime(0, fps),
        duration=otio.opentime.RationalTime(avail_frames, fps),
    )

    source_url = _path_to_uri(edl.source_path) if edl.source_path else "file:///source.mp4"
    aroll_track = _build_source_clips_track(
        TRACK_AROLL_VIDEO,
        otio.schema.TrackKind.Video,
        source_url,
        edl.kept_segments,
        fps,
        available_range,
    )
    timeline.tracks.append(aroll_track)

    if edl.camera_path:
        cam_url = _path_to_uri(edl.camera_path)
        camera_track = _build_source_clips_track(
            TRACK_CAMERA,
            otio.schema.TrackKind.Video,
            cam_url,
            edl.kept_segments,
            fps,
            available_range,
            name_suffix="_cam",
        )
        timeline.tracks.append(camera_track)

    motion_items: list[tuple[float, float, otio.schema.Clip]] = []
    music_items: list[tuple[float, float, otio.schema.Clip]] = []
    sfx_items: list[tuple[float, float, otio.schema.Clip]] = []

    for idx, cue in enumerate(edl.graphic_cues):
        start_rt = _rational_time(cue.start, fps)
        dur_frames = max(1, _quantize_frames(cue.duration, fps))
        dur_rt = otio.opentime.RationalTime(dur_frames, fps)
        marker_label = f"[{cue.type}] {cue.title}".strip()
        marker_meta = {"graphic_cue": cue.model_dump()}

        timeline.tracks.markers.append(
            otio.schema.Marker(
                name=marker_label,
                marked_range=otio.opentime.TimeRange(start_time=start_rt, duration=dur_rt),
                color=otio.schema.MarkerColor.CYAN,
                metadata=dict(marker_meta),
            )
        )
        _attach_marker_to_aroll(
            aroll_track,
            start_rt,
            dur_rt,
            marker_label,
            otio.schema.MarkerColor.CYAN,
            marker_meta,
        )

        plate_ref = otio.schema.GeneratorReference(
            name=cue.id or f"plate_{idx + 1:02d}",
            generator_kind="fcpx_video_placeholder",
            parameters={
                "fcpx_ref": f"r_plate_{idx + 1:02d}",
                "fcpx_effect_name": cue.type,
                "fcpx_effect_uid": f"lesson_studio.motion_plate.{cue.type}",
            },
        )
        plate_clip = otio.schema.Clip(
            name=marker_label,
            media_reference=plate_ref,
            source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, fps), dur_rt),
            metadata={"graphic_cue": cue.model_dump()},
        )
        motion_items.append((cue.start, cue.start + cue.duration, plate_clip))

    for idx, beat in enumerate(storyboard_beats or []):
        start_sec = float(beat.get("start", beat.get("start_sec", 0.0)))
        if "end" in beat and "duration" not in beat:
            dur_sec = max(1.0 / fps, float(beat["end"]) - start_sec)
        else:
            dur_sec = max(1.0 / fps, float(beat.get("duration", 2.0)))
        start_rt = _rational_time(start_sec, fps)
        dur_frames = max(1, _quantize_frames(dur_sec, fps))
        dur_rt = otio.opentime.RationalTime(dur_frames, fps)

        role = _beat_to_track_role(beat)
        beat_title = str(beat.get("title") or beat.get("name") or beat.get("label") or beat.get("id") or f"Beat {idx + 1}")
        beat_type = str(beat.get("type") or beat.get("layout") or beat.get("scene_layout") or role)
        marker_label = f"[{beat_type}] {beat_title}"
        beat_meta = {"storyboard_beat": dict(beat)}

        timeline.tracks.markers.append(
            otio.schema.Marker(
                name=marker_label,
                marked_range=otio.opentime.TimeRange(start_time=start_rt, duration=dur_rt),
                color=otio.schema.MarkerColor.GREEN if role == "motion" else otio.schema.MarkerColor.ORANGE,
                metadata=dict(beat_meta),
            )
        )
        _attach_marker_to_aroll(
            aroll_track,
            start_rt,
            dur_rt,
            marker_label,
            otio.schema.MarkerColor.GREEN if role == "motion" else otio.schema.MarkerColor.ORANGE,
            beat_meta,
        )

        asset_path = beat.get("asset_path") or beat.get("media_path")
        if asset_path:
            media_ref: otio.schema.MediaReference = otio.schema.ExternalReference(
                target_url=_path_to_uri(str(asset_path)),
                available_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, fps), dur_rt),
            )
        else:
            media_ref = otio.schema.GeneratorReference(
                name=beat_title,
                generator_kind="fcpx_video_placeholder",
                parameters={
                    "fcpx_ref": f"r_beat_{idx + 1:02d}",
                    "fcpx_effect_name": beat_type,
                    "fcpx_effect_uid": f"lesson_studio.beat.{beat_type}",
                },
            )
        clip = otio.schema.Clip(
            name=beat_title,
            media_reference=media_ref,
            source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, fps), dur_rt),
            metadata=dict(beat_meta),
        )
        if role == "music":
            music_items.append((start_sec, start_sec + dur_sec, clip))
        elif role == "sfx":
            sfx_items.append((start_sec, start_sec + dur_sec, clip))
        else:
            motion_items.append((start_sec, start_sec + dur_sec, clip))

    if motion_items:
        timeline.tracks.append(
            _populate_timed_track(TRACK_MOTION_PLATES, otio.schema.TrackKind.Video, motion_items, fps)
        )

    dialogue_track = _build_source_clips_track(
        TRACK_DIALOGUE,
        otio.schema.TrackKind.Audio,
        source_url,
        edl.kept_segments,
        fps,
        available_range,
        name_suffix="_audio",
    )
    timeline.tracks.append(dialogue_track)

    if music_items:
        timeline.tracks.append(_populate_timed_track(TRACK_MUSIC, otio.schema.TrackKind.Audio, music_items, fps))
    if sfx_items:
        timeline.tracks.append(_populate_timed_track(TRACK_SFX, otio.schema.TrackKind.Audio, sfx_items, fps))

    timeline.metadata["lesson_studio"] = {
        "source_path": edl.source_path,
        "camera_path": edl.camera_path,
        "fps": fps,
        "width": edl.width,
        "height": edl.height,
        "captions_enabled": edl.captions_enabled,
        "summary": edl.summary,
        "storyboard_beats": list(storyboard_beats or []),
    }
    return timeline


def _parse_marker_cue(
    marker: otio.schema.Marker,
    start_sec: float,
    idx: int,
) -> GraphicCue | None:
    """Reconstruct a GraphicCue from a marker's metadata or '[type] title' label."""
    cue_data = marker.metadata.get("graphic_cue") if isinstance(marker.metadata, Mapping) else None
    if isinstance(cue_data, Mapping):
        return GraphicCue.model_validate(dict(cue_data))

    if isinstance(marker.metadata, Mapping) and "storyboard_beat" in marker.metadata:
        return None

    raw_name = (marker.name or "").strip()
    if not raw_name:
        return None

    cue_type: GraphicType = "callout"
    title = raw_name
    if raw_name.startswith("[") and "]" in raw_name:
        prefix, rest = raw_name[1:].split("]", 1)
        candidate_type = prefix.strip()
        if candidate_type in _VALID_GRAPHIC_TYPES:
            cue_type = candidate_type  # type: ignore[assignment]
            title = rest.strip() or candidate_type
        elif candidate_type.lower() in _BEAT_MARKER_PREFIXES:
            return None

    dur_sec = max(0.5, round(marker.marked_range.duration.to_seconds(), 6))
    return GraphicCue(
        id=f"gfx_{idx:02d}",
        type=cue_type,
        start=round(max(0.0, start_sec), 6),
        duration=dur_sec,
        title=title,
    )


def otio_to_edl(
    timeline: otio.schema.Timeline,
    width: int = 1920,
    height: int = 1080,
) -> EditDecisionList:
    """Convert an OTIO Timeline back into an EditDecisionList."""
    fps = _timeline_fps(timeline)
    meta = timeline.metadata.get("lesson_studio", {}) if isinstance(timeline.metadata, Mapping) else {}
    if not isinstance(meta, Mapping):
        meta = {}

    resolved_width = int(meta["width"]) if (width == 1920 and height == 1080 and "width" in meta) else width
    resolved_height = int(meta["height"]) if (width == 1920 and height == 1080 and "height" in meta) else height

    primary = _primary_track(timeline)
    kept_segments: list[KeepSegment] = []
    source_path = str(meta.get("source_path") or "")

    cues_by_key: dict[tuple[str, float, str], GraphicCue] = {}

    def _register_cue(cue: GraphicCue) -> None:
        key = (cue.type, round(cue.start, 3), cue.title)
        if key not in cues_by_key:
            cues_by_key[key] = cue

    if primary is not None:
        tl_cursor = otio.opentime.RationalTime(0, fps)
        seg_idx = 0
        for item in primary:
            item_dur = item.duration()
            if isinstance(item, otio.schema.Clip):
                seg_idx += 1
                if not source_path and isinstance(item.media_reference, otio.schema.ExternalReference):
                    if item.media_reference.target_url:
                        source_path = _uri_to_path(item.media_reference.target_url)

                src_range = item.trimmed_range()
                start_sec = round(src_range.start_time.to_seconds(), 6)
                end_sec = round(src_range.end_time_exclusive().to_seconds(), 6)
                clip_meta = item.metadata if isinstance(item.metadata, Mapping) else {}
                seg_id = str(clip_meta.get("keep_id") or item.name or f"seg_{seg_idx:02d}")
                reason = str(clip_meta.get("reason") or "")
                kept_segments.append(
                    KeepSegment(
                        id=seg_id,
                        start=start_sec,
                        end=end_sec,
                        reason=reason,
                    )
                )

                clip_tl_start_sec = tl_cursor.to_seconds()
                clip_src_start_sec = src_range.start_time.to_seconds()
                for m_idx, marker in enumerate(item.markers, start=1):
                    offset_in_clip = max(0.0, marker.marked_range.start_time.to_seconds() - clip_src_start_sec)
                    cue = _parse_marker_cue(marker, clip_tl_start_sec + offset_in_clip, m_idx)
                    if cue is not None:
                        _register_cue(cue)

            tl_cursor += item_dur

    camera_path: str | None = meta.get("camera_path")
    for track in timeline.tracks:
        if track.name == TRACK_CAMERA and not camera_path:
            for item in track:
                if isinstance(item, otio.schema.Clip) and isinstance(item.media_reference, otio.schema.ExternalReference):
                    if item.media_reference.target_url:
                        camera_path = _uri_to_path(item.media_reference.target_url)
                        break

        if track.name == TRACK_MOTION_PLATES or (
            track is not primary and track.kind == otio.schema.TrackKind.Video and track.name != TRACK_CAMERA
        ):
            tl_cursor = otio.opentime.RationalTime(0, fps)
            for c_idx, item in enumerate(track, start=1):
                item_dur = item.duration()
                if isinstance(item, otio.schema.Clip):
                    clip_meta = item.metadata if isinstance(item.metadata, Mapping) else {}
                    if isinstance(clip_meta.get("graphic_cue"), Mapping):
                        _register_cue(GraphicCue.model_validate(dict(clip_meta["graphic_cue"])))
                    elif isinstance(item.media_reference, otio.schema.GeneratorReference):
                        params = item.media_reference.parameters or {}
                        eff_name = str(params.get("fcpx_effect_name") or "").strip()
                        if eff_name in _VALID_GRAPHIC_TYPES:
                            title = item.name or eff_name
                            if title.startswith("[") and "]" in title:
                                title = title.split("]", 1)[1].strip() or eff_name
                            _register_cue(
                                GraphicCue(
                                    id=f"gfx_{c_idx:02d}",
                                    type=eff_name,  # type: ignore[arg-type]
                                    start=round(tl_cursor.to_seconds(), 6),
                                    duration=max(0.5, round(item_dur.to_seconds(), 6)),
                                    title=title,
                                )
                            )
                tl_cursor += item_dur

    for m_idx, marker in enumerate(timeline.tracks.markers, start=1):
        cue = _parse_marker_cue(marker, marker.marked_range.start_time.to_seconds(), m_idx)
        if cue is not None:
            _register_cue(cue)

    graphic_cues = sorted(cues_by_key.values(), key=lambda c: c.start)

    return EditDecisionList(
        source_path=source_path,
        camera_path=camera_path,
        fps=round(fps, 3),
        width=resolved_width,
        height=resolved_height,
        kept_segments=kept_segments,
        graphic_cues=graphic_cues,
        captions_enabled=bool(meta.get("captions_enabled", True)),
        summary=str(meta.get("summary") or ""),
    )


def source_to_edit_map(timeline: otio.schema.Timeline) -> list[dict[str, Any]]:
    """Return piecewise source-to-edit time intervals along the primary timeline track."""
    primary = _primary_track(timeline)
    if primary is None:
        return []

    fps = _timeline_fps(timeline)
    edit_cursor = otio.opentime.RationalTime(0, fps)
    intervals: list[dict[str, Any]] = []
    clip_num = 0

    for item in primary:
        item_dur = item.duration()
        if isinstance(item, otio.schema.Clip):
            clip_num += 1
            src_range = item.trimmed_range()
            dur_rt = src_range.duration
            clip_meta = item.metadata if isinstance(item.metadata, Mapping) else {}
            clip_id = str(clip_meta.get("keep_id") or item.name or f"clip_{clip_num:02d}")
            edit_end = edit_cursor + dur_rt
            intervals.append(
                {
                    "clip_id": clip_id,
                    "source_start": round(src_range.start_time.to_seconds(), 6),
                    "source_end": round(src_range.end_time_exclusive().to_seconds(), 6),
                    "edit_start": round(edit_cursor.to_seconds(), 6),
                    "edit_end": round(edit_end.to_seconds(), 6),
                    "duration": round(dur_rt.to_seconds(), 6),
                }
            )
            edit_cursor = edit_end
        else:
            edit_cursor += item_dur

    return intervals


def save_otio(timeline: otio.schema.Timeline, path: Path) -> Path:
    """Serialize an OTIO Timeline to an .otio JSON file."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    otio.adapters.write_to_file(timeline, str(out), adapter_name="otio_json")
    return out


def load_otio(path: Path) -> otio.schema.Timeline:
    """Load an OTIO Timeline from an .otio JSON file."""
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(f"OTIO file not found: {src}")
    loaded = otio.adapters.read_from_file(str(src), adapter_name="otio_json")
    if isinstance(loaded, otio.schema.SerializableCollection):
        for item in loaded:
            if isinstance(item, otio.schema.Timeline):
                return item
        raise ValueError(f"No Timeline found in OTIO collection: {src}")
    if not isinstance(loaded, otio.schema.Timeline):
        raise ValueError(f"Expected otio.schema.Timeline, got {type(loaded).__name__}")
    return loaded


def _record_export(
    timeline: otio.schema.Timeline,
    fmt: str,
    adapter_used: str,
    output_path: Path,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
) -> None:
    """Record export adapter metadata on timeline.metadata for auditability."""
    entry: dict[str, Any] = {
        "format": fmt,
        "adapter": adapter_used,
        "fallback_used": fallback_used,
        "output_path": str(output_path),
    }
    if fallback_reason:
        entry["fallback_reason"] = fallback_reason
    timeline.metadata["last_nle_export"] = entry
    history = timeline.metadata.get("nle_export_history")
    if not isinstance(history, list):
        history = []
    history.append(entry)
    timeline.metadata["nle_export_history"] = history


def export_nle(
    timeline: otio.schema.Timeline,
    output_path: Path,
    fmt: Literal["otio", "fcpxml", "kdenlive"],
) -> Path:
    """Export an OTIO Timeline to .otio, .fcpxml (with clean fallback), or .kdenlive."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "otio":
        save_otio(timeline, out)
        _record_export(timeline, fmt, "otio_json", out, fallback_used=False)
        logger.info("Exported OTIO timeline via otio_json -> %s", out)
        return out

    if fmt == "fcpxml":
        try:
            otio.adapters.write_to_file(
                timeline,
                str(out),
                adapter_name="otio_fcpx_xml_lite_adapter",
            )
            if not out.exists() or out.stat().st_size == 0:
                raise RuntimeError("FCPXML adapter produced an empty output file")
            _record_export(timeline, fmt, "otio_fcpx_xml_lite_adapter", out, fallback_used=False)
            logger.info("Exported FCPXML timeline via otio_fcpx_xml_lite_adapter -> %s", out)
            return out
        except Exception as exc:
            logger.warning(
                "otio_fcpx_xml_lite_adapter failed (%s); falling back to export_nle.export_fcpxml",
                exc,
            )
            edl = otio_to_edl(timeline)
            if not edl.source_path:
                edl = edl.model_copy(update={"source_path": str(out.with_suffix(".mp4"))})
            fallback_export_fcpxml(edl, out)
            _record_export(
                timeline,
                fmt,
                "export_nle.export_fcpxml",
                out,
                fallback_used=True,
                fallback_reason=str(exc),
            )
            return out

    if fmt == "kdenlive":
        otio.adapters.write_to_file(timeline, str(out), adapter_name="kdenlive")
        _record_export(timeline, fmt, "kdenlive", out, fallback_used=False)
        logger.info("Exported Kdenlive timeline via kdenlive adapter -> %s", out)
        return out

    raise ValueError(f"Unsupported NLE format: {fmt!r}")


def import_nle(path: Path) -> otio.schema.Timeline:
    """Import an .otio, .fcpxml, or .kdenlive file into an OTIO Timeline."""
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(f"Timeline file not found: {src}")

    suffix = src.suffix.lower()
    adapter_name = _NLE_ADAPTER_BY_SUFFIX.get(suffix)
    if adapter_name is None:
        raise ValueError(f"Unsupported NLE timeline extension {src.suffix!r}; expected .otio, .fcpxml, or .kdenlive")

    loaded = otio.adapters.read_from_file(str(src), adapter_name=adapter_name)
    if isinstance(loaded, otio.schema.SerializableCollection):
        timeline = next((item for item in loaded if isinstance(item, otio.schema.Timeline)), None)
        if timeline is None:
            raise ValueError(f"No Timeline found in {src}")
    elif isinstance(loaded, otio.schema.Timeline):
        timeline = loaded
    else:
        raise ValueError(f"Expected Timeline from {adapter_name}, got {type(loaded).__name__}")

    if timeline.global_start_time is None:
        timeline.global_start_time = otio.opentime.RationalTime(0, _timeline_fps(timeline))

    return timeline
