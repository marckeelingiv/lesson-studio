"""Automated QC runner implementing Technical Engine Room Rule 04."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np
from pydantic import BaseModel, Field

try:
    from .schema import KeepSegment, TranscriptBundle, WordTiming
except ImportError:
    from schema import KeepSegment, TranscriptBundle, WordTiming


ALLOWED_WAIVER_GATES: frozenset[str] = frozenset({"eyes_mouth_check", "freeze_check"})
TERMINAL_PUNCTUATION: frozenset[str] = frozenset({".", "?", "!"})
_TRAILING_QUOTE_CHARS = "\"'”’)]"


class QCFinding(BaseModel):
    """Single defect, warning, or waived observation produced by a QC gate."""

    gate: str
    severity: Literal["error", "warning", "info"] = "error"
    message: str
    timestamp: float | None = None
    start: float | None = None
    end: float | None = None
    frame_index: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    waived: bool = False
    waiver_reason: str | None = None


class QCWaiver(BaseModel):
    """Explicit timestamped waiver entry matching the shared run.json contract."""

    gate: str
    start: float
    end: float
    reason: str
    approved_by: str
    timestamp: str


class GateResult(BaseModel):
    """Outcome for a single automated QC gate."""

    gate: str
    passed: bool
    findings: list[QCFinding] = Field(default_factory=list)
    waived_findings: list[QCFinding] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    summary: str = ""


class QCReport(BaseModel):
    """Aggregated QC run report persisted as qc_report.json."""

    video_path: str
    delivery_mode: bool = False
    passed: bool
    gates: dict[str, GateResult] = Field(default_factory=dict)
    waivers_applied: list[QCWaiver] = Field(default_factory=list)
    failed_gates: list[str] = Field(default_factory=list)
    created_at: str
    report_path: str | None = None


def _parse_rate(rate_str: str | None) -> float:
    if not rate_str:
        return 0.0
    if "/" in rate_str:
        num_s, den_s = rate_str.split("/", 1)
        den = float(den_s)
        return float(num_s) / den if den else 0.0
    return float(rate_str)


def _ffprobe_info(video_path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(res.stdout)


def _video_props(video_path: Path) -> tuple[int, int, float, float, bool]:
    """Return (width, height, fps, duration, has_audio) from ffprobe."""
    data = _ffprobe_info(video_path)
    streams = data.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if v_stream is None:
        raise ValueError(f"No video stream found in {video_path}")
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    width = int(v_stream["width"])
    height = int(v_stream["height"])
    fps = _parse_rate(v_stream.get("r_frame_rate")) or _parse_rate(v_stream.get("avg_frame_rate")) or 30.0
    duration = float(data.get("format", {}).get("duration") or v_stream.get("duration") or 0.0)
    return width, height, fps, duration, has_audio


def _is_valid_waiver_metadata(w: QCWaiver) -> bool:
    return (
        w.gate in ALLOWED_WAIVER_GATES
        and w.end > w.start
        and bool(w.reason.strip())
        and bool(w.approved_by.strip())
        and bool(w.timestamp.strip())
    )


def validate_waivers(waivers: list[QCWaiver] | None) -> GateResult:
    """Enforce Rule 04 §3 strict waiver policy."""
    findings: list[QCFinding] = []
    waiver_list = waivers or []
    for idx, w in enumerate(waiver_list):
        if w.gate not in ALLOWED_WAIVER_GATES:
            findings.append(
                QCFinding(
                    gate="waiver_policy",
                    message=(
                        f"Illegal waiver[{idx}] for non-waivable gate '{w.gate}'. "
                        f"Only {sorted(ALLOWED_WAIVER_GATES)} may be waived."
                    ),
                    start=w.start,
                    end=w.end,
                    details={"gate": w.gate, "approved_by": w.approved_by},
                )
            )
            continue
        if w.end <= w.start:
            findings.append(
                QCFinding(
                    gate="waiver_policy",
                    message=f"Waiver[{idx}] for '{w.gate}' has invalid range [{w.start}, {w.end}].",
                    start=w.start,
                    end=w.end,
                )
            )
        if not w.reason.strip() or not w.approved_by.strip() or not w.timestamp.strip():
            findings.append(
                QCFinding(
                    gate="waiver_policy",
                    message=f"Waiver[{idx}] for '{w.gate}' is missing reason, approved_by, or timestamp.",
                    start=w.start,
                    end=w.end,
                )
            )

    return GateResult(
        gate="waiver_policy",
        passed=len(findings) == 0,
        findings=findings,
        metrics={"total_waivers": len(waiver_list)},
        summary="Waiver policy verified." if not findings else f"{len(findings)} waiver policy violation(s).",
    )


def _find_matching_waiver(gate: str, ts: float, waivers: list[QCWaiver] | None) -> QCWaiver | None:
    for w in waivers or []:
        if w.gate == gate and _is_valid_waiver_metadata(w) and (w.start - 1e-6) <= ts <= (w.end + 1e-6):
            return w
    return None


def _interval_covered_by_waivers(
    gate: str,
    start: float,
    end: float,
    waivers: list[QCWaiver] | None,
    tolerance: float = 0.15,
) -> QCWaiver | None:
    valid = [w for w in (waivers or []) if w.gate == gate and _is_valid_waiver_metadata(w)]
    if not valid:
        return None
    # Single waiver covering interval within tolerance
    for w in valid:
        if w.start <= start + tolerance and w.end >= end - tolerance:
            return w
    # Merged contiguous waivers covering interval
    intervals = sorted((w.start, w.end, w) for w in valid)
    cur_s, cur_e, first_w = intervals[0]
    for s, e, w in intervals[1:]:
        if s <= cur_e + tolerance:
            cur_e = max(cur_e, e)
        else:
            if cur_s <= start + tolerance and cur_e >= end - tolerance:
                return first_w
            cur_s, cur_e, first_w = s, e, w
    if cur_s <= start + tolerance and cur_e >= end - tolerance:
        return first_w
    return None


def _downsample_frame(frame: np.ndarray, max_width: int = 320) -> np.ndarray:
    h, w = frame.shape[:2]
    if w > max_width:
        scale = max_width / float(w)
        frame = cv2.resize(frame, (max_width, max(1, int(round(h * scale)))), interpolation=cv2.INTER_AREA)
    return frame.astype(np.float32)


def _frame_diff(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a - b)))


def _detect_flash_in_sequence(
    frames: list[tuple[int, float, np.ndarray]],
    window_start_idx: int | None = None,
    window_end_idx: int | None = None,
) -> list[QCFinding]:
    """Identify 1-2 frame visual spikes surrounded by calmer neighboring frames."""
    findings: list[QCFinding] = []
    n = len(frames)
    if n < 3:
        return findings

    diffs = [_frame_diff(frames[i][2], frames[i + 1][2]) for i in range(n - 1)]
    seen_burst_frames: set[int] = set()

    for w in (1, 2):
        for k in range(1, n - w):
            f_idx = frames[k][0]
            if window_start_idx is not None and f_idx < window_start_idx:
                continue
            if window_end_idx is not None and f_idx > window_end_idx:
                continue
            if any(frames[j][0] in seen_burst_frames for j in range(k, k + w)):
                continue

            d_in = diffs[k - 1]
            d_out = diffs[k + w - 1]
            entry_exit_min = min(d_in, d_out)
            if entry_exit_min < 16.0:
                continue

            if w == 2 and diffs[k] > 0.5 * entry_exit_min:
                continue

            neighbor_diffs: list[float] = []
            if k - 2 >= 0:
                neighbor_diffs.append(diffs[k - 2])
            if k + w < n - 1:
                neighbor_diffs.append(diffs[k + w])
            calm_ref = max(neighbor_diffs) if neighbor_diffs else 0.0

            if calm_ref <= 6.0 or entry_exit_min >= 2.5 * calm_ref:
                for j in range(k, k + w):
                    seen_burst_frames.add(frames[j][0])
                start_f, start_ts, _ = frames[k]
                end_f, end_ts, _ = frames[k + w - 1]
                findings.append(
                    QCFinding(
                        gate="flash",
                        message=(
                            f"Detected {w}-frame Flash Frame spike at frame(s) "
                            f"{start_f}..{end_f} ({start_ts:.3f}s) "
                            f"[d_in={d_in:.1f}, d_out={d_out:.1f}, calm={calm_ref:.1f}]."
                        ),
                        timestamp=start_ts,
                        start=start_ts,
                        end=end_ts,
                        frame_index=start_f,
                        details={
                            "burst_frames": w,
                            "d_in": round(d_in, 2),
                            "d_out": round(d_out, 2),
                            "calm_ref": round(calm_ref, 2),
                        },
                    )
                )
    return findings


def check_flash(video_path: Path, cut_timestamps: list[float]) -> GateResult:
    """Gate 1 (`flash`): inspect +/- 3 frames around cuts (or full video) for 1-2 frame spikes."""
    if not video_path.exists():
        return GateResult(
            gate="flash",
            passed=False,
            findings=[QCFinding(gate="flash", message=f"Video file missing: {video_path}")],
        )

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return GateResult(
            gate="flash",
            passed=False,
            findings=[QCFinding(gate="flash", message=f"Failed to open video: {video_path}")],
        )

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if fps <= 0:
            fps = 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        findings: list[QCFinding] = []
        inspected_windows = 0

        if cut_timestamps:
            # Read +/- 5 frames around each cut so +/- 3 candidate frames retain outer neighbors.
            merged_windows: list[tuple[int, int, int, int]] = []
            for ts in sorted(cut_timestamps):
                center = int(round(ts * fps))
                r_s = max(0, center - 5)
                r_e = center + 5 if total_frames <= 0 else min(total_frames - 1, center + 5)
                c_s = max(0, center - 3)
                c_e = center + 3
                if merged_windows and r_s <= merged_windows[-1][1]:
                    p_rs, p_re, p_cs, p_ce = merged_windows[-1]
                    merged_windows[-1] = (p_rs, max(p_re, r_e), min(p_cs, c_s), max(p_ce, c_e))
                else:
                    merged_windows.append((r_s, r_e, c_s, c_e))

            for r_s, r_e, c_s, c_e in merged_windows:
                inspected_windows += 1
                cap.set(cv2.CAP_PROP_POS_FRAMES, r_s)
                seq: list[tuple[int, float, np.ndarray]] = []
                for idx in range(r_s, r_e + 1):
                    ok, frame = cap.read()
                    if not ok:
                        break
                    seq.append((idx, idx / fps, _downsample_frame(frame)))
                findings.extend(_detect_flash_in_sequence(seq, window_start_idx=c_s, window_end_idx=c_e))
        else:
            inspected_windows = 1
            ring: list[tuple[int, float, np.ndarray]] = []
            seen_indices: set[int] = set()
            idx = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                ring.append((idx, idx / fps, _downsample_frame(frame)))
                if len(ring) > 7:
                    ring.pop(0)
                if len(ring) >= 5:
                    for f in _detect_flash_in_sequence(ring, window_start_idx=ring[1][0], window_end_idx=ring[-2][0]):
                        if f.frame_index not in seen_indices:
                            seen_indices.add(f.frame_index or -1)
                            findings.append(f)
                idx += 1
            if len(ring) >= 3:
                for f in _detect_flash_in_sequence(ring):
                    if f.frame_index not in seen_indices:
                        seen_indices.add(f.frame_index or -1)
                        findings.append(f)

        return GateResult(
            gate="flash",
            passed=len(findings) == 0,
            findings=findings,
            metrics={"cut_count": len(cut_timestamps), "inspected_windows": inspected_windows, "fps": fps},
            summary="No Flash Frames detected." if not findings else f"Detected {len(findings)} Flash Frame spike(s).",
        )
    finally:
        cap.release()


def _parse_blackdetect(stderr: str) -> list[tuple[float, float, float]]:
    intervals: list[tuple[float, float, float]] = []
    pattern = re.compile(
        r"black_start:(?P<start>[-+]?\d+(?:\.\d+)?)\s+"
        r"black_end:(?P<end>[-+]?\d+(?:\.\d+)?)\s+"
        r"black_duration:(?P<dur>[-+]?\d+(?:\.\d+)?)"
    )
    for m in pattern.finditer(stderr):
        intervals.append((float(m.group("start")), float(m.group("end")), float(m.group("dur"))))
    return intervals


def check_blank(video_path: Path, std_threshold: float = 2.0) -> GateResult:
    """Gate 2 (`blank_check`): FFmpeg blackdetect + OpenCV low-variance frame check."""
    if not video_path.exists():
        return GateResult(
            gate="blank_check",
            passed=False,
            findings=[QCFinding(gate="blank_check", message=f"Video file missing: {video_path}")],
        )

    findings: list[QCFinding] = []
    cmd = [
        "ffmpeg",
        "-v",
        "info",
        "-i",
        str(video_path),
        "-vf",
        "blackdetect=d=0.03:pix_th=0.10:pic_th=0.98",
        "-f",
        "null",
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    black_intervals = _parse_blackdetect(res.stderr)
    for b_start, b_end, b_dur in black_intervals:
        findings.append(
            QCFinding(
                gate="blank_check",
                message=f"FFmpeg blackdetect flagged black interval [{b_start:.3f}s, {b_end:.3f}s] ({b_dur:.3f}s).",
                timestamp=b_start,
                start=b_start,
                end=b_end,
                details={"source": "blackdetect", "duration": b_dur},
            )
        )

    cap = cv2.VideoCapture(str(video_path))
    low_var_frames: list[tuple[int, float, float]] = []
    total_checked = 0
    if cap.isOpened():
        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
            if fps <= 0:
                fps = 30.0
            idx = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                total_checked += 1
                spatial_std = max(float(np.std(frame[:, :, c])) for c in range(frame.shape[2]))
                if spatial_std < std_threshold:
                    low_var_frames.append((idx, idx / fps, spatial_std))
                idx += 1
        finally:
            cap.release()

    # Group contiguous low-variance frames into intervals to keep reports readable.
    if low_var_frames:
        grp_start = low_var_frames[0]
        grp_prev = low_var_frames[0]
        groups: list[tuple[int, int, float, float, float]] = []
        for item in low_var_frames[1:]:
            if item[0] == grp_prev[0] + 1:
                grp_prev = item
            else:
                groups.append((grp_start[0], grp_prev[0], grp_start[1], grp_prev[1], grp_start[2]))
                grp_start = item
                grp_prev = item
        groups.append((grp_start[0], grp_prev[0], grp_start[1], grp_prev[1], grp_start[2]))

        for f_s, f_e, t_s, t_e, min_std in groups:
            # Skip emitting redundant finding only if identical blackdetect already covers exact interval?
            # Keep explicit low-variance finding so both black and non-black blank frames are evidenced.
            findings.append(
                QCFinding(
                    gate="blank_check",
                    message=(
                        f"Low-variance blank frame(s) {f_s}..{f_e} ({t_s:.3f}s..{t_e:.3f}s, "
                        f"spatial_std={min_std:.3f} < {std_threshold})."
                    ),
                    timestamp=t_s,
                    start=t_s,
                    end=t_e,
                    frame_index=f_s,
                    details={"source": "variance", "spatial_std": round(min_std, 4), "frame_count": f_e - f_s + 1},
                )
            )

    return GateResult(
        gate="blank_check",
        passed=len(findings) == 0,
        findings=findings,
        metrics={
            "blackdetect_intervals": len(black_intervals),
            "low_variance_frames": len(low_var_frames),
            "frames_checked": total_checked,
        },
        summary="No blank/black frames detected." if not findings else f"Detected {len(findings)} blank/black defect(s).",
    )


def _extract_box(item: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Extract (x, y, width, height) from flexible box dictionaries."""
    target = item
    for nested_key in ("bbox", "box", "rect", "bounds"):
        if isinstance(item.get(nested_key), dict):
            target = item[nested_key]
            break

    if "x" in target and "y" in target:
        x = float(target["x"])
        y = float(target["y"])
        if "width" in target and "height" in target:
            return x, y, float(target["width"]), float(target["height"])
        if "w" in target and "h" in target:
            return x, y, float(target["w"]), float(target["h"])
    if all(k in target for k in ("left", "top", "right", "bottom")):
        left = float(target["left"])
        top = float(target["top"])
        right = float(target["right"])
        bottom = float(target["bottom"])
        return left, top, max(0.0, right - left), max(0.0, bottom - top)
    return None


