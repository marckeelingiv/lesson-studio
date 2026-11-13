"""Typer CLI for the AI-automated video editing pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

# Ensure sibling modules resolve regardless of CWD
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from assemble import assemble_rough_cut, remap_timeline  # noqa: E402
from export_nle import export_fcpxml  # noqa: E402
from ingest import extract_audio, probe_video  # noqa: E402
from planner import generate_edl  # noqa: E402
from render import render_with_remotion  # noqa: E402
from schema import EditDecisionList, TranscriptBundle, VideoMetadata  # noqa: E402
from transcribe import build_transcript_bundle  # noqa: E402

app = typer.Typer(help="Transcript-first agentic video editing & programmatic rendering pipeline.")
DEFAULT_WORKSPACE = Path(__file__).resolve().parent.parent / "workspace"


def _project_dir(video_path: Path, out_dir: Optional[Path]) -> Path:
    return out_dir if out_dir is not None else DEFAULT_WORKSPACE / video_path.stem


@app.command()
def ingest(
    video: Path = typer.Argument(..., exists=True, help="Input raw video file."),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", "-o", help="Workspace directory."),
) -> None:
    """Probe video metadata and extract 16 kHz mono WAV audio."""
    work = _project_dir(video, out_dir)
    work.mkdir(parents=True, exist_ok=True)
    meta = probe_video(video)
    (work / "metadata.json").write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    if meta.has_audio:
        extract_audio(video, work / "audio.wav")
    typer.echo(f"Ingested {video.name} -> {work} ({meta.duration:.2f}s, {meta.width}x{meta.height} @ {meta.fps}fps)")


@app.command()
def transcribe(
    video: Path = typer.Argument(..., exists=True, help="Input raw video file."),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", "-o"),
    model_size: str = typer.Option("base", "--whisper-model", help="faster-whisper model size."),
    device: str = typer.Option("auto", "--device", help="cpu, cuda, or auto."),
    noise_db: float = typer.Option(-35.0, "--noise-db", help="Silence threshold in dB."),
    min_silence: float = typer.Option(0.6, "--min-silence", help="Minimum silence duration (s)."),
) -> None:
    """Transcribe audio with word timestamps and detect silences, fillers, and retakes."""
    work = _project_dir(video, out_dir)
    work.mkdir(parents=True, exist_ok=True)
    meta_path = work / "metadata.json"
    meta = VideoMetadata.model_validate_json(meta_path.read_text()) if meta_path.exists() else probe_video(video)
    meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")

    wav_path = work / "audio.wav"
    if not wav_path.exists():
        extract_audio(video, wav_path)

    bundle = build_transcript_bundle(
        meta=meta,
        wav_path=wav_path,
        model_size=model_size,
        device=device,
        noise_db=noise_db,
        min_silence_sec=min_silence,
    )
    (work / "transcript.json").write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(
        f"Transcribed {len(bundle.segments)} segments, {len(bundle.silences)} silences, "
        f"{len(bundle.fillers)} fillers, {len(bundle.retakes)} retakes -> {work / 'transcript.json'}"
    )


@app.command()
def plan(
    transcript_json: Path = typer.Argument(..., exists=True, help="Path to transcript.json."),
    out_edl: Optional[Path] = typer.Option(None, "--out", "-o", help="Output edl.json path."),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="LiteLLM model, opencode, or opencode/<provider>/<model>."),
    heuristic: bool = typer.Option(False, "--heuristic", help="Use deterministic heuristic planner."),
    instructions: Optional[str] = typer.Option(None, "--instructions", help="Extra editorial prompt."),
) -> None:
    """Generate a structured EditDecisionList (edl.json) from transcript.json."""
    bundle = TranscriptBundle.model_validate_json(transcript_json.read_text(encoding="utf-8"))
    edl = generate_edl(bundle, model=model, heuristic=heuristic, instructions=instructions)
    dest = out_edl or transcript_json.parent / "edl.json"
    dest.write_text(edl.model_dump_json(indent=2), encoding="utf-8")
    kept_dur = sum(s.end - s.start for s in edl.kept_segments)
    typer.echo(
        f"Planned {len(edl.kept_segments)} kept segments ({kept_dur:.2f}s / {bundle.duration:.2f}s), "
        f"{len(edl.graphic_cues)} graphic cues -> {dest}"
    )


@app.command()
def assemble(
    edl_json: Path = typer.Argument(..., exists=True, help="Path to edl.json."),
    transcript_json: Optional[Path] = typer.Option(None, "--transcript", "-t"),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", "-o"),
) -> None:
    """Assemble rough_cut.mp4 with FFmpeg and remap captions into timeline_manifest.json."""
    work = out_dir or edl_json.parent
    edl = EditDecisionList.model_validate_json(edl_json.read_text(encoding="utf-8"))
    t_path = transcript_json or work / "transcript.json"
    bundle = TranscriptBundle.model_validate_json(t_path.read_text(encoding="utf-8"))

    rough_cut = work / "rough_cut.mp4"
    meta = probe_video(Path(edl.source_path))
    assemble_rough_cut(Path(edl.source_path), edl, rough_cut, has_audio=meta.has_audio)

    manifest = remap_timeline(bundle, edl, video_file=rough_cut.name)
    (work / "timeline_manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Assembled {rough_cut} ({manifest.durationInFrames} frames) and timeline_manifest.json")


@app.command()
def render(
    manifest_json: Path = typer.Argument(..., exists=True, help="Path to timeline_manifest.json."),
    rough_cut: Optional[Path] = typer.Option(None, "--rough-cut"),
    out_mp4: Optional[Path] = typer.Option(None, "--out", "-o"),
) -> None:
    """Render final MP4 with animated captions and motion graphics via Remotion."""
    work = manifest_json.parent
    rough = rough_cut or work / "rough_cut.mp4"
    dest = out_mp4 or work / "final.mp4"
    render_with_remotion(rough, manifest_json, dest)
    typer.echo(f"Rendered final video -> {dest}")


@app.command("export-nle")
def export_nle(
    edl_json: Path = typer.Argument(..., exists=True, help="Path to edl.json."),
    out_fcpxml: Optional[Path] = typer.Option(None, "--out", "-o"),
) -> None:
    """Export edl.json to FCPXML 1.9 for DaVinci Resolve."""
    edl = EditDecisionList.model_validate_json(edl_json.read_text(encoding="utf-8"))
    dest = out_fcpxml or edl_json.parent / "timeline.fcpxml"
    export_fcpxml(edl, dest)
    typer.echo(f"Exported FCPXML -> {dest}")


@app.command()
def run(
    video: Path = typer.Argument(..., exists=True, help="Input raw video file."),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", "-o"),
    whisper_model: str = typer.Option("base", "--whisper-model"),
    llm_model: str = typer.Option("gpt-4o-mini", "--model"),
    heuristic: bool = typer.Option(False, "--heuristic"),
    instructions: Optional[str] = typer.Option(None, "--instructions"),
    export_fcpxml_flag: bool = typer.Option(True, "--export-nle/--no-export-nle"),
    skip_render: bool = typer.Option(False, "--skip-render", help="Stop after rough_cut.mp4 + manifest."),
) -> None:
    """Run the full end-to-end pipeline: ingest -> transcribe -> plan -> assemble -> render."""
    work = _project_dir(video, out_dir)
    work.mkdir(parents=True, exist_ok=True)

    ingest(video=video, out_dir=work)
    transcribe(video=video, out_dir=work, model_size=whisper_model)
    plan(
        transcript_json=work / "transcript.json",
        out_edl=work / "edl.json",
        model=llm_model,
        heuristic=heuristic,
        instructions=instructions,
    )
    assemble(edl_json=work / "edl.json", transcript_json=work / "transcript.json", out_dir=work)
    if export_fcpxml_flag:
        export_nle(edl_json=work / "edl.json", out_fcpxml=work / "timeline.fcpxml")
    if not skip_render:
        render(manifest_json=work / "timeline_manifest.json", rough_cut=work / "rough_cut.mp4", out_mp4=work / "final.mp4")


if __name__ == "__main__":
    app()
