"""Typer CLI for the AI-automated video editing pipeline."""

from __future__ import annotations

from datetime import date as dt_date
import json
import sys
from pathlib import Path
from typing import Literal, Optional

import typer

# Ensure sibling modules resolve regardless of CWD
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from assemble import assemble_rough_cut, remap_timeline  # noqa: E402
from audio_mix import AudioSfxCue, PictureLockRequiredError, export_srt, mix_locked_audio  # noqa: E402
from cursor_events import CursorEventLog, record_hyprland_cursor  # noqa: E402
from editing_system import (  # noqa: E402
    DEFAULT_CATALOG_PATH,
    EDITING_SYSTEM_DIR,
    RunState,
    init_creative_brief,
    load_asset_catalog,
    load_creative_brief,
    validate_asset_catalog,
    validate_storyboard,
)
from export_nle import export_fcpxml  # noqa: E402
from hyperframes_bridge import (  # noqa: E402
    compile_hyperframes_project,
    render_contact_sheet,
    render_hyperframes_video,
    run_hyperframes_check,
    run_hyperframes_lint,
)
from ingest import extract_audio, probe_video  # noqa: E402
from planner import generate_edl  # noqa: E402
from qc import run_qc  # noqa: E402
from render import render_with_remotion  # noqa: E402
from schema import EditDecisionList, TimelineManifest, TranscriptBundle, VideoMetadata  # noqa: E402
from sift import run_scientific_sift  # noqa: E402
from taste_memory import (  # noqa: E402
    ReviewCategory,
    ReviewLogEntry,
    ReviewTag,
    append_review_note,
    find_promotion_candidates,
    load_review_log,
    render_taste_profile_md,
)
from timeline_otio import (  # noqa: E402
    edl_to_otio,
    export_nle as export_otio_nle,
    import_nle as import_otio_nle,
    load_otio,
    otio_to_edl,
    save_otio,
)
from transcribe import build_transcript_bundle  # noqa: E402

app = typer.Typer(help="Transcript-first agentic video editing & programmatic rendering pipeline.")
DEFAULT_WORKSPACE = Path(__file__).resolve().parent.parent / "workspace"


def _project_dir(video_path: Path, out_dir: Optional[Path]) -> Path:
    return out_dir if out_dir is not None else DEFAULT_WORKSPACE / video_path.stem


def _opt_path(value: Optional[Path]) -> Optional[Path]:
    """Return value as Path when set, ignoring Typer OptionInfo defaults in direct Python calls."""
    if isinstance(value, Path):
        return value
    if isinstance(value, str):
        return Path(value)
    return None


@app.command("record-cursor")
def record_cursor(
    out_json: Path = typer.Option(Path("events.json"), "--out", "-o", help="Output cursor events JSON path."),
    duration: float = typer.Option(10.0, "--duration", help="Recording duration in seconds."),
    interval: float = typer.Option(0.1, "--interval", help="Polling interval in seconds."),
    width: int = typer.Option(1920, "--width", help="Screen width in pixels."),
    height: int = typer.Option(1080, "--height", help="Screen height in pixels."),
) -> None:
    """Record Hyprland cursor movements and focus clicks into an events JSON log."""
    log = record_hyprland_cursor(
        output_path=out_json,
        duration_sec=duration,
        interval_sec=interval,
        width=width,
        height=height,
    )
    typer.echo(f"Recorded {len(log.events)} cursor events -> {out_json}")


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
    events: Optional[Path] = typer.Option(None, "--events", help="Optional cursor events.json log."),
) -> None:
    """Generate a structured EditDecisionList (edl.json) from transcript.json."""
    bundle = TranscriptBundle.model_validate_json(transcript_json.read_text(encoding="utf-8"))
    events_path = _opt_path(events)
    cursor_log = (
        CursorEventLog.model_validate_json(events_path.read_text(encoding="utf-8"))
        if events_path is not None
        else None
    )
    edl = generate_edl(
        bundle,
        model=model,
        heuristic=heuristic,
        instructions=instructions,
        cursor_log=cursor_log,
    )
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
    camera: Optional[Path] = typer.Option(None, "--camera", help="Optional separate camera video track."),
) -> None:
    """Assemble rough_cut.mp4 with FFmpeg and remap captions into timeline_manifest.json."""
    work = out_dir or edl_json.parent
    edl = EditDecisionList.model_validate_json(edl_json.read_text(encoding="utf-8"))
    t_path = transcript_json or work / "transcript.json"
    bundle = TranscriptBundle.model_validate_json(t_path.read_text(encoding="utf-8"))

    rough_cut = work / "rough_cut.mp4"
    meta = probe_video(Path(edl.source_path))
    assemble_rough_cut(Path(edl.source_path), edl, rough_cut, has_audio=meta.has_audio)

    cam_arg = _opt_path(camera)
    cam_path = cam_arg or (Path(edl.camera_path) if edl.camera_path else None)
    camera_file: Optional[str] = None
    if cam_path is not None:
        if not cam_path.exists():
            raise typer.BadParameter(f"Camera video not found: {cam_path}", param_hint="--camera")
        if edl.camera_path != str(cam_path):
            edl = edl.model_copy(update={"camera_path": str(cam_path)})
            edl_json.write_text(edl.model_dump_json(indent=2), encoding="utf-8")
        rough_camera = work / "rough_camera.mp4"
        assemble_rough_cut(
            cam_path,
            edl,
            rough_camera,
            has_audio=False,
            normalize_audio=False,
        )
        camera_file = rough_camera.name

    manifest = remap_timeline(bundle, edl, video_file=rough_cut.name, camera_file=camera_file)
    (work / "timeline_manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Assembled {rough_cut} ({manifest.durationInFrames} frames) and timeline_manifest.json")


