"""Remotion headless render bridge."""

from __future__ import annotations

import os
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
    camera_cut_path: Path | None = None,
) -> Path:
    """Stage rough cut (and optional camera cut) in renderer/public and run headless Remotion render."""
    if not (renderer_dir / "node_modules").exists():
        raise RuntimeError(
            f"Remotion dependencies not installed in {renderer_dir}. Run 'make video-setup' or 'npm --prefix video_pipeline/renderer install'."
        )

    manifest = TimelineManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    public_dir = renderer_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    staged_video = public_dir / manifest.videoFile
    staged_camera: Path | None = None
    camera_file = getattr(manifest, "cameraFile", None)

    try:
        shutil.copy2(rough_cut_path, staged_video)
        if camera_cut_path is not None and camera_file:
            staged_camera = public_dir / camera_file
            shutil.copy2(camera_cut_path, staged_camera)

        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "npx",
            "remotion",
            "render",
            "src/index.ts",
            "MainVideo",
            str(output_mp4.resolve()),
            f"--props={manifest_path.resolve()}",
        ]
        browser = (
            os.environ.get("REMOTION_BROWSER_EXECUTABLE")
            or shutil.which("chromium")
            or shutil.which("google-chrome")
        )
        if browser:
            cmd.append(f"--browser-executable={browser}")
        subprocess.run(cmd, cwd=renderer_dir, check=True)
    finally:
        if staged_video.exists():
            staged_video.unlink()
        if staged_camera is not None and staged_camera.exists():
            staged_camera.unlink()

    return output_mp4
