"""Companion cursor and focus-click logger for Hyprland and timeline cue mapping."""

from __future__ import annotations

import json
import math
import subprocess
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from schema import GraphicCue, KeepSegment


class CursorEvent(BaseModel):
    """Single sampled cursor position or synthesized dwell/click event."""

    t: float
    x: float
    y: float
    kind: Literal["move", "click"] = "move"
    title: str = ""


class CursorEventLog(BaseModel):
    """Normalized cursor event trace captured over a screen recording session."""

    width: int = 1920
    height: int = 1080
    events: list[CursorEvent] = Field(default_factory=list)


def parse_hyprctl_cursorpos(raw: str) -> tuple[float, float]:
    """Parse `hyprctl cursorpos` output in JSON or comma-separated format."""
    text = raw.strip()
    if not text:
        raise ValueError("Empty cursor position output")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        parts = [part.strip() for part in text.split(",")]
        if len(parts) != 2:
            raise ValueError(f"Invalid cursorpos format: {raw!r}")
        return (float(parts[0]), float(parts[1]))

    if not isinstance(data, dict) or "x" not in data or "y" not in data:
        raise ValueError(f"Invalid JSON cursorpos payload: {raw!r}")
    if isinstance(data["x"], bool) or isinstance(data["y"], bool):
        raise ValueError(f"Invalid boolean cursorpos coordinates: {raw!r}")
    try:
        return (float(data["x"]), float(data["y"]))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Non-numeric cursorpos coordinates: {raw!r}") from exc


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def record_hyprland_cursor(
    output_path: Path,
    duration_sec: float = 10.0,
    interval_sec: float = 0.1,
    width: int = 1920,
    height: int = 1080,
) -> CursorEventLog:
    """Poll `hyprctl cursorpos`, detect dwell/focus clicks, and write a JSON log."""
    safe_w = max(1, width)
    safe_h = max(1, height)
    interval = max(0.01, interval_sec)

    events: list[CursorEvent] = []
    start_mono = time.monotonic()
    deadline = start_mono + max(0.0, duration_sec)

    prev_x = 0.0
    prev_y = 0.0
    settle_x = 0.0
    settle_y = 0.0
    settle_start_t = 0.0
    move_origin_x = 0.0
    move_origin_y = 0.0
    armed = False
    settle_emitted = False

    step = 0
    while True:
        now = time.monotonic()
        t = max(0.0, now - start_mono)

        proc = subprocess.run(
            ["hyprctl", "cursorpos", "-j"],
            capture_output=True,
            text=True,
            check=True,
        )
        px, py = parse_hyprctl_cursorpos(proc.stdout)
        nx = _clamp01(px / safe_w)
        ny = _clamp01(py / safe_h)

        kind: Literal["move", "click"] = "move"
        if not events:
            settle_x, settle_y = nx, ny
            move_origin_x, move_origin_y = nx, ny
            settle_start_t = t
        else:
            step_dist = math.hypot(nx - prev_x, ny - prev_y)
            anchor_dist = math.hypot(nx - settle_x, ny - settle_y)

            if step_dist >= 0.05:
                armed = True
                settle_x, settle_y = nx, ny
                settle_start_t = t
                settle_emitted = False
            elif anchor_dist >= 0.015:
                if math.hypot(nx - move_origin_x, ny - move_origin_y) >= 0.05:
                    armed = True
                settle_x, settle_y = nx, ny
                settle_start_t = t
                settle_emitted = False
            elif armed and not settle_emitted and (t - settle_start_t) >= (0.4 - 1e-6):
                kind = "click"
                settle_emitted = True
                armed = False
                move_origin_x, move_origin_y = nx, ny

        prev_x, prev_y = nx, ny
        events.append(
            CursorEvent(
                t=round(t, 3),
                x=round(nx, 4),
                y=round(ny, 4),
                kind=kind,
            )
        )

        step += 1
        next_target = start_mono + step * interval
        if next_target > deadline:
            break
        sleep_for = next_target - time.monotonic()
        if sleep_for > 0:
            time.sleep(sleep_for)

    log = CursorEventLog(width=width, height=height, events=events)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(log.model_dump_json(indent=2), encoding="utf-8")
    return log


def cues_from_cursor_log(
    log: CursorEventLog,
    kept_segments: list[KeepSegment],
    max_cues: int = 5,
) -> list[GraphicCue]:
    """Map click events onto the concatenated edited timeline as cursor_highlight cues."""
    if max_cues <= 0 or not kept_segments:
        return []

    cues: list[GraphicCue] = []
    last_t: float | None = None
    click_events = sorted(
        (ev for ev in log.events if ev.kind == "click"),
        key=lambda ev: ev.t,
    )

    for ev in click_events:
        if len(cues) >= max_cues:
            break

        offset = 0.0
        mapped_t: float | None = None
        for seg in kept_segments:
            if seg.start <= ev.t <= seg.end:
                mapped_t = offset + (ev.t - seg.start)
                break
            offset += seg.end - seg.start

        if mapped_t is None:
            continue
        if last_t is not None and (mapped_t - last_t) < 1.5:
            continue

        idx = len(cues) + 1
        cues.append(
            GraphicCue(
                id=f"cursor_{idx:02d}",
                type="cursor_highlight",
                start=round(mapped_t, 3),
                duration=2.0,
                title=ev.title or "Focus",
                x=round(_clamp01(ev.x), 3),
                y=round(_clamp01(ev.y), 3),
            )
        )
        last_t = mapped_t

    return cues
