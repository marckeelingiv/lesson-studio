"""Domain validation, asset catalog, storyboard, and run-state tracking for the Editing System."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EDITING_SYSTEM_DIR = REPO_ROOT / "editing_system"
DEFAULT_CATALOG_PATH = EDITING_SYSTEM_DIR / "assets" / "catalog.json"
DEFAULT_PRESETS_DIR = EDITING_SYSTEM_DIR / "briefs" / "presets"
DEFAULT_BRIEF_TEMPLATE_PATH = EDITING_SYSTEM_DIR / "briefs" / "creative-brief.template.yaml"

SceneLayout = Literal["Full Screen", "Panel", "Centre", "Full Graphic", "Circle"]
TransitionType = Literal["subtle", "swipe", "zoom", "film_burn"]
AssetClass = Literal["tokens", "layouts", "frameworks", "heroes", "motion", "graphics", "audio"]
AspectRatio = Literal["16:9", "9:16", "any"]
GateName = Literal["rough_cut", "contact_sheet", "picture_lock", "final_delivery"]
UpstreamKey = Literal["source", "transcript", "otio", "storyboard", "tokens"]

CANONICAL_GATES: tuple[GateName, ...] = (
    "rough_cut",
    "contact_sheet",
    "picture_lock",
    "final_delivery",
)

UPSTREAM_STALE_ARTIFACTS: dict[UpstreamKey, tuple[str, ...]] = {
    "source": (
        "transcript",
        "otio",
        "cut_audit",
        "rough_cut",
        "storyboard",
        "contact_sheet",
        "visual_plates",
        "audio_mix",
        "captions",
        "final_delivery",
        "qc_report",
    ),
    "transcript": (
        "otio",
        "cut_audit",
        "rough_cut",
        "storyboard",
        "contact_sheet",
        "visual_plates",
        "audio_mix",
        "captions",
        "final_delivery",
        "qc_report",
    ),
    "otio": (
        "rough_cut",
        "storyboard",
        "contact_sheet",
        "visual_plates",
        "audio_mix",
        "captions",
        "final_delivery",
        "qc_report",
    ),
    "storyboard": (
        "contact_sheet",
        "visual_plates",
        "audio_mix",
        "captions",
        "final_delivery",
        "qc_report",
    ),
    "tokens": (
        "contact_sheet",
        "visual_plates",
        "final_delivery",
        "qc_report",
    ),
}

UPSTREAM_STALE_GATES: dict[UpstreamKey, tuple[GateName, ...]] = {
    "source": ("rough_cut", "contact_sheet", "picture_lock", "final_delivery"),
    "transcript": ("rough_cut", "contact_sheet", "picture_lock", "final_delivery"),
    "otio": ("rough_cut", "contact_sheet", "picture_lock", "final_delivery"),
    "storyboard": ("contact_sheet", "picture_lock", "final_delivery"),
    "tokens": ("contact_sheet", "picture_lock", "final_delivery"),
}

GATE_CLEARS_ARTIFACTS: dict[GateName, tuple[str, ...]] = {
    "rough_cut": ("cut_audit", "rough_cut"),
    "contact_sheet": ("contact_sheet",),
    "picture_lock": ("visual_plates", "qc_report"),
    "final_delivery": ("audio_mix", "captions", "final_delivery", "qc_report"),
}


def _reject_bool(value: Any) -> Any:
    """Reject booleans before Pydantic coerces True/False to 1/0."""
    if isinstance(value, bool):
        raise ValueError("Boolean is not allowed where an integer is required.")
    return value


StrictIntField = Annotated[int, BeforeValidator(_reject_bool)]


def _require_non_empty(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty.")
    return value


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override onto base without mutating inputs."""
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


# ---------------------------------------------------------------------------
# Creative Brief models
# ---------------------------------------------------------------------------


class ReferenceVideo(BaseModel):
    """Good or not-good reference video example in a Creative Brief."""

    model_config = ConfigDict(extra="forbid")

    label: Literal["good", "not_good"]
    url_or_path: str = ""
    emulate: list[str] = Field(default_factory=list)
    notes: str = ""