def _iter_dom_elements(dom_manifest: dict[str, Any] | None) -> list[tuple[float | None, str, dict[str, Any]]]:
    """Collect (timestamp, collection_name, element_dict) from dom_manifest."""
    if not dom_manifest:
        return []
    out: list[tuple[float | None, str, dict[str, Any]]] = []
    for key in ("elements", "nodes", "boxes", "overlays", "overlay_boxes", "captions"):
        items = dom_manifest.get(key)
        if isinstance(items, list):
            for el in items:
                if isinstance(el, dict):
                    ts = el.get("timestamp", el.get("start"))
                    out.append((float(ts) if ts is not None else None, key, el))
    if isinstance(dom_manifest.get("caption_box"), dict):
        cap = dict(dom_manifest["caption_box"])
        cap.setdefault("id", "caption_box")
        cap.setdefault("role", "caption")
        out.append((None, "captions", cap))
    frames = dom_manifest.get("frames")
    if isinstance(frames, list):
        for fr in frames:
            if not isinstance(fr, dict):
                continue
            ts = fr.get("timestamp", fr.get("time"))
            ts_val = float(ts) if ts is not None else None
            for key in ("elements", "nodes", "boxes", "overlays", "overlay_boxes", "captions"):
                items = fr.get(key)
                if isinstance(items, list):
                    for el in items:
                        if isinstance(el, dict):
                            out.append((ts_val, key, el))
            if isinstance(fr.get("caption"), dict):
                out.append((ts_val, "captions", fr["caption"]))
    return out


