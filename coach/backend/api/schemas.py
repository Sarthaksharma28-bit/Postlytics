"""
API Schemas — Pydantic models for request/response validation
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class VisualMetrics(BaseModel):
    brightness_score: float          # 0–100
    brightness_label: str            # "good" | "overexposed" | "too_dark"
    contrast_score: float
    contrast_label: str              # "good" | "low_contrast" | "high_contrast"
    noise_level: float               # 0–100
    noise_label: str
    stability_score: float           # 0–100 (higher = more stable)
    stability_label: str             # "stable" | "minor_shake" | "shaky"
    framing_label: str               # "good" | "subject_too_small" | "subject_off_center"
    motion_energy: float             # 0–100


class HookAnalysis(BaseModel):
    has_strong_hook: bool
    motion_intensity: float
    scene_change_detected: bool
    subject_visible: bool
    hook_score: float                # 0–10
    hook_assessment: str             # human-readable summary


class AudioMetrics(BaseModel):
    audio_type: str                  # "music" | "speech" | "speech+music" | "ambient" | "none"
    rms_loudness: float              # dB
    volume_label: str                # "good" | "too_quiet" | "too_loud"
    tempo_bpm: Optional[float]
    spectral_centroid: float
    noise_level: float
    noise_label: str                 # "clean" | "noisy"
    silence_percentage: float
    clipping_detected: bool
    issues: List[str]                # list of detected audio issues


class CoachingPoint(BaseModel):
    category: str                    # e.g. "Audio", "Framing", "Hook"
    issue: str                       # specific detected issue
    feedback: str                    # creator-style advice
    priority: str                    # "high" | "medium" | "low"


class CoachingFeedback(BaseModel):
    creator_persona: str             # e.g. "professional music creator"
    what_works_well: List[str]
    what_needs_improvement: List[CoachingPoint]
    overall_score: float             # 0–10
    overall_summary: str


class CaptionSet(BaseModel):
    engaging: str
    question_based: str
    viral_short: str
    story_style: str


class ThumbnailResult(BaseModel):
    frame_index: int
    timestamp_seconds: float
    url: str                         # URL to download the frame
    reason: str                      # why this frame was selected
    overlay_text_suggestion: Optional[str]


class AnalysisResult(BaseModel):
    session_id: str
    video_description: str
    content_category: str
    duration_seconds: float
    visual_analysis: VisualMetrics
    hook_analysis: HookAnalysis
    audio_analysis: AudioMetrics
    coaching_feedback: CoachingFeedback
    captions: CaptionSet
    hashtags: List[str]
    thumbnail: ThumbnailResult