@app.command()
def render(
    manifest_json: Path = typer.Argument(..., exists=True, help="Path to timeline_manifest.json."),
    rough_cut: Optional[Path] = typer.Option(None, "--rough-cut"),
    out_mp4: Optional[Path] = typer.Option(None, "--out", "-o"),
    camera: Optional[Path] = typer.Option(None, "--camera", help="Optional separate camera video track."),
) -> None:
    """Render final MP4 with animated captions and motion graphics via Remotion."""
    work = manifest_json.parent
    rough = rough_cut or work / "rough_cut.mp4"
    dest = out_mp4 or work / "final.mp4"
    cam_arg = _opt_path(camera)
    default_camera = work / "rough_camera.mp4"
    camera_cut = cam_arg or (default_camera if default_camera.exists() else None)
    render_with_remotion(rough, manifest_json, dest, camera_cut_path=camera_cut)
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
    events: Optional[Path] = typer.Option(None, "--events", help="Optional cursor events.json log."),
    camera: Optional[Path] = typer.Option(None, "--camera", help="Optional separate camera video track."),
    export_fcpxml_flag: bool = typer.Option(True, "--export-nle/--no-export-nle"),
    skip_render: bool = typer.Option(False, "--skip-render", help="Stop after rough_cut.mp4 + manifest."),
) -> None:
    """Run the full end-to-end pipeline: ingest -> transcribe -> plan -> assemble -> render."""
    work = _project_dir(video, out_dir)
    work.mkdir(parents=True, exist_ok=True)
    events_path = _opt_path(events)
    camera_path = _opt_path(camera)

    ingest(video=video, out_dir=work)
    transcribe(video=video, out_dir=work, model_size=whisper_model)
    plan(
        transcript_json=work / "transcript.json",
        out_edl=work / "edl.json",
        model=llm_model,
        heuristic=heuristic,
        instructions=instructions,
        events=events_path,
    )
    assemble(
        edl_json=work / "edl.json",
        transcript_json=work / "transcript.json",
        out_dir=work,
        camera=camera_path,
    )
    if export_fcpxml_flag:
        export_nle(edl_json=work / "edl.json", out_fcpxml=work / "timeline.fcpxml")
        if not skip_render:
            render(
                manifest_json=work / "timeline_manifest.json",
                rough_cut=work / "rough_cut.mp4",
                out_mp4=work / "final.mp4",
                camera=work / "rough_camera.mp4" if camera_path is not None else None,
            )