class FeelSettings(BaseModel):
    """Creative Engine Room intensity dials and transition bounds."""

    model_config = ConfigDict(extra="forbid")

    animation: StrictIntField = Field(default=2, ge=1, le=5)
    visuals: StrictIntField = Field(default=2, ge=1, le=5)
    sound_design: StrictIntField = Field(default=1, ge=1, le=5)
    pacing: Literal["deliberate", "steady", "punchy"] = "steady"
    max_transitions: StrictIntField = Field(default=3, ge=0, le=3)
    allowed_transitions: list[TransitionType] = Field(
        default_factory=lambda: ["subtle", "swipe", "zoom"]
    )


class BriefMoment(BaseModel):
    """Timestamped spoken cue to emphasize visually in the Storyboard."""

    model_config = ConfigDict(extra="forbid")

    cue: str = Field(..., min_length=1)
    intent: str = ""
    preferred_layout: SceneLayout | None = None


class StartingVisuals(BaseModel):
    """Concrete starting visual anchors so visual generation avoids generic metaphors."""

    model_config = ConfigDict(extra="forbid")

    hero_template_goal: str = ""
    anchors: list[str] = Field(default_factory=list)


class DeliveryTarget(BaseModel):
    """Target frame geometry, loudness, and caption settings."""

    model_config = ConfigDict(extra="forbid")

    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    width: StrictIntField = Field(default=1920, gt=0)
    height: StrictIntField = Field(default=1080, gt=0)
    fps: StrictIntField = Field(default=30, gt=0)
    loudness_lufs: float = Field(default=-14.0, le=0.0)
    true_peak_dbtp: float = Field(default=-1.0, le=0.0)
    captions_enabled: bool = True


class CreativeBrief(BaseModel):
    """Per-video Creative Engine Room specification."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    video_id: str = ""
    title: str = ""
    audience: str = ""
    communication_goal: str = ""
    entry_mode: Literal["sift", "clean_a_roll"] = "sift"
    references: list[ReferenceVideo] = Field(default_factory=list, max_length=2)
    feel: FeelSettings = Field(default_factory=FeelSettings)
    moments: list[BriefMoment | str] = Field(default_factory=list)
    starting_visuals: StartingVisuals = Field(default_factory=StartingVisuals)
    delivery_target: DeliveryTarget = Field(default_factory=DeliveryTarget)
    token_kit: str = "tok-engineering-editorial"
    theme: Literal["dark", "light"] = "dark"
    preset: str | None = "clean-editorial"

    @field_validator("references")
    @classmethod
    def _validate_reference_limit(cls, value: list[ReferenceVideo]) -> list[ReferenceVideo]:
        if len(value) > 2:
            raise ValueError("Creative Brief allows at most 2 reference videos.")
        return value


def _load_preset_defaults(preset_name: str, presets_dir: Path, required: bool) -> dict[str, Any]:
    preset_path = presets_dir / f"{preset_name}.yaml"
    if not preset_path.exists():
        if required:
            raise FileNotFoundError(f"Creative Brief preset not found: {preset_path}")
        return {}
    raw = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Preset YAML must be a mapping: {preset_path}")
    # Presets carry metadata keys (preset_id, description) outside CreativeBrief.
    return {k: v for k, v in raw.items() if k not in {"preset_id", "description"}}


def load_creative_brief(path: Path, presets_dir: Path | None = None) -> CreativeBrief:
    """Load a Creative Brief YAML, merge matching preset defaults underneath, and validate."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Creative Brief YAML must be a mapping: {path}")

    resolved_presets_dir = presets_dir if presets_dir is not None else DEFAULT_PRESETS_DIR
    preset_explicit = "preset" in raw
    preset_name = raw.get("preset", "clean-editorial")

    merged = dict(raw)
    if isinstance(preset_name, str) and preset_name.strip():
        preset_defaults = _load_preset_defaults(
            preset_name.strip(),
            resolved_presets_dir,
            required=preset_explicit,
        )
        merged = _deep_merge(preset_defaults, raw)
    elif preset_name is not None and not isinstance(preset_name, str):
        raise ValueError("Creative Brief 'preset' must be a string or null.")

    return CreativeBrief.model_validate(merged)


