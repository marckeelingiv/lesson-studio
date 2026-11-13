"""Remotion headless render bridge."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from schema import TimelineManifest

RENDERER_DIR = Path(__file__).resolve().parent.parent / "renderer"


def render_with_remotion(
    rough_cut_path: Path,
    manifest_path: Path,
    output_mp4: Path,
    renderer_dir: Path = RENDERER_DIR,
) -> Path:
    """Stage rough_cut.mp4 in renderer/public and run headless Remotion render."""
    if not (renderer_dir / "node_modules").exists():
        raise RuntimeError(
            f"Remotion dependencies not installed in {renderer_dir}. Run 'make video-setup' or 'npm --prefix video_pipeline/renderer install'."
        )

    manifest = TimelineManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    public_dir = renderer_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    staged_video = public_dir / manifest.videoFile

    shutil.copy2(rough_cut_path, staged_video)
    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    try:
        cmd = [
            "npx",
            "remotion",
            "render",
            "src/index.ts",
            "MainVideo",
            str(output_mp4.resolve()),
            f"--props={manifest_path.resolve()}",
        ]
        subprocess.run(cmd, cwd=renderer_dir, check=True)
    finally:
        if staged_video.exists():
            staged_video.unlink()

    return output_mp4