def check_fit(
    hyperframes_check_report: dict[str, Any] | None = None,
    dom_manifest: dict[str, Any] | None = None,
) -> GateResult:
    """Gate 3 (`fit`): detect overflow, clipping, or truncation in hyperframes check & DOM manifest."""
    findings: list[QCFinding] = []

    if hyperframes_check_report is not None:
        if hyperframes_check_report.get("passed") is False or hyperframes_check_report.get("ok") is False:
            if not any(
                hyperframes_check_report.get(k)
                for k in ("errors", "findings", "issues", "violations", "checks")
            ):
                findings.append(
                    QCFinding(
                        gate="fit",
                        message="hyperframes check reported passed=False.",
                        details={"source": "hyperframes_check"},
                    )
                )
        if hyperframes_check_report.get("overflow") is True or hyperframes_check_report.get("clipped") is True:
            findings.append(
                QCFinding(
                    gate="fit",
                    message="hyperframes check reported top-level overflow/clipping.",
                    details={"source": "hyperframes_check"},
                )
            )
        for list_key in ("errors", "violations", "findings", "issues", "checks"):
            items = hyperframes_check_report.get(list_key)
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, str):
                    if list_key in ("errors", "violations") or any(
                        tok in item.lower() for tok in ("overflow", "clip", "truncat", "fit")
                    ):
                        findings.append(
                            QCFinding(gate="fit", message=f"hyperframes check: {item}", details={"source": list_key})
                        )
                    continue
                if not isinstance(item, dict):
                    continue
                sev = str(item.get("severity", item.get("level", ""))).lower()
                status = str(item.get("status", "")).lower()
                text_blob = " ".join(
                    str(item.get(k, "")) for k in ("type", "rule", "code", "message", "msg")
                ).lower()
                is_fit_defect = (
                    list_key in ("errors", "violations")
                    or item.get("clipped") is True
                    or item.get("overflow") is True
                    or sev in ("error", "fail", "fatal")
                    or status in ("fail", "failed", "error")
                    or any(tok in text_blob for tok in ("overflow", "clip", "truncat"))
                )
                if is_fit_defect and status not in ("pass", "passed", "ok") and item.get("passed") is not True:
                    ts = item.get("timestamp", item.get("time"))
                    findings.append(
                        QCFinding(
                            gate="fit",
                            message=str(item.get("message") or item.get("msg") or f"hyperframes fit defect: {item}"),
                            timestamp=float(ts) if ts is not None else None,
                            details={"source": "hyperframes_check", "item": item},
                        )
                    )

    canvas_w = float(dom_manifest.get("width", 0)) if dom_manifest else 0.0
    canvas_h = float(dom_manifest.get("height", 0)) if dom_manifest else 0.0
    dom_elements = _iter_dom_elements(dom_manifest)
    for ts, col_name, el in dom_elements:
        el_id = str(el.get("id") or el.get("name") or el.get("selector") or col_name)
        if el.get("clipped") is True or el.get("is_clipped") is True or el.get("overflow") is True or el.get("has_overflow") is True or el.get("truncated") is True:
            findings.append(
                QCFinding(
                    gate="fit",
                    message=f"DOM element '{el_id}' flagged with clipping/overflow.",
                    timestamp=ts,
                    details={"element": el_id, "collection": col_name},
                )
            )
            continue

        sw = el.get("scrollWidth", el.get("scroll_width"))
        cw = el.get("clientWidth", el.get("client_width"))
        sh = el.get("scrollHeight", el.get("scroll_height"))
        ch = el.get("clientHeight", el.get("client_height"))
        if sw is not None and cw is not None and float(sw) > float(cw) + 1.0:
            findings.append(
                QCFinding(
                    gate="fit",
                    message=f"DOM element '{el_id}' horizontal text overflow (scrollWidth={sw} > clientWidth={cw}).",
                    timestamp=ts,
                    details={"element": el_id, "scrollWidth": sw, "clientWidth": cw},
                )
            )
        if sh is not None and ch is not None and float(sh) > float(ch) + 1.0:
            findings.append(
                QCFinding(
                    gate="fit",
                    message=f"DOM element '{el_id}' vertical text overflow (scrollHeight={sh} > clientHeight={ch}).",
                    timestamp=ts,
                    details={"element": el_id, "scrollHeight": sh, "clientHeight": ch},
                )
            )

        box = _extract_box(el)
        parent = el.get("container") or el.get("parent")
        if box is not None and isinstance(parent, dict):
            p_box = _extract_box(parent)
            if p_box is not None:
                bx, by, bw, bh = box
                px, py, pw, ph = p_box
                if bx < px - 1.0 or by < py - 1.0 or bx + bw > px + pw + 1.0 or by + bh > py + ph + 1.0:
                    findings.append(
                        QCFinding(
                            gate="fit",
                            message=f"DOM element '{el_id}' overflows parent container bounds.",
                            timestamp=ts,
                            details={"element": el_id, "box": box, "parent": p_box},
                        )
                    )
        elif box is not None and canvas_w > 0 and canvas_h > 0:
            bx, by, bw, bh = box
            if bx < -1.0 or by < -1.0 or bx + bw > canvas_w + 1.0 or by + bh > canvas_h + 1.0:
                findings.append(
                    QCFinding(
                        gate="fit",
                        message=f"DOM element '{el_id}' exceeds canvas bounds {canvas_w}x{canvas_h}.",
                        timestamp=ts,
                        details={"element": el_id, "box": box},
                    )
                )

    return GateResult(
        gate="fit",
        passed=len(findings) == 0,
        findings=findings,
        metrics={"dom_elements_checked": len(dom_elements), "has_hyperframes_report": hyperframes_check_report is not None},
        summary="Fit check passed." if not findings else f"Detected {len(findings)} overflow/clipping defect(s).",
    )


def check_margins(
    dom_manifest: dict[str, Any] | None,
    width: int = 1920,
    height: int = 1080,
    margin_ratio: float = 0.05,
    tolerance_px: float = 1.0,
) -> GateResult:
    """Gate 4 (`margin_check`): verify overlays and captions obey Safe Zone margins."""
    if dom_manifest is None:
        return GateResult(
            gate="margin_check",
            passed=True,
            metrics={"checked_boxes": 0, "width": width, "height": height, "margin_ratio": margin_ratio},
            summary="No DOM manifest provided; 0 margin violations.",
        )

    margin_x = width * margin_ratio
    margin_y = height * margin_ratio
    safe_left = margin_x - tolerance_px
    safe_right = width - margin_x + tolerance_px
    safe_top = margin_y - tolerance_px
    safe_bottom = height - margin_y + tolerance_px

    findings: list[QCFinding] = []
    checked = 0
    for ts, col_name, el in _iter_dom_elements(dom_manifest):
        role = str(el.get("role", el.get("type", ""))).lower()
        if el.get("full_bleed") is True or el.get("ignore_safe_zone") is True or role in ("background", "canvas", "video", "root"):
            continue
        box = _extract_box(el)
        if box is None:
            continue
        checked += 1
        x, y, w, h = box
        if el.get("normalized") is True:
            x, y, w, h = x * width, y * height, w * width, h * height
        right = x + w
        bottom = y + h
        el_id = str(el.get("id") or el.get("name") or col_name)

        violations: list[str] = []
        if x < safe_left:
            violations.append(f"left={x:.1f} < {margin_x:.1f}")
        if right > safe_right:
            violations.append(f"right={right:.1f} > {width - margin_x:.1f}")
        if y < safe_top:
            violations.append(f"top={y:.1f} < {margin_y:.1f}")
        if bottom > safe_bottom:
            violations.append(f"bottom={bottom:.1f} > {height - margin_y:.1f}")

        if violations:
            findings.append(
                QCFinding(
                    gate="margin_check",
                    message=f"Safe Zone violation for '{el_id}': {', '.join(violations)}.",
                    timestamp=ts,
                    details={"element": el_id, "collection": col_name, "box": [x, y, w, h]},
                )
            )

    return GateResult(
        gate="margin_check",
        passed=len(findings) == 0,
        findings=findings,
        metrics={
            "checked_boxes": checked,
            "safe_zone": [margin_x, margin_y, width - margin_x, height - margin_y],
            "tolerance_px": tolerance_px,
        },
        summary="Safe Zone margins verified." if not findings else f"{len(findings)} Safe Zone violation(s).",
    )


def _find_haarcascade_path(filename: str) -> Path | None:
    candidates: list[Path] = []
    data_dir = getattr(getattr(cv2, "data", None), "haarcascades", None)
    if data_dir:
        candidates.append(Path(data_dir) / filename)
    for base in ("/usr/share/opencv5/haarcascades", "/usr/share/opencv4/haarcascades", "/usr/share/opencv/haarcascades"):
        candidates.append(Path(base) / filename)
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def _load_haar_cascades() -> tuple[Any | None, Any | None]:
    cascade_cls = getattr(cv2, "CascadeClassifier", None)
    if cascade_cls is None:
        return None, None
    face_path = _find_haarcascade_path("haarcascade_frontalface_default.xml")
    eye_path = _find_haarcascade_path("haarcascade_eye.xml")
    face_cascade = cascade_cls(str(face_path)) if face_path else None
    eye_cascade = cascade_cls(str(eye_path)) if eye_path else None
    if face_cascade is not None and face_cascade.empty():
        face_cascade = None
    if eye_cascade is not None and eye_cascade.empty():
        eye_cascade = None
    return face_cascade, eye_cascade


def _estimate_face_regions_from_bbox(
    fx: int,
    fy: int,
    fw: int,
    fh: int,
    eye_boxes: list[tuple[int, int, int, int]] | None = None,
) -> dict[str, tuple[float, float, float, float]]:
    """Derive upper eye band and lower mouth band from a detected face box."""
    if eye_boxes and len(eye_boxes) >= 1:
        ex1 = min(fx + ex for ex, _, _, _ in eye_boxes)
        ey1 = min(fy + ey for _, ey, _, _ in eye_boxes)
        ex2 = max(fx + ex + ew for ex, _, ew, _ in eye_boxes)
        ey2 = max(fy + ey + eh for _, ey, _, eh in eye_boxes)
        eyes = (float(ex1), float(ey1), float(max(1, ex2 - ex1)), float(max(1, ey2 - ey1)))
    else:
        eyes = (fx + 0.15 * fw, fy + 0.18 * fh, 0.70 * fw, 0.34 * fh)

    mouth = (fx + 0.22 * fw, fy + 0.62 * fh, 0.56 * fw, 0.28 * fh)
    return {
        "face": (float(fx), float(fy), float(fw), float(fh)),
        "eyes": eyes,
        "mouth": mouth,
    }