def init_creative_brief(
    dest: Path,
    video_id: str,
    title: str,
    preset: str = "clean-editorial",
) -> Path:
    """Initialize a validated creative-brief.yaml from the template and preset."""
    _require_non_empty(video_id, "video_id")
    _require_non_empty(title, "title")

    template_raw = yaml.safe_load(DEFAULT_BRIEF_TEMPLATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(template_raw, dict):
        raise ValueError(f"Invalid Creative Brief template: {DEFAULT_BRIEF_TEMPLATE_PATH}")

    data = dict(template_raw)
    if preset:
        preset_defaults = _load_preset_defaults(preset, DEFAULT_PRESETS_DIR, required=True)
        data = _deep_merge(data, preset_defaults)

    data["video_id"] = video_id
    data["title"] = title
    data["preset"] = preset or None

    validated = CreativeBrief.model_validate(data)
    out_path = dest / "creative-brief.yaml" if dest.exists() and dest.is_dir() else dest
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(validated.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )
    return out_path


# ---------------------------------------------------------------------------
# Asset Catalog models
# ---------------------------------------------------------------------------


class AssetEntry(BaseModel):
    """Single reusable asset registered in editing_system/assets/catalog.json."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(..., pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    class_: AssetClass = Field(..., alias="class")
    subtype: str = Field(..., min_length=1)
    aspect_ratios: list[AspectRatio] = Field(..., min_length=1)
    tags: list[Annotated[str, Field(min_length=1)]]
    license: str = Field(..., min_length=1)
    attribution: str
    path: str = Field(..., min_length=1)
    status: Literal["active", "planned"]
    usage_rules: str = Field(..., min_length=1)


class AssetCatalog(BaseModel):
    """Typed registry of reusable editing assets across 7 asset classes."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    assets: list[AssetEntry]

    @field_validator("schema_version", mode="before")
    @classmethod
    def _reject_bool_schema_version(cls, value: Any) -> Any:
        return _reject_bool(value)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> AssetCatalog:
        seen: set[str] = set()
        duplicates: list[str] = []
        for entry in self.assets:
            if entry.id in seen and entry.id not in duplicates:
                duplicates.append(entry.id)
            seen.add(entry.id)
        if duplicates:
            raise ValueError(f"Duplicate asset IDs in catalog: {', '.join(duplicates)}")
        return self

    def get(self, asset_id: str) -> AssetEntry | None:
        """Return the AssetEntry matching asset_id, or None."""
        for entry in self.assets:
            if entry.id == asset_id:
                return entry
        return None

    def has_id(self, asset_id: str) -> bool:
        """Return True when asset_id is registered in the catalog."""
        return any(entry.id == asset_id for entry in self.assets)

    def by_class(self, asset_class: AssetClass) -> list[AssetEntry]:
        """Return all assets belonging to asset_class."""
        return [entry for entry in self.assets if entry.class_ == asset_class]


def load_asset_catalog(catalog_path: Path = DEFAULT_CATALOG_PATH) -> AssetCatalog:
    """Load and validate an asset catalog JSON file."""
    return AssetCatalog.model_validate_json(catalog_path.read_text(encoding="utf-8"))


def _resolve_catalog_asset_path(base_dir: Path, rel_path: str) -> Path | None:
    """Resolve rel_path under base_dir; return None if it escapes base_dir."""
    rel = Path(rel_path)
    if rel.is_absolute():
        return None
    resolved_base = base_dir.resolve()
    resolved_target = (resolved_base / rel).resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError:
        return None
    return resolved_target


def validate_asset_catalog(catalog_path: Path = DEFAULT_CATALOG_PATH) -> list[str]:
    """Validate catalog JSON, schema rules, unique IDs, and active file existence."""
    if not catalog_path.is_file():
        return [f"Catalog file not found: {catalog_path}"]

    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Invalid catalog JSON: {exc}"]

    errors: list[str] = []
    if not isinstance(raw, dict):
        return ["Catalog root must be a JSON object."]

    for required_key in ("schema_version", "assets"):
        if required_key not in raw:
            errors.append(f"Missing required top-level key: {required_key}")

    try:
        catalog = AssetCatalog.model_validate(raw)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", ()))
            msg = err.get("msg", "validation error")
            errors.append(f"{loc}: {msg}" if loc else msg)
        return errors

    base_dir = catalog_path.parent
    for entry in catalog.assets:
        resolved = _resolve_catalog_asset_path(base_dir, entry.path)
        if resolved is None:
            errors.append(f"{entry.id}: asset path escapes catalog directory: {entry.path}")
        elif entry.status == "active" and not resolved.exists():
            errors.append(f"{entry.id}: active asset path missing: {entry.path}")

    return errors


# ---------------------------------------------------------------------------
# Storyboard models
# ---------------------------------------------------------------------------


class StoryboardBeat(BaseModel):
    """Single beat in storyboard.json aligned for HyperFrames composition."""

    id: str
    start: float = Field(..., ge=0.0)
    duration: float = Field(..., gt=0.0)
    scene_layout: SceneLayout
    title: str = ""
    subtitle: str = ""
    body: str = ""
    items: list[str] = Field(default_factory=list)
    transition: TransitionType | None = None
    asset_ids: list[str] = Field(default_factory=list)
    reason: str
    purpose: str
    intention: str
    media_src: str | None = None
    camera_src: str | None = None
    visual_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("start", "duration")
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Timing values must be finite numbers.")
        return value

    @field_validator("id", "reason", "purpose", "intention")
    @classmethod
    def _validate_non_empty(cls, value: str, info: Any) -> str:
        return _require_non_empty(value, info.field_name)

    @property
    def end(self) -> float:
        """Beat end timestamp in seconds."""
        return self.start + self.duration


class Storyboard(BaseModel):
    """Beat-by-beat visual plan mapping Rough Cut timecodes to Scene Layouts."""

    video_id: str
    theme: Literal["dark", "light"] = "dark"
    token_kit: str = "tok-engineering-editorial"
    beats: list[StoryboardBeat] = Field(default_factory=list)

    @field_validator("video_id", "token_kit")
    @classmethod
    def _validate_non_empty(cls, value: str, info: Any) -> str:
        return _require_non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _validate_beats(self) -> Storyboard:
        seen_ids: set[str] = set()
        prev_beat: StoryboardBeat | None = None
        transition_count = 0

        for beat in self.beats:
            if beat.id in seen_ids:
                raise ValueError(f"Duplicate beat id: {beat.id}")
            seen_ids.add(beat.id)

            if prev_beat is not None:
                if beat.start < prev_beat.start:
                    raise ValueError(
                        f"Beats must be strictly ordered: '{beat.id}' starts at {beat.start} "
                        f"before '{prev_beat.id}' ({prev_beat.start})."
                    )
                if beat.start + 1e-9 < prev_beat.end:
                    raise ValueError(
                        f"Beats must not overlap: '{beat.id}' starts at {beat.start} "
                        f"before '{prev_beat.id}' ends ({prev_beat.end})."
                    )
            prev_beat = beat

            if beat.transition is not None:
                transition_count += 1

        if transition_count > 3:
            raise ValueError(
                f"Storyboard uses {transition_count} transitions, exceeding hard ceiling of 3."
            )
        return self

    @property
    def transition_count(self) -> int:
        """Total number of transitions declared across beats."""
        return sum(1 for beat in self.beats if beat.transition is not None)

    def validate_against(
        self,
        brief: CreativeBrief | None = None,
        catalog: AssetCatalog | None = None,
    ) -> None:
        """Validate transition limits against brief and asset_ids against catalog."""
        if brief is not None:
            cap = min(brief.feel.max_transitions, 3)
            if self.transition_count > cap:
                raise ValueError(
                    f"Storyboard uses {self.transition_count} transitions, exceeding brief cap {cap}."
                )
            allowed = set(brief.feel.allowed_transitions)
            for beat in self.beats:
                if beat.transition is not None and beat.transition not in allowed:
                    raise ValueError(
                        f"Beat '{beat.id}' uses disallowed transition '{beat.transition}' "
                        f"(allowed: {sorted(allowed)})."
                    )

        if catalog is not None:
            known_ids = {entry.id for entry in catalog.assets}
            for beat in self.beats:
                missing = [asset_id for asset_id in beat.asset_ids if asset_id not in known_ids]
                if missing:
                    raise ValueError(
                        f"Beat '{beat.id}' references unknown asset_ids: {', '.join(missing)}"
                    )


def validate_storyboard(
    storyboard_path: Path,
    brief: CreativeBrief | None = None,
    catalog: AssetCatalog | None = None,
) -> Storyboard:
    """Load storyboard JSON and validate structure, brief limits, and catalog references."""
    storyboard = Storyboard.model_validate_json(storyboard_path.read_text(encoding="utf-8"))
    storyboard.validate_against(brief=brief, catalog=catalog)
    return storyboard


# ---------------------------------------------------------------------------
# RunState (run.json) tracker
# ---------------------------------------------------------------------------


def compute_sha256(path: Path) -> str:
    """Compute hex SHA-256 digest for a file without loading it all into memory."""
    if not path.is_file():
        raise FileNotFoundError(f"Cannot hash missing file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


class InputHashRecord(BaseModel):
    """Tracked SHA-256 hash of a pipeline input file."""

    path: str
    sha256: str


class GateApprovalRecord(BaseModel):
    """Human gate approval status and checkpoint artifact hashes."""

    status: Literal["pending", "approved", "rejected"] = "pending"
    approved_by: str = ""
    timestamp: str = ""
    artifact_hashes: dict[str, str] = Field(default_factory=dict)


def _default_gates() -> dict[str, GateApprovalRecord]:
    return {gate: GateApprovalRecord() for gate in CANONICAL_GATES}


class RunState(BaseModel):
    """Persistent run.json state for dependency hashing, human gates, and waivers."""

    run_id: str
    video_id: str
    input_hashes: dict[str, InputHashRecord] = Field(default_factory=dict)
    gates: dict[str, GateApprovalRecord] = Field(default_factory=_default_gates)
    waivers: list[dict[str, Any]] = Field(default_factory=list)
    stale_artifacts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ensure_canonical_gates(self) -> RunState:
        for gate in CANONICAL_GATES:
            self.gates.setdefault(gate, GateApprovalRecord())
        return self

    def record_input_hash(self, key: str, path: Path) -> InputHashRecord:
        """Hash path and mark downstream artifacts/gates stale if an existing hash changed."""
        digest = compute_sha256(path)
        previous = self.input_hashes.get(key)
        record = InputHashRecord(path=str(path), sha256=digest)
        self.input_hashes[key] = record
        if previous is not None and previous.sha256 != digest and key in UPSTREAM_STALE_ARTIFACTS:
            self.mark_stale(key)
        return record

    def mark_stale(self, upstream_key: str) -> list[str]:
        """Mark downstream artifacts stale and reset downstream gates to pending."""
        if upstream_key not in UPSTREAM_STALE_ARTIFACTS:
            raise ValueError(
                f"Unknown upstream key '{upstream_key}'. "
                f"Expected one of: {', '.join(UPSTREAM_STALE_ARTIFACTS)}."
            )

        artifacts = list(UPSTREAM_STALE_ARTIFACTS[upstream_key])  # type: ignore[index]
        for artifact in artifacts:
            if artifact not in self.stale_artifacts:
                self.stale_artifacts.append(artifact)

        for gate in UPSTREAM_STALE_GATES[upstream_key]:  # type: ignore[index]
            self.gates[gate] = GateApprovalRecord(status="pending")

        return artifacts

    def approve_gate(
        self,
        gate: str,
        approved_by: str = "human",
        artifact_paths: dict[str, Path] | None = None,
        artifact_hashes: dict[str, str] | None = None,
        timestamp: str | None = None,
    ) -> GateApprovalRecord:
        """Record approval for a canonical gate and clear resolved stale flags."""
        if gate not in CANONICAL_GATES:
            raise ValueError(
                f"Unknown gate '{gate}'. Expected one of: {', '.join(CANONICAL_GATES)}."
            )

        hashes: dict[str, str] = dict(artifact_hashes or {})
        if artifact_paths:
            for name, artifact_path in artifact_paths.items():
                hashes[name] = compute_sha256(artifact_path)

        record = GateApprovalRecord(
            status="approved",
            approved_by=approved_by,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            artifact_hashes=hashes,
        )
        self.gates[gate] = record

        resolved = set(GATE_CLEARS_ARTIFACTS[gate])  # type: ignore[index]
        self.stale_artifacts = [item for item in self.stale_artifacts if item not in resolved]
        return record

    def save(self, path: Path) -> Path:
        """Persist run state atomically as formatted JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> RunState:
        """Load run state from a run.json file."""
        return cls.model_validate_json(path.read_text(encoding="utf-8"))