def _parse_holds(holds: Optional[list[str]]) -> list[tuple[float, float]] | None:
    if not holds:
        return None
    parsed: list[tuple[float, float]] = []
    for raw in holds:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 2:
            raise typer.BadParameter(f"Expected START,END hold range, got '{raw}'", param_hint="--hold")
        s, e = float(parts[0]), float(parts[1])
        if e <= s:
            raise typer.BadParameter(f"Hold end must exceed start in '{raw}'", param_hint="--hold")
        parsed.append((s, e))
    return parsed


def _resolve_tokens_css(tokens_opt: Optional[Path], catalog_path: Path, token_kit: str) -> Optional[Path]:
    if tokens_opt is not None:
        return tokens_opt
    if catalog_path.exists():
        cat = load_asset_catalog(catalog_path)
        entry = cat.get(token_kit)
        if entry is not None:
            brand_path = catalog_path.parent / entry.path
            candidate = brand_path.parent / "tokens.css"
            if candidate.exists():
                return candidate
    return None


@app.command("brief-init")
def brief_init(
    dest: Path = typer.Argument(Path("creative-brief.yaml"), help="Destination YAML file or directory."),
    video_id: str = typer.Option(..., "--video-id", help="Canonical video identifier (e.g. de-for-fun/lesson)."),
    title: str = typer.Option(..., "--title", help="Video title."),
    preset: str = typer.Option("clean-editorial", "--preset", help="Preset name in editing_system/briefs/presets/."),
) -> None:
    """Scaffold a validated creative-brief.yaml from template and preset."""
    out = init_creative_brief(dest=dest, video_id=video_id, title=title, preset=preset)
    typer.echo(f"Created Creative Brief -> {out}")


@app.command("sift")
def sift_cmd(
    video: Path = typer.Argument(..., exists=True, help="Raw A-Roll or screen video file."),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", "-o", help="Workspace output directory."),
    wav: Optional[Path] = typer.Option(None, "--wav", help="Optional pre-extracted 16 kHz mono WAV."),
    transcript: Optional[Path] = typer.Option(None, "--transcript", "-t", help="Optional existing transcript.json."),
    camera: Optional[Path] = typer.Option(None, "--camera", help="Optional separate camera video track."),
    events: Optional[Path] = typer.Option(None, "--events", help="Optional cursor events.json log."),
    hold: Optional[list[str]] = typer.Option(None, "--hold", help="Protected reading hold as START,END seconds."),
    whisper_model: str = typer.Option("base", "--whisper-model", help="Whisper size if transcribing."),
    no_assemble: bool = typer.Option(False, "--no-assemble", help="Write audit/OTIO/EDL without rendering rough_cut.mp4."),
) -> None:
    """Stage 1 Scientific Sifting: adaptive room tone, consonant tails, retakes, and demo holds."""
    work = _project_dir(video, out_dir)
    work.mkdir(parents=True, exist_ok=True)
    wav_path = _opt_path(wav) or (work / "audio.wav")
    if not wav_path.exists():
        extract_audio(video, wav_path)

    t_path = _opt_path(transcript) or (work / "transcript.json")
    if t_path.exists():
        bundle = TranscriptBundle.model_validate_json(t_path.read_text(encoding="utf-8"))
    else:
        meta = probe_video(video)
        (work / "metadata.json").write_text(meta.model_dump_json(indent=2), encoding="utf-8")
        bundle = build_transcript_bundle(meta=meta, wav_path=wav_path, model_size=whisper_model)
        t_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")

    events_path = _opt_path(events)
    cursor_log = (
        CursorEventLog.model_validate_json(events_path.read_text(encoding="utf-8"))
        if events_path is not None
        else None
    )
    res = run_scientific_sift(
        video_path=video,
        wav_path=wav_path,
        bundle=bundle,
        out_dir=work,
        camera_path=_opt_path(camera),
        cursor_log=cursor_log,
        declared_holds=_parse_holds(hold),
        assemble_video=not no_assemble,
    )
    typer.echo(
        f"Sifted {video.name}: {res.duration_before:.2f}s -> {res.duration_after:.2f}s "
        f"(removed {res.unique_removed_seconds:.2f}s) | OTIO: {res.otio_path} | Audit: {res.cut_audit_path}"
    )