def _detect_faces_skin_and_features(frame_bgr: np.ndarray) -> list[dict[str, tuple[float, float, float, float]]]:
    """OpenCV 5.1 fallback face/eye/mouth detector using YCrCb skin segmentation + bilateral dark eyes + mouth contrast."""
    h_img, w_img = frame_bgr.shape[:2]
    ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    y_ch, cr_ch, cb_ch = ycrcb[:, :, 0], ycrcb[:, :, 1], ycrcb[:, :, 2]

    skin_mask = (
        (y_ch >= 60)
        & (cr_ch >= 137)
        & (cr_ch <= 178)
        & (cb_ch >= 77)
        & (cb_ch <= 126)
        & ((cr_ch.astype(np.int16) - cb_ch.astype(np.int16)) >= 18)
    ).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_w = max(36, int(0.04 * w_img))
    min_h = max(40, int(0.05 * h_img))
    detected: list[dict[str, tuple[float, float, float, float]]] = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < min_w or h < min_h or w > int(0.85 * w_img) or h > int(0.90 * h_img):
            continue
        fh = min(h, int(round(w * 1.35)))
        aspect = w / float(fh)
        if not (0.55 <= aspect <= 1.45):
            continue
        roi_mask = skin_mask[y : y + fh, x : x + w]
        fill_ratio = float(np.count_nonzero(roi_mask)) / float(w * fh)
        if fill_ratio < 0.45:
            continue

        roi_gray = gray[y : y + fh, x : x + w]
        roi_cr = cr_ch[y : y + fh, x : x + w]
        skin_pixels = roi_gray[roi_mask > 0]
        if skin_pixels.size < 100:
            continue
        skin_med = float(np.percentile(skin_pixels, 70))

        # Bilateral upper-half eye search
        y1_e, y2_e = int(0.15 * fh), int(0.54 * fh)
        left_band = roi_gray[y1_e:y2_e, int(0.12 * w) : int(0.48 * w)]
        right_band = roi_gray[y1_e:y2_e, int(0.52 * w) : int(0.88 * w)]
        if left_band.size == 0 or right_band.size == 0:
            continue

        left_dark = skin_med - float(np.percentile(left_band, 5))
        right_dark = skin_med - float(np.percentile(right_band, 5))
        if left_dark < 18.0 or right_dark < 18.0:
            continue

        ly_rel, lx_rel = np.unravel_index(int(np.argmin(left_band)), left_band.shape)
        ry_rel, rx_rel = np.unravel_index(int(np.argmin(right_band)), right_band.shape)
        lx = int(0.12 * w) + int(lx_rel)
        rx = int(0.52 * w) + int(rx_rel)
        ly = y1_e + int(ly_rel)
        ry = y1_e + int(ry_rel)
        if abs(ly - ry) > 0.16 * fh or (rx - lx) < 0.16 * w:
            continue

        # Lower-half mouth search
        mouth_gray = roi_gray[int(0.58 * fh) : int(0.88 * fh), int(0.22 * w) : int(0.78 * w)]
        mouth_cr = roi_cr[int(0.58 * fh) : int(0.88 * fh), int(0.22 * w) : int(0.78 * w)]
        if mouth_gray.size == 0:
            continue
        mouth_dark = skin_med - float(np.percentile(mouth_gray, 10))
        cheek_cr_med = float(np.median(roi_cr[roi_mask > 0]))
        mouth_cr_delta = float(np.percentile(mouth_cr, 95)) - cheek_cr_med
        if mouth_dark < 12.0 and mouth_cr_delta < 6.0:
            continue

        pad = max(4, int(0.08 * w))
        eye_boxes = [
            (max(0, lx - pad), max(0, ly - pad), 2 * pad, 2 * pad),
            (max(0, rx - pad), max(0, ry - pad), 2 * pad, 2 * pad),
        ]
        detected.append(_estimate_face_regions_from_bbox(x, y, w, fh, eye_boxes=eye_boxes))

    return detected


def _detect_faces_and_regions(
    frame_bgr: np.ndarray,
    face_cascade: Any | None,
    eye_cascade: Any | None,
) -> tuple[list[dict[str, tuple[float, float, float, float]]], str]:
    """Detect face + eyes + mouth boxes via Haar cascade when available, else OpenCV YCrCb/feature fallback."""
    if face_cascade is not None:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        if len(faces) > 0:
            results: list[dict[str, tuple[float, float, float, float]]] = []
            for fx, fy, fw, fh in faces:
                eye_boxes: list[tuple[int, int, int, int]] = []
                if eye_cascade is not None:
                    roi = gray[fy : fy + int(0.6 * fh), fx : fx + fw]
                    eyes = eye_cascade.detectMultiScale(roi, scaleFactor=1.1, minNeighbors=3, minSize=(12, 12))
                    eye_boxes = [(int(ex), int(ey), int(ew), int(eh)) for ex, ey, ew, eh in eyes]
                results.append(_estimate_face_regions_from_bbox(int(fx), int(fy), int(fw), int(fh), eye_boxes=eye_boxes))
            return results, "haar_cascade"

    return _detect_faces_skin_and_features(frame_bgr), "opencv_skin_features"


def _boxes_overlap_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix1 = max(ax, bx)
    iy1 = max(ay, by)
    ix2 = min(ax + aw, bx + bw)
    iy2 = min(ay + ah, by + bh)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    return (ix2 - ix1) * (iy2 - iy1)


