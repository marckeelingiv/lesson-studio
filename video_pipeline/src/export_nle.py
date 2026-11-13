"""FCPXML 1.9 timeline exporter for DaVinci Resolve and other NLEs."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from schema import EditDecisionList


def _to_rational_time(seconds: float, fps: float) -> str:
    """Convert seconds to frame-aligned FCPXML rational time string (e.g. '150/30s')."""
    fps_int = max(1, int(round(fps)))
    frames = max(0, int(round(seconds * fps_int)))
    frac = Fraction(frames, fps_int)
    if frac.denominator == 1:
        return f"{frac.numerator}s"
    return f"{frac.numerator}/{frac.denominator}s"


def export_fcpxml(edl: EditDecisionList, output_path: Path) -> Path:
    """Export an EditDecisionList as FCPXML 1.9 with cut clips and graphic markers."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source = Path(edl.source_path)
    fps_int = max(1, int(round(edl.fps)))
    total_dur = sum(s.end - s.start for s in edl.kept_segments)

    root = ET.Element("fcpxml", version="1.9")
    resources = ET.SubElement(root, "resources")
    ET.SubElement(
        resources,
        "format",
        id="r1",
        name=f"FFVideoFormat{edl.height}p{fps_int}",
        frameDuration=f"1/{fps_int}s",
        width=str(edl.width),
        height=str(edl.height),
    )
    ET.SubElement(
        resources,
        "asset",
        id="r2",
        name=source.name,
        src=source.resolve().as_uri(),
        hasVideo="1",
        hasAudio="1",
        format="r1",
    )

    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", name="AI Video Pipeline")
    project = ET.SubElement(event, "project", name=source.stem)
    sequence = ET.SubElement(
        project,
        "sequence",
        format="r1",
        duration=_to_rational_time(total_dur, edl.fps),
    )
    spine = ET.SubElement(sequence, "spine")

    offset = 0.0
    for seg in edl.kept_segments:
        dur = seg.end - seg.start
        clip = ET.SubElement(
            spine,
            "asset-clip",
            ref="r2",
            name=f"{source.stem}_{seg.id}",
            offset=_to_rational_time(offset, edl.fps),
            start=_to_rational_time(seg.start, edl.fps),
            duration=_to_rational_time(dur, edl.fps),
        )
        # Attach any graphic cues whose start falls inside this clip
        for cue in edl.graphic_cues:
            if offset <= cue.start < offset + dur:
                local_start = seg.start + (cue.start - offset)
                ET.SubElement(
                    clip,
                    "marker",
                    start=_to_rational_time(local_start, edl.fps),
                    duration=_to_rational_time(cue.duration, edl.fps),
                    value=f"[{cue.type}] {cue.title}",
                )
        offset += dur

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path