@app.command("otio-export")
def otio_export(
    input_path: Path = typer.Argument(..., exists=True, help="Source .otio or edl.json file."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Destination NLE timeline file."),
    fmt: Optional[Literal["otio", "fcpxml", "kdenlive"]] = typer.Option(
        None, "--format", "-f", help="Target format: otio, fcpxml, or kdenlive."
    ),
) -> None:
    """Export an OTIO timeline (or edl.json) to .otio, .fcpxml, or .kdenlive."""
    if input_path.suffix.lower() == ".json":
        edl = EditDecisionList.model_validate_json(input_path.read_text(encoding="utf-8"))
        timeline = edl_to_otio(edl)
    else:
        timeline = load_otio(input_path) if input_path.suffix.lower() == ".otio" else import_otio_nle(input_path)

    target_fmt = fmt
    if target_fmt is None:
        if out is not None and out.suffix.lower() == ".kdenlive":
            target_fmt = "kdenlive"
        elif out is not None and out.suffix.lower() == ".otio":
            target_fmt = "otio"
        else:
            target_fmt = "fcpxml"

    ext_map = {"otio": ".otio", "fcpxml": ".fcpxml", "kdenlive": ".kdenlive"}
    dest = out or input_path.with_suffix(ext_map[target_fmt])
    exported = export_otio_nle(timeline, dest, fmt=target_fmt)
    typer.echo(f"Exported {target_fmt} timeline -> {exported}")


@app.command("otio-import")
def otio_import(
    input_path: Path = typer.Argument(..., exists=True, help="Source .fcpxml, .kdenlive, or .otio file."),
    out_otio: Optional[Path] = typer.Option(None, "--out-otio", help="Optional canonical .otio output path."),
    out_edl: Optional[Path] = typer.Option(None, "--out-edl", help="Optional edl.json output path."),
    width: int = typer.Option(1920, "--width"),
    height: int = typer.Option(1080, "--height"),
) -> None:
    """Import an NLE timeline (.fcpxml, .kdenlive, .otio) into canonical OTIO and optional EDL."""
    timeline = import_otio_nle(input_path)
    otio_dest = out_otio or input_path.with_suffix(".otio")
    save_otio(timeline, otio_dest)
    if out_edl is not None:
        edl = otio_to_edl(timeline, width=width, height=height)
        out_edl.parent.mkdir(parents=True, exist_ok=True)
        out_edl.write_text(edl.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Imported timeline -> {otio_dest}")


@app.command("contact-sheet")
def contact_sheet_cmd(
    storyboard_json: Path = typer.Argument(..., exists=True, help="Path to storyboard.json."),
    manifest: Path = typer.Option(..., "--manifest", "-m", exists=True, help="Path to timeline_manifest.json."),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", "-o", help="Output workspace directory."),
    brief: Optional[Path] = typer.Option(None, "--brief", "-b", exists=True, help="Optional creative-brief.yaml."),
    tokens: Optional[Path] = typer.Option(None, "--tokens", exists=True, help="Optional tokens.css override."),
    theme: Optional[Literal["dark", "light"]] = typer.Option(None, "--theme", help="Theme override."),
    media_dir: Optional[Path] = typer.Option(None, "--media-dir", exists=True, help="Optional media lookup dir."),
    catalog: Path = typer.Option(DEFAULT_CATALOG_PATH, "--catalog", help="Asset catalog path."),
) -> None:
    """Stage 2: Validate Storyboard, compile HyperFrames project, lint, and generate Contact Sheet."""
    brief_obj = load_creative_brief(brief) if brief is not None else None
    cat_obj = load_asset_catalog(catalog) if catalog.exists() else None
    sb = validate_storyboard(storyboard_json, brief=brief_obj, catalog=cat_obj)

    resolved_theme = theme or (brief_obj.theme if brief_obj is not None else sb.theme)
    resolved_tokens = _resolve_tokens_css(
        tokens, catalog, brief_obj.token_kit if brief_obj is not None else sb.token_kit
    )
    work = out_dir or storyboard_json.parent
    proj_dir = work / "hyperframes_project"
    compile_hyperframes_project(
        storyboard_path=storyboard_json,
        manifest_path=manifest,
        out_project_dir=proj_dir,
        tokens_css=resolved_tokens,
        theme=resolved_theme,
        media_dir=media_dir,
    )
    lint_report = run_hyperframes_lint(proj_dir)
    if not lint_report.get("ok") or int(lint_report.get("errorCount", 0)) > 0:
        typer.echo(f"HyperFrames lint failed: {json.dumps(lint_report, indent=2)}", err=True)
        raise typer.Exit(code=1)

    cs_res = render_contact_sheet(proj_dir, storyboard_json, work / "contact_sheet")
    typer.echo(
        f"Rendered Contact Sheet ({len(cs_res.stills)} stills) -> {cs_res.contact_sheet_path}"
    )


@app.command("hf-render")
def hf_render_cmd(
    storyboard_json: Path = typer.Argument(..., exists=True, help="Path to storyboard.json."),
    manifest: Path = typer.Option(..., "--manifest", "-m", exists=True, help="Path to timeline_manifest.json."),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Rendered output file path."),
    project_dir: Optional[Path] = typer.Option(None, "--project-dir", help="Optional compiled HyperFrames project dir."),
    brief: Optional[Path] = typer.Option(None, "--brief", "-b", exists=True, help="Optional creative-brief.yaml."),
    tokens: Optional[Path] = typer.Option(None, "--tokens", exists=True, help="Optional tokens.css override."),
    theme: Optional[Literal["dark", "light"]] = typer.Option(None, "--theme"),
    media_dir: Optional[Path] = typer.Option(None, "--media-dir", exists=True),
    fmt: str = typer.Option("mp4", "--format", help="Output format: mp4, webm, mov, gif."),
    quality: str = typer.Option("looks", "--quality", help="Render quality: draft, looks, delivery."),
    skip_check: bool = typer.Option(False, "--skip-check", help="Skip `hyperframes check` preflight."),
    catalog: Path = typer.Option(DEFAULT_CATALOG_PATH, "--catalog"),
) -> None:
    """Stage 3: Compile HyperFrames project, run lint/check, and render deterministic video."""
    brief_obj = load_creative_brief(brief) if brief is not None else None
    cat_obj = load_asset_catalog(catalog) if catalog.exists() else None
    sb = validate_storyboard(storyboard_json, brief=brief_obj, catalog=cat_obj)

    resolved_theme = theme or (brief_obj.theme if brief_obj is not None else sb.theme)
    resolved_tokens = _resolve_tokens_css(
        tokens, catalog, brief_obj.token_kit if brief_obj is not None else sb.token_kit
    )
    proj = project_dir or (storyboard_json.parent / "hyperframes_project")
    compile_hyperframes_project(
        storyboard_path=storyboard_json,
        manifest_path=manifest,
        out_project_dir=proj,
        tokens_css=resolved_tokens,
        theme=resolved_theme,
        media_dir=media_dir,
    )
    lint_report = run_hyperframes_lint(proj)
    if not lint_report.get("ok") or int(lint_report.get("errorCount", 0)) > 0:
        typer.echo(f"HyperFrames lint failed: {json.dumps(lint_report, indent=2)}", err=True)
        raise typer.Exit(code=1)

    if not skip_check:
        check_report = run_hyperframes_check(proj)
        (proj / "hyperframes_check.json").write_text(json.dumps(check_report, indent=2), encoding="utf-8")
        if not check_report.get("ok"):
            typer.echo(f"HyperFrames check failed: {json.dumps(check_report, indent=2)}", err=True)
            raise typer.Exit(code=1)

    dest = out or (storyboard_json.parent / f"hf_visual.{fmt}")
    rendered = render_hyperframes_video(proj, dest, fmt=fmt, quality=quality)
    typer.echo(f"Rendered HyperFrames video -> {rendered}")


@app.command("qc")
def qc_cmd(
    video: Path = typer.Argument(..., exists=True, help="Rendered MP4 to verify."),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", "-o", help="Directory for qc_report.json and frames."),
    delivery: bool = typer.Option(False, "--delivery", help="Include the 6 Stage 4 Final Delivery checks."),
    run_json: Optional[Path] = typer.Option(None, "--run-json", exists=True, help="Path to run.json for stale_check & waivers."),
    dom_manifest: Optional[Path] = typer.Option(None, "--dom-manifest", exists=True, help="Path to dom_layout_manifest.json."),
    hf_check: Optional[Path] = typer.Option(None, "--hf-check", exists=True, help="Path to hyperframes_check.json."),
    edl: Optional[Path] = typer.Option(None, "--edl", exists=True, help="Path to edl.json for kept_segments and cuts."),
    transcript: Optional[Path] = typer.Option(None, "--transcript", exists=True, help="Path to transcript.json."),
    srt: Optional[Path] = typer.Option(None, "--srt", exists=True, help="Path to captions .srt file."),
    cuts: Optional[str] = typer.Option(None, "--cuts", help="Comma-separated edited-timeline cut timestamps (seconds)."),
    target_lufs: float = typer.Option(-14.0, "--target-lufs"),
    max_true_peak: float = typer.Option(-1.0, "--max-true-peak"),
) -> None:
    """Run the 8 hard-blocking QC gates (plus 6 delivery checks with --delivery)."""
    work = out_dir or video.parent
    dom_data = json.loads(dom_manifest.read_text(encoding="utf-8")) if dom_manifest is not None else None
    hf_data = json.loads(hf_check.read_text(encoding="utf-8")) if hf_check is not None else None
    edl_obj = EditDecisionList.model_validate_json(edl.read_text(encoding="utf-8")) if edl is not None else None
    bundle_obj = (
        TranscriptBundle.model_validate_json(transcript.read_text(encoding="utf-8"))
        if transcript is not None
        else None
    )

    cut_list: list[float] = []
    if cuts:
        cut_list = [float(part.strip()) for part in cuts.split(",") if part.strip()]
    elif edl_obj is not None and len(edl_obj.kept_segments) > 1:
        acc = 0.0
        for seg in edl_obj.kept_segments[:-1]:
            acc += seg.end - seg.start
            cut_list.append(round(acc, 4))

    report = run_qc(
        video_path=video,
        out_dir=work,
        delivery_mode=delivery,
        cut_timestamps=cut_list,
        run_json_path=run_json,
        hyperframes_check_report=hf_data,
        dom_manifest=dom_data,
        kept_segments=edl_obj.kept_segments if edl_obj is not None else None,
        transcript_bundle=bundle_obj,
        srt_path=srt,
        target_lufs=target_lufs,
        max_true_peak=max_true_peak,
    )
    status_word = "PASSED" if report.passed else "FAILED"
    typer.echo(
        f"QC {status_word} ({len(report.gates)} gates, failed={report.failed_gates}) -> {report.report_path}"
    )
    if not report.passed:
        raise typer.Exit(code=1)


@app.command("audio-mix")
def audio_mix_cmd(
    video: Path = typer.Argument(..., exists=True, help="Picture-locked video to mix."),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", "-o", help="Output directory."),
    picture_locked: bool = typer.Option(False, "--picture-locked", help="Confirm Stage 3 Picture Lock."),
    run_json: Optional[Path] = typer.Option(None, "--run-json", exists=True, help="Check Picture Lock gate in run.json."),
    music: Optional[Path] = typer.Option(None, "--music", exists=True, help="Optional local licensed background music."),
    sfx_json: Optional[Path] = typer.Option(None, "--sfx-json", exists=True, help="Optional JSON list of AudioSfxCue items."),
    target_lufs: float = typer.Option(-14.0, "--target-lufs"),
    true_peak: float = typer.Option(-1.0, "--true-peak"),
    sound_design: int = typer.Option(1, "--sound-design", min=0, max=5),
    manifest: Optional[Path] = typer.Option(None, "--manifest", exists=True, help="Optional timeline_manifest.json for SRT."),
    out_srt: Optional[Path] = typer.Option(None, "--out-srt", help="Optional .srt output path."),
) -> None:
    """Stage 4: Layer ducked music and rule-governed SFX after Picture Lock and normalize loudness."""
    locked = picture_locked
    if not locked and run_json is not None:
        state = RunState.load(run_json)
        locked = state.gates["picture_lock"].status == "approved"

    sfx_list: list[AudioSfxCue] = []
    if sfx_json is not None:
        raw_cues = json.loads(sfx_json.read_text(encoding="utf-8"))
        sfx_list = [AudioSfxCue.model_validate(item) for item in raw_cues]

    work = out_dir or video.parent
    try:
        res = mix_locked_audio(
            video_path=video,
            out_dir=work,
            picture_locked=locked,
            music_path=music,
            sfx_cues=sfx_list,
            target_lufs=target_lufs,
            true_peak_dbtp=true_peak,
            sound_design_level=sound_design,
        )
    except PictureLockRequiredError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if manifest is not None:
        tm = TimelineManifest.model_validate_json(manifest.read_text(encoding="utf-8"))
        srt_dest = out_srt or (work / "captions.srt")
        export_srt(tm.captions, srt_dest)
        typer.echo(f"Exported SRT -> {srt_dest}")

    typer.echo(
        f"Mixed audio ({res.measured_lufs:.2f} LUFS, {res.measured_true_peak_dbtp:.2f} dBTP) -> {res.final_mixed_path}"
    )


@app.command("taste-log")
def taste_log_cmd(
    video_id: str = typer.Option(..., "--video-id", help="Video identifier."),
    timestamp: str = typer.Option(..., "--timestamp", help="Timestamp string (e.g. 00:14.200)."),
    category: ReviewCategory = typer.Option(..., "--category", help="sifting|layout|motion|captions|audio|pacing"),
    tag: ReviewTag = typer.Option(..., "--tag", help="DO|DON'T|PREFERENCE|NON-NEGOTIABLE"),
    note: str = typer.Option(..., "--note", help="Concrete review observation."),
    entry_date: Optional[str] = typer.Option(None, "--date", help="ISO YYYY-MM-DD date (defaults to today)."),
    log_path: Path = typer.Option(EDITING_SYSTEM_DIR / "memory" / "review_log.jsonl", "--log"),
    profile_path: Path = typer.Option(EDITING_SYSTEM_DIR / "memory" / "taste_profile.md", "--profile"),
) -> None:
    """Append a tagged review note to review_log.jsonl and refresh taste_profile.md."""
    entry = ReviewLogEntry(
        date=entry_date or dt_date.today().isoformat(),
        video_id=video_id,
        timestamp=timestamp,
        category=category,
        tag=tag,
        note=note,
    )
    append_review_note(log_path, entry)
    entries = load_review_log(log_path)
    render_taste_profile_md(entries, profile_path)
    proposals = find_promotion_candidates(entries)
    typer.echo(
        f"Logged {tag} [{category}] note ({len(entries)} total). Promotion candidates: {len(proposals)}"
    )


@app.command("taste-review")
def taste_review_cmd(
    log_path: Path = typer.Option(EDITING_SYSTEM_DIR / "memory" / "review_log.jsonl", "--log"),
    profile_path: Path = typer.Option(EDITING_SYSTEM_DIR / "memory" / "taste_profile.md", "--profile"),
    min_videos: int = typer.Option(3, "--min-videos", min=1),
    refresh: bool = typer.Option(False, "--refresh", help="Re-render Section 3 of taste_profile.md."),
) -> None:
    """Inspect Taste Profile entries and report >=3-video rule promotion proposals (read-only on rules)."""
    entries = load_review_log(log_path)
    if refresh:
        render_taste_profile_md(entries, profile_path)
    proposals = find_promotion_candidates(entries, min_videos=min_videos)
    typer.echo(f"Loaded {len(entries)} review note(s); found {len(proposals)} promotion proposal(s):")
    for idx, prop in enumerate(proposals, start=1):
        typer.echo(f"  {idx}. {prop.proposed_rule_summary}")


@app.command("catalog-check")
def catalog_check_cmd(
    catalog: Path = typer.Option(DEFAULT_CATALOG_PATH, "--catalog", help="Path to asset catalog.json."),
) -> None:
    """Validate editing_system/assets/catalog.json schema, IDs, classes, and active file paths."""
    errors = validate_asset_catalog(catalog)
    if errors:
        for err in errors:
            typer.echo(f"ERROR: {err}", err=True)
        raise typer.Exit(code=1)
    cat = load_asset_catalog(catalog)
    typer.echo(f"OK: {len(cat.assets)} assets validated in {catalog}")


if __name__ == "__main__":
    app()
