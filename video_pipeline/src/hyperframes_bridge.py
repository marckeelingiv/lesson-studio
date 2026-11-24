"""HyperFrames compilation, verification, Contact Sheet, and video render bridge."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
HYPERFRAMES_DIR = REPO_ROOT / "video_pipeline" / "hyperframes"
COMPOSE_SCRIPT = HYPERFRAMES_DIR / "src" / "compose.mjs"
DEFAULT_TOKENS_CSS = (
    REPO_ROOT / "editing_system" / "assets" / "tokens" / "engineering-editorial" / "tokens.css"
)


class ContactSheetStill(BaseModel):
    """Single keyframe still captured for a Storyboard beat."""

    beat_id: str
    timestamp: float
    scene_layout: str
    image_path: Path


class ContactSheetResult(BaseModel):
    """Rendered Contact Sheet grid and individual beat still metadata."""

    contact_sheet_path: Path
    stills: list[ContactSheetStill] = Field(default_factory=list)


def _hyperframes_env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("HYPERFRAMES_BROWSER_PATH"):
        chromium = shutil.which("chromium") or "/usr/bin/chromium"
        if Path(chromium).exists():
            env["HYPERFRAMES_BROWSER_PATH"] = chromium
    return env


def _parse_json_output(stdout: str, stderr: str, cmd: list[str], returncode: int) -> dict[str, Any]:
    text = stdout.strip()
    if text:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            first = text.find("{")
            last = text.rfind("}")
            if first != -1 and last > first:
                try:
                    parsed = json.loads(text[first : last + 1])
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass
    raise RuntimeError(
        f"Command {' '.join(cmd)} exited with {returncode} without valid JSON output.\n"
        f"stdout: {stdout}\nstderr: {stderr}"
    )


def _run_hyperframes(args: list[str]) -> subprocess.CompletedProcess[str]:
    cmd = ["npx", "--prefix", str(HYPERFRAMES_DIR), "hyperframes", *args]
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=_hyperframes_env(),
        capture_output=True,
        text=True,
        check=False,
    )


def compile_hyperframes_project(
    storyboard_path: Path,
    manifest_path: Path,
    out_project_dir: Path,
    tokens_css: Path | None = None,
    theme: str = "dark",
    media_dir: Path | None = None,
) -> Path:
    """Compile storyboard.json and timeline_manifest.json into a self-contained HyperFrames project."""
    storyboard = Path(storyboard_path).resolve()
    manifest = Path(manifest_path).resolve()
    out_dir = Path(out_project_dir).resolve()
    tokens = Path(tokens_css).resolve() if tokens_css is not None else DEFAULT_TOKENS_CSS

    if not storyboard.exists():
        raise FileNotFoundError(f"Storyboard not found: {storyboard}")
    if not manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest}")
    if not tokens.exists():
        raise FileNotFoundError(f"Design tokens file not found: {tokens}")
    if not COMPOSE_SCRIPT.exists():
        raise FileNotFoundError(f"compose.mjs not found: {COMPOSE_SCRIPT}")

    cmd = [
        "node",
        str(COMPOSE_SCRIPT),
        "--storyboard",
        str(storyboard),
        "--manifest",
        str(manifest),
        "--tokens",
        str(tokens),
        "--theme",
        theme,
        "--out",
        str(out_dir),
    ]
    if media_dir is not None:
        cmd.extend(["--media-dir", str(Path(media_dir).resolve())])

    proc = subprocess.run(cmd, cwd=HYPERFRAMES_DIR, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"compose.mjs failed (exit {proc.returncode}):\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )

    index_html = out_dir / "index.html"
    if not index_html.exists():
        raise RuntimeError(f"compose.mjs did not generate {index_html}")
    return out_dir


def run_hyperframes_lint(project_dir: Path) -> dict[str, Any]:
    """Run `hyperframes lint <project_dir> --json` and return parsed findings."""
    target = Path(project_dir).resolve()
    proc = _run_hyperframes(["lint", str(target), "--json"])
    return _parse_json_output(proc.stdout, proc.stderr, ["hyperframes", "lint"], proc.returncode)


def run_hyperframes_check(project_dir: Path) -> dict[str, Any]:
    """Run `hyperframes check <project_dir> --json --no-browser-gpu` and return parsed report."""
    target = Path(project_dir).resolve()
    proc = _run_hyperframes(
        ["check", str(target), "--json", "--no-browser-gpu", "--no-cache"]
    )
    return _parse_json_output(proc.stdout, proc.stderr, ["hyperframes", "check"], proc.returncode)


def _load_beats(storyboard_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(storyboard_path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [b for b in raw if isinstance(b, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("beats"), list):
        return [b for b in raw["beats"] if isinstance(b, dict)]
    raise ValueError(f"Invalid storyboard structure in {storyboard_path}: expected beats list.")


def _load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _stitch_contact_sheet(
    stills: list[ContactSheetStill],
    beat_titles: dict[str, str],
    out_path: Path,
) -> Path:
    """Assemble captured beat stills into a labeled 16:9 Contact Sheet PNG grid."""
    cols = 2 if len(stills) <= 4 else 3
    rows = max(1, math.ceil(len(stills) / cols))
    tile_w, tile_h = 640, 360
    label_h = 56
    pad = 24
    header_h = 56

    canvas_w = pad + cols * (tile_w + pad)
    canvas_h = header_h + pad + rows * (tile_h + label_h + pad)

    bg_color = (11, 16, 20)
    surface_color = (18, 25, 32)
    border_color = (56, 74, 92)
    accent_color = (56, 189, 248)
    text_primary = (241, 245, 249)
    text_secondary = (148, 163, 184)

    sheet = Image.new("RGB", (canvas_w, canvas_h), bg_color)
    draw = ImageDraw.Draw(sheet)
    header_font = _load_font(22)
    label_font = _load_font(16)
    sub_font = _load_font(14)

    draw.text(
        (pad, 16),
        f"LESSON STUDIO CONTACT SHEET  |  {len(stills)} BEAT(S)",
        fill=text_primary,
        font=header_font,
    )
    draw.line([(pad, header_h - 4), (canvas_w - pad, header_h - 4)], fill=border_color, width=2)

    for idx, still in enumerate(stills):
        col = idx % cols
        row = idx // cols
        x = pad + col * (tile_w + pad)
        y = header_h + pad + row * (tile_h + label_h + pad)

        with Image.open(still.image_path) as img:
            thumb = img.convert("RGB").resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        sheet.paste(thumb, (x, y))

        draw.rectangle(
            [x, y + tile_h, x + tile_w - 1, y + tile_h + label_h - 1],
            fill=surface_color,
            outline=border_color,
        )
        draw.rectangle([x, y, x + tile_w - 1, y + tile_h + label_h - 1], outline=border_color, width=2)
        draw.rectangle([x, y + tile_h, x + 4, y + tile_h + label_h - 1], fill=accent_color)

        title = beat_titles.get(still.beat_id, "")
        line1 = f"{still.beat_id}  |  {still.scene_layout}  |  t={still.timestamp:.2f}s"
        draw.text((x + 14, y + tile_h + 7), line1, fill=text_primary, font=label_font)
        if title:
            short_title = title if len(title) <= 68 else f"{title[:65]}..."
            draw.text((x + 14, y + tile_h + 30), short_title, fill=text_secondary, font=sub_font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, format="PNG")
    return out_path


def render_contact_sheet(
    project_dir: Path,
    storyboard_path: Path,
    out_dir: Path,
) -> ContactSheetResult:
    """Capture beat midpoint stills via `hyperframes snapshot` and stitch a labeled Contact Sheet PNG."""
    project = Path(project_dir).resolve()
    sb_path = Path(storyboard_path).resolve()
    output_dir = Path(out_dir).resolve()
    stills_dir = output_dir / "stills"
    stills_dir.mkdir(parents=True, exist_ok=True)

    beats = _load_beats(sb_path)
    if not beats:
        raise ValueError(f"Storyboard has no beats: {sb_path}")

    beat_requests: list[tuple[str, float, str]] = []
    beat_titles: dict[str, str] = {}
    unique_times: list[float] = []

    for idx, beat in enumerate(beats):
        beat_id = str(beat.get("id") or f"beat-{idx + 1}")
        start = float(beat.get("start", 0.0))
        duration = max(0.05, float(beat.get("duration", 1.0)))
        midpoint = round(start + min(0.5, duration / 2.0), 3)
        scene_layout = str(beat.get("scene_layout") or "full-graphic")
        beat_titles[beat_id] = str(beat.get("title") or "")
        beat_requests.append((beat_id, midpoint, scene_layout))
        if all(abs(midpoint - existing) >= 0.002 for existing in unique_times):
            unique_times.append(midpoint)

    at_arg = ",".join(f"{t:.3f}".rstrip("0").rstrip(".") or "0" for t in unique_times)
    proc = _run_hyperframes(
        [
            "snapshot",
            str(project),
            "--at",
            at_arg,
            "--keep",
            "--no-end",
            "--no-browser-gpu",
            "--output",
            str(stills_dir),
            "--json",
        ]
    )
    envelope = _parse_json_output(
        proc.stdout, proc.stderr, ["hyperframes", "snapshot"], proc.returncode
    )
    if not envelope.get("ok"):
        raise RuntimeError(f"hyperframes snapshot failed: {json.dumps(envelope)}")

    captured_frames = envelope.get("frames") or []
    stills: list[ContactSheetStill] = []
    for beat_id, midpoint, scene_layout in beat_requests:
        matched_path: Path | None = None
        best_delta = float("inf")
        for frame in captured_frames:
            frame_time = frame.get("time")
            frame_path = frame.get("path")
            if frame_time is None or not frame_path:
                continue
            delta = abs(float(frame_time) - midpoint)
            if delta < best_delta:
                best_delta = delta
                matched_path = Path(frame_path)
        if matched_path is None or best_delta > 0.01:
            raise RuntimeError(
                f"Snapshot frame missing for beat '{beat_id}' at t={midpoint}s in {captured_frames}"
            )
        if not matched_path.exists() or matched_path.stat().st_size <= 0:
            raise RuntimeError(f"Captured snapshot PNG is missing or empty: {matched_path}")
        stills.append(
            ContactSheetStill(
                beat_id=beat_id,
                timestamp=midpoint,
                scene_layout=scene_layout,
                image_path=matched_path,
            )
        )

    contact_sheet_path = output_dir / "contact_sheet.png"
    _stitch_contact_sheet(stills, beat_titles, contact_sheet_path)
    return ContactSheetResult(contact_sheet_path=contact_sheet_path, stills=stills)


def render_hyperframes_video(
    project_dir: Path,
    output_path: Path,
    fmt: str = "mp4",
    quality: str = "looks",
) -> Path:
    """Render a compiled HyperFrames project to MP4/WebM/etc. with `--no-browser-gpu`."""
    project = Path(project_dir).resolve()
    dest = Path(output_path).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    proc = _run_hyperframes(
        [
            "render",
            str(project),
            "--output",
            str(dest),
            "--format",
            fmt,
            "--quality",
            quality,
            "--no-browser-gpu",
        ]
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"hyperframes render failed (exit {proc.returncode}):\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    if not dest.exists():
        raise RuntimeError(f"hyperframes render completed without writing {dest}")
    if dest.is_file() and dest.stat().st_size <= 0:
        raise RuntimeError(f"Rendered output file is empty: {dest}")
    return dest
