"""Pydantic schemas for transcripts, edit decision lists, and timeline manifests."""

from typing import Literal
from pydantic import BaseModel, Field


class VideoMetadata(BaseModel):
    """Technical metadata extracted via ffprobe."""

    source_path: str
    duration: float
    fps: float
    width: int
    height: int
    has_audio: bool = True


class WordTiming(BaseModel):
    """Single transcribed word with seconds-based timestamps."""

    word: str
    start: float
    end: float
    probability: float = 1.0


class TranscriptSegment(BaseModel):
    """Transcribed speech segment containing word-level timings."""

    id: int
    start: float
    end: float
    text: str
    words: list[WordTiming] = Field(default_factory=list)


class SilenceRegion(BaseModel):
    """Detected silence interval in source audio."""

    start: float
    end: float
    duration: float


class FillerCandidate(BaseModel):
    """Detected filler word or hesitation."""

    word: str
    start: float
    end: float
    segment_id: int


class RetakeCandidate(BaseModel):
    """Detected repeated phrase or false start."""

    segment_id: int
    reason: str
    start: float
    end: float
    text: str


class TranscriptBundle(BaseModel):
    """Complete transcription and signal analysis bundle for planning."""

    source_path: str
    duration: float
    fps: float
    width: int
    height: int
    language: str = "en"
    segments: list[TranscriptSegment] = Field(default_factory=list)
    silences: list[SilenceRegion] = Field(default_factory=list)
    fillers: list[FillerCandidate] = Field(default_factory=list)
    retakes: list[RetakeCandidate] = Field(default_factory=list)


class KeepSegment(BaseModel):
    """Source time range to keep in the edited timeline."""

    id: str
    start: float
    end: float
    reason: str = ""


GraphicType = Literal[
    "lower_third",
    "callout",
    "stat_card",
    "broll_card",
    "slide_card",
    "code_card",
    "cursor_highlight",
]


class GraphicCue(BaseModel):
    """Programmatic motion graphic cue positioned on the edited timeline."""

    id: str
    type: GraphicType
    start: float
    duration: float = 3.0
    title: str
    subtitle: str = ""
    value: str = ""
    x: float | None = None
    y: float | None = None


class EditDecisionList(BaseModel):
    """Structured cut plan and motion graphic cues produced by the editorial planner."""

    source_path: str
    camera_path: str | None = None
    fps: float
    width: int
    height: int
    kept_segments: list[KeepSegment] = Field(default_factory=list)
    graphic_cues: list[GraphicCue] = Field(default_factory=list)
    captions_enabled: bool = True
    summary: str = ""


class RemappedWord(BaseModel):
    """Word timing mapped onto the assembled timeline in milliseconds."""

    text: str
    startMs: int
    endMs: int


class TimelineManifest(BaseModel):
    """Props payload passed to the Remotion renderer."""

    videoFile: str
    cameraFile: str | None = None
    fps: float
    width: int
    height: int
    durationInFrames: int
    captionsEnabled: bool = True
    captions: list[RemappedWord] = Field(default_factory=list)
    graphicCues: list[GraphicCue] = Field(default_factory=list)