def check_eyes_mouth(
    video_path: Path,
    overlay_boxes: list[dict[str, Any]],
    waivers: list[QCWaiver] | None = None,
) -> GateResult:
    """Gate 5 (`eyes_mouth_check`): verify overlays/captions never cover speaker eyes or mouth without a waiver."""
    if not video_path.exists():
        return GateResult(
            gate="eyes_mouth_check",
            passed=False,
            findings=[QCFinding(gate="eyes_mouth_check", message=f"Video file missing: {video_path}")],
        )

    active_overlays = [
        ov for ov in overlay_boxes
        if isinstance(ov, dict)
        and ov.get("active", True) is not False
        and ov.get("enabled", True) is not False
        and ov.get("full_bleed") is not True
        and str(ov.get("role", ov.get("type", ""))).lower() not in ("background", "canvas", "video", "root")
        and _extract_box(ov) is not None
    ]
    if not active_overlays:
        return GateResult(
            gate="eyes_mouth_check",
            passed=True,
            metrics={"sampled_frames": 0, "overlays": 0, "faces_detected": 0},
            summary="No active overlay boxes to check.",
        )

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return GateResult(
            gate="eyes_mouth_check",
            passed=False,
            findings=[QCFinding(gate="eyes_mouth_check", message=f"Failed to open video: {video_path}")],
        )

    face_cascade, eye_cascade = _load_haar_cascades()
    findings: list[QCFinding] = []
    waived_findings: list[QCFinding] = []
    detector_used = "haar_cascade" if face_cascade is not None else "opencv_skin_features"
    faces_detected_total = 0

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if fps <= 0:
            fps = 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
        duration = (frame_count / fps) if frame_count > 0 else 10.0

        # Build deduplicated frame indices covering all active overlay intervals
        sample_map: dict[int, list[tuple[str, tuple[float, float, float, float]]]] = {}
        for idx, ov in enumerate(active_overlays):
            raw_box = _extract_box(ov)
            assert raw_box is not None
            bx, by, bw, bh = raw_box
            if ov.get("normalized") is True:
                bx, by, bw, bh = bx * frame_w, by * frame_h, bw * frame_w, bh * frame_h
            ov_box = (bx, by, bw, bh)
            ov_id = str(ov.get("id") or ov.get("name") or ov.get("type") or f"overlay_{idx}")

            ov_start = float(ov.get("start", ov.get("start_sec", ov.get("timestamp", 0.0))))
            if "end" in ov or "end_sec" in ov:
                ov_end = float(ov.get("end", ov.get("end_sec", duration)))
            elif "duration" in ov:
                ov_end = ov_start + float(ov["duration"])
            else:
                ov_end = duration

            ov_start = max(0.0, min(ov_start, max(0.0, duration - 1.0 / fps)))
            ov_end = max(ov_start, min(ov_end, duration))

            ts_points = [ov_start, 0.5 * (ov_start + ov_end), max(ov_start, ov_end - 1.0 / fps)]
            t = ov_start + 0.5
            while t < ov_end:
                ts_points.append(t)
                t += 0.5

            for ts in ts_points:
                f_idx = int(round(ts * fps))
                if frame_count > 0:
                    f_idx = max(0, min(frame_count - 1, f_idx))
                sample_map.setdefault(f_idx, []).append((ov_id, ov_box))

        for f_idx in sorted(sample_map):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ok, frame = cap.read()
            if not ok:
                continue
            ts = f_idx / fps
            faces, det_name = _detect_faces_and_regions(frame, face_cascade, eye_cascade)
            detector_used = det_name
            if not faces:
                continue
            faces_detected_total += len(faces)

            for ov_id, ov_box in sample_map[f_idx]:
                for face_regions in faces:
                    eyes_overlap = _boxes_overlap_area(ov_box, face_regions["eyes"])
                    mouth_overlap = _boxes_overlap_area(ov_box, face_regions["mouth"])
                    if eyes_overlap <= 0.0 and mouth_overlap <= 0.0:
                        continue
                    part = "eyes and mouth" if (eyes_overlap > 0 and mouth_overlap > 0) else ("eyes" if eyes_overlap > 0 else "mouth")
                    waiver = _find_matching_waiver("eyes_mouth_check", ts, waivers)
                    finding = QCFinding(
                        gate="eyes_mouth_check",
                        severity="info" if waiver else "error",
                        message=f"Overlay '{ov_id}' overlaps speaker {part} at {ts:.3f}s.",
                        timestamp=ts,
                        frame_index=f_idx,
                        details={
                            "overlay": ov_id,
                            "overlay_box": list(ov_box),
                            "eyes_box": list(face_regions["eyes"]),
                            "mouth_box": list(face_regions["mouth"]),
                        },
                        waived=waiver is not None,
                        waiver_reason=waiver.reason if waiver else None,
                    )
                    if waiver is not None:
                        waived_findings.append(finding)
                    else:
                        findings.append(finding)
    finally:
        cap.release()

    return GateResult(
        gate="eyes_mouth_check",
        passed=len(findings) == 0,
        findings=findings,
        waived_findings=waived_findings,
        metrics={
            "sampled_frames": len(sample_map),
            "overlays": len(active_overlays),
            "faces_detected": faces_detected_total,
            "detector": detector_used,
        },
        summary=(
            "No unwaived eye/mouth overlaps detected."
            if not findings
            else f"Detected {len(findings)} unwaived eye/mouth overlay overlap(s)."
        ),
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_stale(run_json_path: Path | None) -> GateResult:
    """Gate 6 (`stale_check`): verify live SHA-256 of every dependency recorded in run.json."""
    if run_json_path is None:
        return GateResult(
            gate="stale_check",
            passed=True,
            summary="No run.json provided; stale check skipped.",
        )
    if not run_json_path.exists():
        return GateResult(
            gate="stale_check",
            passed=False,
            findings=[QCFinding(gate="stale_check", message=f"run.json not found: {run_json_path}")],
        )

    try:
        data = json.loads(run_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return GateResult(
            gate="stale_check",
            passed=False,
            findings=[QCFinding(gate="stale_check", message=f"Failed to parse run.json: {exc}")],
        )

    input_hashes = data.get("input_hashes")
    if not isinstance(input_hashes, dict):
        return GateResult(
            gate="stale_check",
            passed=False,
            findings=[QCFinding(gate="stale_check", message="run.json missing dict 'input_hashes'.")],
        )

    findings: list[QCFinding] = []
    mismatches = 0
    missing = 0
    checked_keys: list[str] = []

    for key, entry in input_hashes.items():
        checked_keys.append(str(key))
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            findings.append(
                QCFinding(gate="stale_check", message=f"Malformed input_hashes entry for '{key}'.")
            )
            continue

        raw_path = Path(str(entry["path"]))
        candidate = raw_path if raw_path.is_absolute() else (run_json_path.parent / raw_path)
        if not candidate.exists() and not raw_path.is_absolute():
            candidate = raw_path
        if not candidate.exists() or not candidate.is_file():
            missing += 1
            findings.append(
                QCFinding(
                    gate="stale_check",
                    message=f"Missing dependency '{key}': {entry['path']}",
                    details={"key": key, "path": str(entry["path"])},
                )
            )
            continue

        actual_sha = _sha256_file(candidate)
        expected_sha = str(entry["sha256"])
        if actual_sha.lower() != expected_sha.lower():
            mismatches += 1
            findings.append(
                QCFinding(
                    gate="stale_check",
                    message=(
                        f"Stale dependency '{key}' ({candidate}): "
                        f"expected sha256 {expected_sha[:12]}..., got {actual_sha[:12]}..."
                    ),
                    details={"key": key, "path": str(candidate), "expected": expected_sha, "actual": actual_sha},
                )
            )

    return GateResult(
        gate="stale_check",
        passed=len(findings) == 0,
        findings=findings,
        metrics={"checked_keys": checked_keys, "mismatches": mismatches, "missing": missing},
        summary="All dependency SHA-256 hashes match." if not findings else f"{len(findings)} stale/missing dependency issue(s).",
    )


def _has_terminal_punctuation(text: str) -> bool:
    stripped = text.strip().rstrip(_TRAILING_QUOTE_CHARS)
    return bool(stripped) and stripped[-1] in TERMINAL_PUNCTUATION


def check_hold_sentence(
    kept_segments: list[KeepSegment],
    transcript_bundle: TranscriptBundle,
) -> GateResult:
    """Gate 7 (`hold_sentence`): verify kept segment edges never slice mid-word or mid-sentence."""
    words: list[WordTiming] = []
    for t_seg in transcript_bundle.segments:
        words.extend(t_seg.words)
    words.sort(key=lambda w: (w.start, w.end))

    findings: list[QCFinding] = []
    if not words:
        # Fallback to segment-level bounds if word timings were omitted
        t_segs = sorted(transcript_bundle.segments, key=lambda s: (s.start, s.end))
        for k_seg in kept_segments:
            for ts_seg in t_segs:
                if ts_seg.start + 0.02 < k_seg.end < ts_seg.end - 0.02 and not _has_terminal_punctuation(ts_seg.text):
                    findings.append(
                        QCFinding(
                            gate="hold_sentence",
                            message=f"Segment '{k_seg.id}' end ({k_seg.end:.3f}s) cuts inside transcript segment {ts_seg.id}.",
                            timestamp=k_seg.end,
                        )
                    )
        return GateResult(
            gate="hold_sentence",
            passed=len(findings) == 0,
            findings=findings,
            metrics={"segments_checked": len(kept_segments), "words_checked": 0},
            summary="Hold-sentence check passed." if not findings else f"{len(findings)} mid-sentence cut(s).",
        )

    ordered_kept = sorted(kept_segments, key=lambda s: (s.start, s.end))
    for i, seg in enumerate(ordered_kept):
        # 1. Strict mid-word slice check on both start and end
        for edge_name, edge in (("start", seg.start), ("end", seg.end)):
            for w in words:
                if w.start + 0.02 < edge < w.end - 0.02:
                    findings.append(
                        QCFinding(
                            gate="hold_sentence",
                            message=(
                                f"Segment '{seg.id}' {edge_name} ({edge:.3f}s) slices mid-word "
                                f"inside '{w.word}' [{w.start:.3f}s, {w.end:.3f}s]."
                            ),
                            timestamp=edge,
                            details={"segment_id": seg.id, "edge": edge_name, "word": w.word},
                        )
                    )

        # 2. Mid-sentence out-point check
        next_kept = ordered_kept[i + 1] if i + 1 < len(ordered_kept) else None
        contiguous_next = next_kept is not None and abs(next_kept.start - seg.end) <= 0.02
        kept_words = [w for w in words if seg.start - 0.02 <= (w.start + w.end) / 2.0 <= seg.end + 0.02]
        if kept_words and not contiguous_next:
            last_w = kept_words[-1]
            trailing_words = [w for w in words if w.start >= seg.end - 0.02 and w is not last_w]
            if trailing_words:
                next_w = trailing_words[0]
                gap = next_w.start - last_w.end
                if not _has_terminal_punctuation(last_w.word) and gap < 0.25:
                    findings.append(
                        QCFinding(
                            gate="hold_sentence",
                            message=(
                                f"Segment '{seg.id}' cuts mid-sentence at {seg.end:.3f}s after '{last_w.word}' "
                                f"before '{next_w.word}' (no terminal punctuation and pause gap {gap:.3f}s < 0.25s)."
                            ),
                            timestamp=seg.end,
                            details={"segment_id": seg.id, "last_word": last_w.word, "next_word": next_w.word, "gap_sec": round(gap, 3)},
                        )
                    )

        # 3. Mid-sentence in-point check
        prev_kept = ordered_kept[i - 1] if i > 0 else None
        contiguous_prev = prev_kept is not None and abs(seg.start - prev_kept.end) <= 0.02
        if kept_words and not contiguous_prev:
            first_w = kept_words[0]
            prior_words = [w for w in words if w.end <= seg.start + 0.02 and w is not first_w]
            if prior_words:
                prev_w = prior_words[-1]
                gap = first_w.start - prev_w.end
                if not _has_terminal_punctuation(prev_w.word) and gap < 0.25:
                    findings.append(
                        QCFinding(
                            gate="hold_sentence",
                            message=(
                                f"Segment '{seg.id}' starts mid-sentence at {seg.start:.3f}s before '{first_w.word}' "
                                f"following '{prev_w.word}' (no terminal punctuation and pause gap {gap:.3f}s < 0.25s)."
                            ),
                            timestamp=seg.start,
                            details={"segment_id": seg.id, "prev_word": prev_w.word, "first_word": first_w.word, "gap_sec": round(gap, 3)},
                        )
                    )

    return GateResult(
        gate="hold_sentence",
        passed=len(findings) == 0,
        findings=findings,
        metrics={"segments_checked": len(kept_segments), "words_checked": len(words)},
        summary="All cut boundaries honor word and sentence holds." if not findings else f"{len(findings)} hold-sentence violation(s).",
    )


def _extract_caption_boxes(dom_manifest: dict[str, Any] | None) -> list[tuple[float | None, dict[str, Any], tuple[float, float, float, float]]]:
    if not dom_manifest:
        return []
    out: list[tuple[float | None, dict[str, Any], tuple[float, float, float, float]]] = []
    for ts, col_name, el in _iter_dom_elements(dom_manifest):
        role = str(el.get("role", el.get("type", ""))).lower()
        if col_name != "captions" and "caption" not in role:
            continue
        box = _extract_box(el)
        if box is not None:
            out.append((ts, el, box))
    return out


def check_stability(
    video_path: Path,
    dom_manifest: dict[str, Any] | None = None,
    plate_windows: list[tuple[float, float]] | None = None,
    max_anchor_drift_px: float = 2.0,
) -> GateResult:
    """Gate 8 (`stability`): verify fixed caption anchor (<= 2px drift) and static window jitter."""
    findings: list[QCFinding] = []

    caption_items = _extract_caption_boxes(dom_manifest)
    h_drift = 0.0
    v_drift = 0.0
    if len(caption_items) >= 2:
        has_explicit_anchor = all(
            ("anchor_x" in el or "anchorX" in el) and ("anchor_y" in el or "anchorY" in el)
            for _, el, _ in caption_items
        )
        if has_explicit_anchor:
            axs = [float(el.get("anchor_x", el.get("anchorX"))) for _, el, _ in caption_items]
            ays = [float(el.get("anchor_y", el.get("anchorY"))) for _, el, _ in caption_items]
            h_drift = max(axs) - min(axs)
            v_drift = max(ays) - min(ays)
        else:
            xs = [b[0] for _, _, b in caption_items]
            cxs = [b[0] + 0.5 * b[2] for _, _, b in caption_items]
            rights = [b[0] + b[2] for _, _, b in caption_items]
            ys = [b[1] for _, _, b in caption_items]
            cys = [b[1] + 0.5 * b[3] for _, _, b in caption_items]
            bottoms = [b[1] + b[3] for _, _, b in caption_items]
            h_drift = min(max(xs) - min(xs), max(cxs) - min(cxs), max(rights) - min(rights))
            v_drift = min(max(ys) - min(ys), max(cys) - min(cys), max(bottoms) - min(bottoms))

        if h_drift > max_anchor_drift_px or v_drift > max_anchor_drift_px:
            findings.append(
                QCFinding(
                    gate="stability",
                    message=(
                        f"Caption anchor drifted across beats (h_drift={h_drift:.2f}px, "
                        f"v_drift={v_drift:.2f}px > {max_anchor_drift_px:.1f}px)."
                    ),
                    details={"h_drift_px": round(h_drift, 2), "v_drift_px": round(v_drift, 2)},
                )
            )

    windows = list(plate_windows or [])
    if not windows and dom_manifest:
        for key in ("plate_windows", "static_windows"):
            raw = dom_manifest.get(key)
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        windows.append((float(item[0]), float(item[1])))
                    elif isinstance(item, dict) and "start" in item and "end" in item:
                        windows.append((float(item["start"]), float(item["end"])))

    jitter_windows_checked = 0
    if windows and video_path.exists():
        cap = cv2.VideoCapture(str(video_path))
        if cap.isOpened():
            try:
                fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
                if fps <= 0:
                    fps = 30.0
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                for w_start, w_end in windows:
                    if w_end <= w_start:
                        continue
                    jitter_windows_checked += 1
                    f_start = max(0, int(round(w_start * fps)))
                    f_end = int(round(w_end * fps))
                    if total_frames > 0:
                        f_end = min(total_frames - 1, f_end)
                    if f_end - f_start < 2:
                        continue

                    cap.set(cv2.CAP_PROP_POS_FRAMES, f_start)
                    prev_gray: np.ndarray | None = None
                    hann: np.ndarray | None = None
                    diffs: list[float] = []
                    shifts: list[float] = []
                    for _ in range(f_start, f_end + 1):
                        ok, frame = cap.read()
                        if not ok:
                            break
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
                        if hann is None:
                            hann = cv2.createHanningWindow((gray.shape[1], gray.shape[0]), cv2.CV_32F)
                        if prev_gray is not None:
                            mad = float(np.mean(np.abs(gray - prev_gray)))
                            diffs.append(mad)
                            if mad > 0.5 and float(np.std(gray)) >= 5.0:
                                (dx, dy), _ = cv2.phaseCorrelate(prev_gray, gray, window=hann)
                                shifts.append(float(np.hypot(dx, dy)))
                        prev_gray = gray

                    if diffs:
                        p90_diff = float(np.percentile(diffs, 90))
                        max_shift = max(shifts) if shifts else 0.0
                        if p90_diff > 2.0 or max_shift >= 0.75:
                            findings.append(
                                QCFinding(
                                    gate="stability",
                                    message=(
                                        f"Unintended pixel jitter in static window [{w_start:.2f}s, {w_end:.2f}s] "
                                        f"(p90_diff={p90_diff:.2f}, max_shift={max_shift:.2f}px)."
                                    ),
                                    start=w_start,
                                    end=w_end,
                                    details={"p90_diff": round(p90_diff, 3), "max_shift_px": round(max_shift, 3)},
                                )
                            )
            finally:
                cap.release()

    return GateResult(
        gate="stability",
        passed=len(findings) == 0,
        findings=findings,
        metrics={
            "caption_boxes_checked": len(caption_items),
            "h_drift_px": round(h_drift, 2),
            "v_drift_px": round(v_drift, 2),
            "plate_windows_checked": jitter_windows_checked,
        },
        summary="Caption anchor and static plate stability verified." if not findings else f"{len(findings)} stability defect(s).",
    )


def check_decode(video_path: Path) -> GateResult:
    """Delivery Check 1 (`decode`): FFmpeg decode integrity + ffprobe stream/audio/VFR check."""
    if not video_path.exists():
        return GateResult(
            gate="decode",
            passed=False,
            findings=[QCFinding(gate="decode", message=f"Video file missing: {video_path}")],
        )

    findings: list[QCFinding] = []
    metrics: dict[str, Any] = {}
    try:
        data = _ffprobe_info(video_path)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return GateResult(
            gate="decode",
            passed=False,
            findings=[QCFinding(gate="decode", message=f"ffprobe failed: {exc}")],
        )

    streams = data.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if v_stream is None:
        findings.append(QCFinding(gate="decode", message="Missing video stream in container."))
    if a_stream is None:
        findings.append(QCFinding(gate="decode", message="Missing audio stream in final delivery container."))

    if v_stream is not None:
        r_fps = _parse_rate(v_stream.get("r_frame_rate"))
        avg_fps = _parse_rate(v_stream.get("avg_frame_rate"))
        duration = float(data.get("format", {}).get("duration") or v_stream.get("duration") or 0.0)
        metrics.update(
            {
                "width": int(v_stream.get("width", 0)),
                "height": int(v_stream.get("height", 0)),
                "r_fps": round(r_fps, 4),
                "avg_fps": round(avg_fps, 4),
                "duration": round(duration, 4),
                "video_codec": v_stream.get("codec_name"),
            }
        )
        if duration <= 0.0:
            findings.append(QCFinding(gate="decode", message="Container duration <= 0.0s."))
        if r_fps > 0 and avg_fps > 0 and abs(r_fps - avg_fps) / r_fps > 0.02:
            findings.append(
                QCFinding(
                    gate="decode",
                    message=f"VFR drift detected: r_frame_rate={r_fps:.3f} vs avg_frame_rate={avg_fps:.3f}.",
                    details={"r_fps": r_fps, "avg_fps": avg_fps},
                )
            )

    if a_stream is not None:
        metrics.update(
            {
                "audio_codec": a_stream.get("codec_name"),
                "sample_rate": int(a_stream.get("sample_rate", 0) or 0),
                "channels": int(a_stream.get("channels", 0) or 0),
            }
        )

    dec = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video_path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    if dec.returncode != 0 or dec.stderr.strip():
        findings.append(
            QCFinding(
                gate="decode",
                message=f"FFmpeg decode errors: {dec.stderr.strip() or f'exit {dec.returncode}'}",
            )
        )

    return GateResult(
        gate="decode",
        passed=len(findings) == 0,
        findings=findings,
        metrics=metrics,
        summary="Full decode and CFR/stream check passed." if not findings else f"Decode check failed ({len(findings)} issue(s)).",
    )


def _rms_dbfs(samples: np.ndarray) -> float:
    if samples.size == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    return 20.0 * float(np.log10(max(rms, 1e-9)))


def check_tail(
    video_path: Path,
    cut_timestamps: list[float],
    max_tail_dbfs: float = -18.0,
) -> GateResult:
    """Delivery Check 2 (`tail_check`): audit final 30ms before cuts for abrupt un-faded Consonant Tail truncation."""
    if not video_path.exists():
        return GateResult(
            gate="tail_check",
            passed=False,
            findings=[QCFinding(gate="tail_check", message=f"Video file missing: {video_path}")],
        )
    if not cut_timestamps:
        return GateResult(
            gate="tail_check",
            passed=True,
            metrics={"cuts_checked": 0},
            summary="No cut timestamps provided; tail check skipped.",
        )

    sample_rate = 48000
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "tail_audit.wav"
        res = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(video_path),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(sample_rate),
                "-ac",
                "1",
                str(wav_path),
            ],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0 or not wav_path.exists():
            return GateResult(
                gate="tail_check",
                passed=False,
                findings=[QCFinding(gate="tail_check", message=f"Failed to extract audio for tail check: {res.stderr.strip()}")],
            )
        with wave.open(str(wav_path), "rb") as wf:
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

    findings: list[QCFinding] = []
    tail_metrics: list[dict[str, float]] = []
    n_30ms = int(0.030 * sample_rate)
    n_5ms = int(0.005 * sample_rate)

    for cut_ts in cut_timestamps:
        if cut_ts <= 0.03:
            continue
        end_idx = min(len(pcm), int(round(cut_ts * sample_rate)))
        if end_idx < n_30ms:
            continue
        tail_30 = pcm[end_idx - n_30ms : end_idx]
        end_5 = pcm[end_idx - n_5ms : end_idx]
        prev_30 = pcm[max(0, end_idx - 2 * n_30ms) : end_idx - n_30ms]

        tail_db = _rms_dbfs(tail_30)
        end5_db = _rms_dbfs(end_5)
        prev_db = _rms_dbfs(prev_30) if prev_30.size > 0 else tail_db
        decay_db = prev_db - end5_db
        tail_metrics.append({"cut_ts": cut_ts, "tail_30ms_dbfs": round(tail_db, 2), "end_5ms_dbfs": round(end5_db, 2)})

        # Flag abrupt high-energy truncation where both 30ms tail exceeds threshold and final 5ms lacks decay
        has_clean_fade = decay_db >= 10.0 and end5_db <= max_tail_dbfs - 4.0
        if tail_db > max_tail_dbfs and not has_clean_fade and end5_db > max_tail_dbfs - 3.0:
            findings.append(
                QCFinding(
                    gate="tail_check",
                    message=(
                        f"Abrupt high-energy cut at {cut_ts:.3f}s (30ms tail={tail_db:.1f} dBFS, "
                        f"final 5ms={end5_db:.1f} dBFS > limit {max_tail_dbfs:.1f} dBFS without decay)."
                    ),
                    timestamp=cut_ts,
                    details={"tail_30ms_dbfs": round(tail_db, 2), "end_5ms_dbfs": round(end5_db, 2), "decay_db": round(decay_db, 2)},
                )
            )

    return GateResult(
        gate="tail_check",
        passed=len(findings) == 0,
        findings=findings,
        metrics={"cuts_checked": len(tail_metrics), "max_tail_dbfs": max_tail_dbfs, "tails": tail_metrics},
        summary="Consonant Tail decay verified." if not findings else f"{len(findings)} abrupt tail truncation(s).",
    )


def _parse_freezedetect(stderr: str, total_duration: float) -> list[tuple[float, float]]:
    starts: list[float] = []
    intervals: list[tuple[float, float]] = []
    re_start = re.compile(r"freeze_start:\s*([-+]?\d+(?:\.\d+)?)")
    re_end = re.compile(r"freeze_end:\s*([-+]?\d+(?:\.\d+)?)")
    for line in stderr.splitlines():
        m_s = re_start.search(line)
        if m_s:
            starts.append(float(m_s.group(1)))
            continue
        m_e = re_end.search(line)
        if m_e and starts:
            s = starts.pop(0)
            intervals.append((s, float(m_e.group(1))))
    for s in starts:
        intervals.append((s, max(s, total_duration)))
    return intervals


def check_freeze(video_path: Path, waivers: list[QCWaiver] | None = None) -> GateResult:
    """Delivery Check 3 (`freeze_check`): FFmpeg freezedetect=n=-60dB:d=1.5 honoring freeze_check waivers."""
    if not video_path.exists():
        return GateResult(
            gate="freeze_check",
            passed=False,
            findings=[QCFinding(gate="freeze_check", message=f"Video file missing: {video_path}")],
        )

    try:
        _, _, _, duration, _ = _video_props(video_path)
    except Exception:
        duration = 0.0

    res = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(video_path), "-vf", "freezedetect=n=-60dB:d=1.5", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    intervals = _parse_freezedetect(res.stderr, duration)
    findings: list[QCFinding] = []
    waived_findings: list[QCFinding] = []

    for f_start, f_end in intervals:
        waiver = _interval_covered_by_waivers("freeze_check", f_start, f_end, waivers)
        finding = QCFinding(
            gate="freeze_check",
            severity="info" if waiver else "error",
            message=f"Frozen video interval [{f_start:.3f}s, {f_end:.3f}s] ({f_end - f_start:.2f}s).",
            timestamp=f_start,
            start=f_start,
            end=f_end,
            details={"duration": round(f_end - f_start, 3)},
            waived=waiver is not None,
            waiver_reason=waiver.reason if waiver else None,
        )
        if waiver is not None:
            waived_findings.append(finding)
        else:
            findings.append(finding)

    return GateResult(
        gate="freeze_check",
        passed=len(findings) == 0,
        findings=findings,
        waived_findings=waived_findings,
        metrics={"freeze_intervals": len(intervals), "waived_intervals": len(waived_findings)},
        summary="No unwaived freeze intervals detected." if not findings else f"{len(findings)} unwaived freeze interval(s).",
    )


_SRT_TIME_RE = re.compile(
    r"^(?P<h1>\d{2}):(?P<m1>\d{2}):(?P<s1>\d{2}),(?P<ms1>\d{3})\s*-->\s*"
    r"(?P<h2>\d{2}):(?P<m2>\d{2}):(?P<s2>\d{2}),(?P<ms2>\d{3})$"
)


def _srt_ts_to_sec(h: str, m: str, s: str, ms: str) -> float | None:
    hi, mi, si, msi = int(h), int(m), int(s), int(ms)
    if mi >= 60 or si >= 60:
        return None
    return hi * 3600.0 + mi * 60.0 + si + msi / 1000.0


def check_captions(
    srt_path: Path | None,
    duration_sec: float,
    max_chars_per_line: int = 48,
) -> GateResult:
    """Delivery Check 4 (`captions`): validate SRT structure, monotonic zero-based timings, and line length."""
    if srt_path is None:
        return GateResult(
            gate="captions",
            passed=True,
            summary="No SRT path provided; captions check skipped.",
        )
    if not srt_path.exists():
        return GateResult(
            gate="captions",
            passed=False,
            findings=[QCFinding(gate="captions", message=f"SRT file not found: {srt_path}")],
        )

    raw = srt_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    if not raw:
        return GateResult(
            gate="captions",
            passed=False,
            findings=[QCFinding(gate="captions", message=f"SRT file is empty: {srt_path}")],
        )

    blocks = [b.strip() for b in re.split(r"\n{2,}", raw) if b.strip()]
    findings: list[QCFinding] = []
    prev_end = -1.0
    cue_count = 0

    for expected_idx, block in enumerate(blocks, start=1):
        lines = block.split("\n")
        if len(lines) < 3:
            findings.append(
                QCFinding(gate="captions", message=f"Malformed SRT block {expected_idx}: fewer than 3 lines.")
            )
            continue
        try:
            block_num = int(lines[0].strip())
        except ValueError:
            findings.append(
                QCFinding(gate="captions", message=f"SRT block {expected_idx} has non-integer index '{lines[0]}'.")
            )
            continue
        if block_num != expected_idx:
            findings.append(
                QCFinding(
                    gate="captions",
                    message=f"SRT cue index out of sequence: expected {expected_idx}, got {block_num}.",
                )
            )

        m = _SRT_TIME_RE.match(lines[1].strip())
        if not m:
            findings.append(
                QCFinding(gate="captions", message=f"Invalid SRT timestamp line in cue {expected_idx}: '{lines[1]}'.")
            )
            continue

        start_s = _srt_ts_to_sec(m.group("h1"), m.group("m1"), m.group("s1"), m.group("ms1"))
        end_s = _srt_ts_to_sec(m.group("h2"), m.group("m2"), m.group("s2"), m.group("ms2"))
        if start_s is None or end_s is None:
            findings.append(
                QCFinding(gate="captions", message=f"Out-of-range MM/SS in cue {expected_idx}: '{lines[1]}'.")
            )
            continue

        if start_s < 0.0 or end_s <= start_s:
            findings.append(
                QCFinding(
                    gate="captions",
                    message=f"Invalid cue {expected_idx} duration [{start_s:.3f}s, {end_s:.3f}s].",
                    start=start_s,
                    end=end_s,
                )
            )
        if end_s > duration_sec + 0.05:
            findings.append(
                QCFinding(
                    gate="captions",
                    message=f"Cue {expected_idx} end ({end_s:.3f}s) exceeds video duration ({duration_sec:.3f}s).",
                    timestamp=end_s,
                )
            )
        if prev_end >= 0.0 and start_s < prev_end - 0.001:
            findings.append(
                QCFinding(
                    gate="captions",
                    message=f"Overlapping/non-monotonic cue {expected_idx}: starts at {start_s:.3f}s < prev end {prev_end:.3f}s.",
                    timestamp=start_s,
                )
            )
        prev_end = max(prev_end, end_s)

        text_lines = [ln.rstrip() for ln in lines[2:]]
        if not any(ln.strip() for ln in text_lines):
            findings.append(QCFinding(gate="captions", message=f"Cue {expected_idx} has empty text.", timestamp=start_s))
        for ln_no, ln in enumerate(text_lines, start=1):
            if len(ln) > max_chars_per_line:
                findings.append(
                    QCFinding(
                        gate="captions",
                        message=f"Cue {expected_idx} line {ln_no} length {len(ln)} > {max_chars_per_line} chars: '{ln}'.",
                        timestamp=start_s,
                    )
                )
        cue_count += 1

    return GateResult(
        gate="captions",
        passed=len(findings) == 0,
        findings=findings,
        metrics={"cues": cue_count, "duration_sec": duration_sec, "max_chars_per_line": max_chars_per_line},
        summary="SRT captions verified." if not findings else f"{len(findings)} SRT caption defect(s).",
    )


def _parse_ebur128(stderr: str) -> tuple[float | None, float | None, float | None]:
    lufs_matches = re.findall(r"Integrated loudness:\s*\n\s*I:\s*([-+]?\d+(?:\.\d+)?)\s*LUFS", stderr)
    lra_matches = re.findall(r"Loudness range:\s*\n\s*LRA:\s*([-+]?\d+(?:\.\d+)?)\s*LU", stderr)
    tp_matches = re.findall(r"True peak:\s*\n\s*Peak:\s*([-+]?\d+(?:\.\d+)?)\s*(?:dBFS|dBTP)", stderr)
    integrated = float(lufs_matches[-1]) if lufs_matches else None
    lra = float(lra_matches[-1]) if lra_matches else None
    true_peak = float(tp_matches[-1]) if tp_matches else None
    return integrated, true_peak, lra


def check_loudness(
    video_path: Path,
    target_lufs: float = -14.0,
    max_true_peak: float = -1.0,
) -> GateResult:
    """Delivery Check 5 (`loudness`): verify integrated LUFS (target +/- 1.5) and true peak via FFmpeg ebur128."""
    if not video_path.exists():
        return GateResult(
            gate="loudness",
            passed=False,
            findings=[QCFinding(gate="loudness", message=f"Video file missing: {video_path}")],
        )

    try:
        _, _, _, _, has_audio = _video_props(video_path)
    except Exception as exc:
        return GateResult(
            gate="loudness",
            passed=False,
            findings=[QCFinding(gate="loudness", message=f"Failed to probe media: {exc}")],
        )
    if not has_audio:
        return GateResult(
            gate="loudness",
            passed=False,
            findings=[QCFinding(gate="loudness", message="No audio stream present for loudness measurement.")],
        )

    res = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(video_path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    integrated, true_peak, lra = _parse_ebur128(res.stderr)
    findings: list[QCFinding] = []

    if integrated is None or true_peak is None:
        findings.append(
            QCFinding(gate="loudness", message="Failed to parse ebur128 loudness or true peak summary.")
        )
    else:
        if abs(integrated - target_lufs) > 1.5:
            findings.append(
                QCFinding(
                    gate="loudness",
                    message=(
                        f"Integrated loudness {integrated:.2f} LUFS outside target "
                        f"{target_lufs:.1f} +/- 1.5 LU."
                    ),
                    details={"integrated_lufs": integrated, "target_lufs": target_lufs},
                )
            )
        if true_peak > max_true_peak + 0.2:
            findings.append(
                QCFinding(
                    gate="loudness",
                    message=f"True peak {true_peak:.2f} dBTP exceeds limit {max_true_peak:.1f} + 0.2 dBTP.",
                    details={"true_peak_dbtp": true_peak, "max_true_peak": max_true_peak},
                )
            )

    return GateResult(
        gate="loudness",
        passed=len(findings) == 0,
        findings=findings,
        metrics={
            "integrated_lufs": integrated,
            "true_peak_dbtp": true_peak,
            "lra_lu": lra,
            "target_lufs": target_lufs,
            "max_true_peak": max_true_peak,
        },
        summary=(
            f"Loudness passed ({integrated:.2f} LUFS, {true_peak:.2f} dBTP)."
            if not findings and integrated is not None and true_peak is not None
            else "Loudness check failed."
        ),
    )


def check_frames_and_boxes(
    video_path: Path,
    sample_timestamps: list[float],
    out_dir: Path,
) -> GateResult:
    """Delivery Check 6 (`frames_and_boxes`): extract PNG frame stills into out_dir / 'qc_frames'."""
    if not video_path.exists():
        return GateResult(
            gate="frames_and_boxes",
            passed=False,
            findings=[QCFinding(gate="frames_and_boxes", message=f"Video file missing: {video_path}")],
        )

    frames_dir = out_dir / "qc_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return GateResult(
            gate="frames_and_boxes",
            passed=False,
            findings=[QCFinding(gate="frames_and_boxes", message=f"Failed to open video: {video_path}")],
        )

    evidence: list[str] = []
    findings: list[QCFinding] = []
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        if fps <= 0:
            fps = 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = (frame_count / fps) if frame_count > 0 else 1.0

        targets = list(sample_timestamps) if sample_timestamps else [0.0, 0.5 * duration, max(0.0, duration - 1.0 / fps)]
        for idx, ts in enumerate(targets):
            clamped_ts = max(0.0, min(ts, max(0.0, duration - 1.0 / fps)))
            frame_idx = int(round(clamped_ts * fps))
            if frame_count > 0:
                frame_idx = max(0, min(frame_count - 1, frame_idx))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frame = cap.read()
            png_path = frames_dir / f"frame_{idx:03d}_{clamped_ts:.3f}s.png"
            if ok and frame is not None and cv2.imwrite(str(png_path), frame):
                evidence.append(str(png_path))
            else:
                # Fallback via FFmpeg seek if VideoCapture seek fails on a stream
                ff_res = subprocess.run(
                    ["ffmpeg", "-y", "-v", "error", "-ss", f"{clamped_ts:.4f}", "-i", str(video_path), "-frames:v", "1", str(png_path)],
                    capture_output=True,
                    text=True,
                )
                if ff_res.returncode == 0 and png_path.exists():
                    evidence.append(str(png_path))
                else:
                    findings.append(
                        QCFinding(
                            gate="frames_and_boxes",
                            message=f"Failed to extract frame still at {ts:.3f}s.",
                            timestamp=ts,
                        )
                    )
    finally:
        cap.release()

    return GateResult(
        gate="frames_and_boxes",
        passed=len(findings) == 0 and len(evidence) > 0,
        findings=findings,
        evidence=evidence,
        metrics={"extracted_count": len(evidence)},
        summary=f"Extracted {len(evidence)} QC frame still(s) into {frames_dir}." if not findings else "Frame extraction failed.",
    )


def _load_waivers_from_run_json(run_json_path: Path | None) -> tuple[list[QCWaiver], list[str]]:
    if run_json_path is None or not run_json_path.exists():
        return [], []
    try:
        data = json.loads(run_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"Failed to read waivers from {run_json_path}: {exc}"]
    raw_waivers = data.get("waivers", [])
    if not isinstance(raw_waivers, list):
        return [], ["run.json field 'waivers' must be a list."]
    parsed: list[QCWaiver] = []
    errors: list[str] = []
    for idx, item in enumerate(raw_waivers):
        try:
            parsed.append(QCWaiver.model_validate(item))
        except Exception as exc:
            errors.append(f"Malformed waiver[{idx}] in run.json: {exc}")
    return parsed, errors


_NON_OCCLUDING_OVERLAY_KINDS: frozenset[str] = frozenset(
    {"speaker_panel", "speaker_centre", "speaker_pip", "circle_stage", "full_graphic"}
)


def _overlays_from_dom_manifest(dom_manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not dom_manifest:
        return []
    overlays: list[dict[str, Any]] = []
    for ts, col_name, el in _iter_dom_elements(dom_manifest):
        kind = str(el.get("kind", "")).lower()
        if col_name == "overlay_boxes":
            if kind in _NON_OCCLUDING_OVERLAY_KINDS:
                continue
        elif not (
            col_name in ("overlays", "captions")
            or "overlay" in str(el.get("role", "")).lower()
            or "caption" in str(el.get("role", "")).lower()
        ):
            continue
        item = dict(el)
        if ts is not None and "timestamp" not in item and "start" not in item:
            item["start"] = ts
            item.setdefault("duration", 0.5)
        overlays.append(item)
    return overlays


def run_qc(
    video_path: Path,
    out_dir: Path,
    *,
    delivery_mode: bool = False,
    cut_timestamps: list[float] | None = None,
    run_json_path: Path | None = None,
    waivers: list[QCWaiver] | None = None,
    hyperframes_check_report: dict[str, Any] | None = None,
    dom_manifest: dict[str, Any] | None = None,
    overlay_boxes: list[dict[str, Any]] | None = None,
    kept_segments: list[KeepSegment] | None = None,
    transcript_bundle: TranscriptBundle | None = None,
    plate_windows: list[tuple[float, float]] | None = None,
    srt_path: Path | None = None,
    sample_timestamps: list[float] | None = None,
    width: int | None = None,
    height: int | None = None,
    margin_ratio: float = 0.05,
    max_tail_dbfs: float = -18.0,
    target_lufs: float = -14.0,
    max_true_peak: float = -1.0,
) -> QCReport:
    """Execute the 8 hard-blocking gates (plus 6 delivery checks when delivery_mode=True) and write qc_report.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    run_waivers, waiver_parse_errors = _load_waivers_from_run_json(run_json_path)
    combined_waivers = [*run_waivers, *(waivers or [])]

    waiver_gate = validate_waivers(combined_waivers)
    for err in waiver_parse_errors:
        waiver_gate.findings.append(QCFinding(gate="waiver_policy", message=err))
        waiver_gate.passed = False

    v_width = width or 1920
    v_height = height or 1080
    v_duration = 0.0
    if video_path.exists():
        try:
            pw, ph, _, pdur, _ = _video_props(video_path)
            v_width = width or pw
            v_height = height or ph
            v_duration = pdur
        except Exception:
            pass

    resolved_overlays = overlay_boxes if overlay_boxes is not None else _overlays_from_dom_manifest(dom_manifest)
    cuts = list(cut_timestamps or [])

    gates: dict[str, GateResult] = {
        "waiver_policy": waiver_gate,
        "flash": check_flash(video_path, cuts),
        "blank_check": check_blank(video_path),
        "fit": check_fit(hyperframes_check_report=hyperframes_check_report, dom_manifest=dom_manifest),
        "margin_check": check_margins(dom_manifest=dom_manifest, width=v_width, height=v_height, margin_ratio=margin_ratio),
        "eyes_mouth_check": check_eyes_mouth(video_path, overlay_boxes=resolved_overlays, waivers=combined_waivers),
        "stale_check": check_stale(run_json_path),
        "hold_sentence": (
            check_hold_sentence(kept_segments, transcript_bundle)
            if kept_segments is not None and transcript_bundle is not None
            else GateResult(gate="hold_sentence", passed=True, summary="No kept_segments/transcript_bundle provided; skipped.")
        ),
        "stability": check_stability(video_path, dom_manifest=dom_manifest, plate_windows=plate_windows),
    }

    if delivery_mode:
        resolved_samples = list(sample_timestamps) if sample_timestamps is not None else sorted(
            set([0.0, *[max(0.0, c) for c in cuts], max(0.0, v_duration * 0.5), max(0.0, v_duration - 0.1)])
        )
        gates["decode"] = check_decode(video_path)
        gates["tail_check"] = check_tail(video_path, cut_timestamps=cuts, max_tail_dbfs=max_tail_dbfs)
        gates["freeze_check"] = check_freeze(video_path, waivers=combined_waivers)
        gates["captions"] = check_captions(srt_path, duration_sec=v_duration)
        gates["loudness"] = check_loudness(video_path, target_lufs=target_lufs, max_true_peak=max_true_peak)
        gates["frames_and_boxes"] = check_frames_and_boxes(video_path, sample_timestamps=resolved_samples, out_dir=out_dir)

    failed_gates = [name for name, g in gates.items() if not g.passed]
    report_path = out_dir / "qc_report.json"
    report = QCReport(
        video_path=str(video_path),
        delivery_mode=delivery_mode,
        passed=len(failed_gates) == 0,
        gates=gates,
        waivers_applied=combined_waivers,
        failed_gates=failed_gates,
        created_at=datetime.now(timezone.utc).isoformat(),
        report_path=str(report_path),
    )
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report
