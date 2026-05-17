# -*- coding: utf-8 -*-
"""
Postlytics — Streamlit App
Run: streamlit run app.py
"""

import sys
import os
import uuid
import shutil
import tempfile
from pathlib import Path

import streamlit as st

# ── Load .env file so GEMINI_API_KEY etc. are available ──────────────────────
def _load_env():
    env_path = Path(__file__).resolve().parent / "backend" / ".env"
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip(); v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
_load_env()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Postlytics",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* Global */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1100px; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Section headings ── */
.cc-title {
  font-family: 'Syne', sans-serif;
  font-size: 2.8rem; font-weight: 800;
  letter-spacing: -2px; line-height: 1.05;
  margin-bottom: 0.4rem;
}
.cc-title span { color: #C8FF57; }
.cc-sub { color: rgba(255,255,255,0.5); font-size: 1.05rem; margin-bottom: 2rem; }

/* ── Score ring placeholder ── */
.score-ring-wrap {
  display: flex; align-items: center; gap: 28px;
  background: #0E1218; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px; padding: 28px 32px; margin-bottom: 20px;
}
.score-circle {
  width: 110px; height: 110px; border-radius: 50%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  border: 6px solid;
  flex-shrink: 0;
}
.score-num { font-family: 'Syne', sans-serif; font-size: 2.2rem; font-weight: 800; line-height: 1; }
.score-sub { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.5; }
.score-info { flex: 1; }
.score-info h3 { font-family: 'Syne', sans-serif; font-size: 1.25rem; font-weight: 700; margin-bottom: 6px; }
.score-info .cat-pill {
  display: inline-block;
  background: rgba(87,200,255,0.12); color: #57C8FF;
  border: 1px solid rgba(87,200,255,0.22); border-radius: 100px;
  padding: 3px 14px; font-size: 0.75rem; font-weight: 500;
  margin-bottom: 10px;
}
.score-info .summary { color: rgba(255,255,255,0.5); font-size: 0.88rem; line-height: 1.65; }

/* ── Metric cards ── */
.metric-card {
  background: #0E1218; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px; padding: 20px 22px; height: 100%;
}
.metric-card h4 {
  font-family: 'Syne', sans-serif; font-size: 0.92rem; font-weight: 700;
  margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
}
.mrow {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);
  font-size: 0.83rem;
}
.mrow:last-child { border-bottom: none; }
.mrow-label { color: rgba(255,255,255,0.45); }
.mrow-val { display: flex; align-items: center; gap: 6px; font-weight: 500; }
.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-good  { background: #6BCB77; }
.dot-warn  { background: #FFD93D; }
.dot-bad   { background: #FF4757; }
.dot-neu   { background: rgba(255,255,255,0.25); }

/* ── Hook score bar ── */
.hook-bar-track {
  background: rgba(255,255,255,0.07); border-radius: 100px;
  height: 5px; overflow: hidden; margin-top: 4px;
}
.hook-bar-fill {
  height: 100%; border-radius: 100px;
  background: linear-gradient(90deg, #57C8FF, #C8FF57);
}
.hook-badge {
  display: inline-block; padding: 3px 12px; border-radius: 100px;
  font-size: 0.75rem; font-weight: 600; margin-bottom: 10px;
}
.hook-strong { background: rgba(107,203,119,0.15); color: #6BCB77; border: 1px solid rgba(107,203,119,0.3); }
.hook-weak   { background: rgba(255,71,87,0.12); color: #FF4757; border: 1px solid rgba(255,71,87,0.25); }

/* ── Coaching ── */
.persona-bar {
  display: flex; align-items: center; gap: 10px;
  background: #141920; border-radius: 8px;
  padding: 10px 14px; margin-bottom: 18px;
  font-size: 0.83rem; color: rgba(255,255,255,0.5);
}
.persona-ava {
  width: 28px; height: 28px; border-radius: 50%;
  background: linear-gradient(135deg, #C8FF57, #57C8FF);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; flex-shrink: 0;
}
.works-item {
  display: flex; gap: 10px; font-size: 0.87rem;
  line-height: 1.6; margin-bottom: 8px;
}
.works-check { color: #6BCB77; font-weight: 700; flex-shrink: 0; }

.imp-item {
  border-left: 3px solid;
  padding: 11px 14px; border-radius: 0 8px 8px 0;
  margin-bottom: 10px;
}
.imp-high   { border-color: #FF4757; background: rgba(255,71,87,0.07); }
.imp-medium { border-color: #FFD93D; background: rgba(255,217,61,0.07); }
.imp-low    { border-color: #57C8FF; background: rgba(87,200,255,0.07); }
.imp-header { display: flex; gap: 8px; align-items: center; margin-bottom: 5px; }
.imp-cat { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.07em; text-transform: uppercase; opacity: 0.6; }
.imp-pri {
  font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
  text-transform: uppercase; padding: 2px 8px; border-radius: 100px;
}
.pri-high   { background: rgba(255,71,87,0.2); color: #FF4757; }
.pri-medium { background: rgba(255,217,61,0.2); color: #FFD93D; }
.pri-low    { background: rgba(87,200,255,0.2); color: #57C8FF; }
.imp-text { font-size: 0.83rem; line-height: 1.65; color: rgba(255,255,255,0.55); }

/* ── Captions ── */
.caption-card {
  background: #141920; border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px; padding: 14px 16px; height: 100%;
}
.caption-type {
  font-size: 0.68rem; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; color: #C8FF57; margin-bottom: 8px;
}
.caption-body { font-size: 0.85rem; color: rgba(255,255,255,0.55); line-height: 1.65; }

/* ── Hashtags ── */
.ht-wrap { display: flex; flex-wrap: wrap; gap: 7px; }
.ht-chip {
  background: #141920; border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px; padding: 4px 12px;
  font-size: 0.82rem; color: #57C8FF;
}

/* ── Issues ── */
.issue-line {
  display: flex; gap: 8px; font-size: 0.82rem;
  color: rgba(255,255,255,0.5); line-height: 1.55;
  padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05);
}
.issue-line:last-child { border-bottom: none; }

/* ── Section label ── */
.sec-label {
  font-size: 0.68rem; font-weight: 600; letter-spacing: 0.1em;
  text-transform: uppercase; color: rgba(255,255,255,0.25);
  margin-bottom: 10px;
}

/* ── Divider ── */
.cc-divider { border: none; border-top: 1px solid rgba(255,255,255,0.07); margin: 28px 0; }

/* ── Upload area ── */
[data-testid="stFileUploader"] {
  background: #0E1218 !important;
  border: 2px dashed rgba(255,255,255,0.12) !important;
  border-radius: 16px !important;
  padding: 20px !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: #C8FF57 !important;
}

/* ── Progress ── */
[data-testid="stProgress"] > div > div {
  background: #C8FF57 !important;
}

/* ── Buttons ── */
.stButton > button {
  background: #C8FF57 !important; color: #080B10 !important;
  font-family: 'Syne', sans-serif !important; font-weight: 800 !important;
  font-size: 1rem !important; border: none !important;
  border-radius: 12px !important; padding: 14px 32px !important;
  width: 100% !important; transition: all 0.2s ease !important;
}
.stButton > button:hover { box-shadow: 0 6px 24px rgba(200,255,87,0.35) !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
  background: #0E1218 !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 12px !important;
}

/* ── Background ── */
.stApp { background: #080B10; }
</style>
""", unsafe_allow_html=True)

# ── Resolve backend directory (works regardless of cwd) ──────────────────────
BACKEND_DIR = Path(__file__).resolve().parent / "backend"


def _ensure_backend_on_path():
    """Insert backend/ into sys.path so `modules.*` imports work."""
    backend_str = str(BACKEND_DIR)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)


# Call immediately at import time AND inside cached loader (cache may run in
# a different context where the mutation hasn't been seen yet).
_ensure_backend_on_path()


# ── Lazy imports with graceful fallback ──────────────────────────────────────
@st.cache_resource
def load_modules():
    """Load backend modules once. Returns dict of classes or {'error': msg}."""
    _ensure_backend_on_path()
    _load_env()

    try:
        from modules.video_processor import VideoProcessor
        from modules.vision_analyzer import VisionAnalyzer
        from modules.audio_analyzer import AudioAnalyzer
        from modules.content_understanding import ContentUnderstandingModule
        from modules.creator_coach import CreatorCoachModule
        from modules.caption_generator import CaptionGenerator
        from modules.hashtag_generator import HashtagGenerator
        from modules.thumbnail_selector import ThumbnailSelector

        # ── Initialise Gemini client at startup so model is auto-detected once
        # and the model name is logged before any analysis runs.
        gemini_model_label = "not configured"
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            try:
                from modules.gemini_client import get_model, get_model_name
                get_model()   # triggers auto-detection + print
                gemini_model_label = get_model_name()
            except Exception as e:
                gemini_model_label = f"ERROR: {e}"
        print(f"[CreatorCoach] Gemini model: {gemini_model_label}")

        return {
            "VideoProcessor": VideoProcessor,
            "VisionAnalyzer": VisionAnalyzer,
            "AudioAnalyzer": AudioAnalyzer,
            "ContentUnderstanding": ContentUnderstandingModule,
            "CreatorCoach": CreatorCoachModule,
            "CaptionGenerator": CaptionGenerator,
            "HashtagGenerator": HashtagGenerator,
            "ThumbnailSelector": ThumbnailSelector,
            "gemini_model": gemini_model_label,
        }
    except ImportError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected error loading modules: {e}"}


# ── Helpers ───────────────────────────────────────────────────────────────────
def score_color(score: float) -> str:
    if score >= 8: return "#6BCB77"
    if score >= 6: return "#C8FF57"
    if score >= 4: return "#FFD93D"
    return "#FF4757"

def status_dot(label: str) -> str:
    good = {"good", "stable", "clean", "yes", "true"}
    bad  = {"shaky", "noisy", "too_dark", "overexposed", "too_loud", "too_quiet",
            "clipping", "subject_too_small", "subject_off_center", "no", "false"}
    l = label.lower()
    if l in good:   return '<div class="dot dot-good"></div>'
    if l in bad:    return '<div class="dot dot-bad"></div>'
    if "warn" in l or "minor" in l or "moderate" in l: return '<div class="dot dot-warn"></div>'
    return '<div class="dot dot-neu"></div>'

def mrow(label: str, value: str, status: str = "neutral") -> str:
    dot = status_dot(status)
    return f'<div class="mrow"><span class="mrow-label">{label}</span><span class="mrow-val">{dot}{value}</span></div>'

def priority_class(p: str) -> str:
    return {"high": "imp-high", "medium": "imp-medium", "low": "imp-low"}.get(p, "imp-low")

def priority_badge(p: str) -> str:
    return f'<span class="imp-pri pri-{p}">{p}</span>'


# ── Analysis pipeline ─────────────────────────────────────────────────────────
def run_analysis(uploaded_file) -> dict:
    """
    Full pipeline per architecture spec:

      [OpenCV]      Extract 6 evenly-spaced frames (10/25/40/55/70/90% positions)
      [FFmpeg]      Extract audio track
      [OpenCV]      Measure visual metrics: brightness, contrast, stability, noise, framing
      [OpenCV]      Measure hook: motion, scene change, subject visibility
      [Librosa]     Measure audio: volume, clipping, BPM, noise, silence
      [YOLOv8]      Detect objects in all frames (guitar, microphone, basketball, etc.)
      [Gemini]      Multi-frame vision: ALL 6 frames sent together in one request
                    → video_description, primary_activity, detected_objects, environment
      [ActivityDet] Fuse Gemini output + YOLO objects → accurate category
      [Gemini]      Write niche-specific coaching from measured issues
      [Gemini]      Generate captions + hashtags            ─ parallel
      [OpenCV]      Select best thumbnail frame
    """
    import concurrent.futures

    _load_env()

    mods = load_modules()
    if "error" in mods:
        st.error(
            f"**Backend modules failed to load.**\n\n"
            f"Error: `{mods['error']}`\n\n"
            f"Expected backend at: `{BACKEND_DIR}`\n\n"
            f"Make sure `backend/modules/` exists relative to `app.py`."
        )
        st.stop()

    # ── Save uploaded file ────────────────────────────────────────────────────
    session_id = str(uuid.uuid4())
    session_dir = Path(tempfile.mkdtemp()) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(uploaded_file.name).suffix or ".mp4"
    video_path = session_dir / f"video{suffix}"
    with open(video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    progress = st.progress(0)
    status   = st.empty()

    def step(pct, msg):
        progress.progress(pct)
        status.markdown(f"**⏳ {msg}**")

    # ── STEP 1: Extract 6 frames at 10/25/40/55/70/90% + audio ──────────────
    step(0.05, "Extracting 6 frames from video & audio track…")
    processor  = mods["VideoProcessor"](session_dir)
    video_meta = processor.process(video_path)
    frames     = video_meta["frames"]
    audio_path = video_meta["audio_path"]
    duration   = video_meta["duration"]

    # ── STEP 2: OpenCV visual metrics (no AI) ────────────────────────────────
    step(0.12, "Measuring visual quality: brightness, contrast, stability, framing…")
    visual_metrics = processor.analyze_visual_quality(frames)
    hook_analysis  = processor.analyze_hook(frames[:min(3, len(frames))])

    # ── STEP 3: PARALLEL — YOLOv8 object detection + Librosa audio ───────────
    step(0.20, "Running YOLOv8 object detection + audio analysis in parallel…")

    yolo_results  = {}
    audio_metrics = {}

    def run_yolo():
        _load_env()
        _ensure_backend_on_path()
        from modules.object_detector import ObjectDetector
        return ObjectDetector().detect(frames)

    def run_librosa():
        return mods["AudioAnalyzer"]().analyze(audio_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_yolo    = executor.submit(run_yolo)
        f_librosa = executor.submit(run_librosa)
        step(0.35, "YOLOv8 detecting objects + Librosa measuring audio…")
        yolo_results  = f_yolo.result()
        audio_metrics = f_librosa.result()

    # ── STEP 4: Gemini Vision — ALL frames sent together in one request ───────
    step(0.55, "Gemini analyzing all 6 frames together — describing video content…")
    content_module  = mods["ContentUnderstanding"]()
    understanding   = content_module.understand([], audio_metrics, frame_paths=frames)

    # understanding is now a dict: {video_description, primary_activity, detected_objects, environment}
    if isinstance(understanding, dict):
        video_description = understanding.get("video_description", "")
        primary_activity  = understanding.get("primary_activity", "")
        gemini_objects    = understanding.get("detected_objects", [])
        environment       = understanding.get("environment", "")
    else:
        # backward compat if string returned
        video_description = str(understanding)
        primary_activity  = ""
        gemini_objects    = []
        environment       = ""

    # ── STEP 5: Activity detection — fuse Gemini + YOLO ─────────────────────
    step(0.65, "Detecting activity and content category from Gemini + YOLO results…")
    _ensure_backend_on_path()
    from modules.activity_detector import ActivityDetector

    # Combine YOLO objects + Gemini-detected objects for best coverage
    all_detected_objects = list(set(
        yolo_results.get("detected_objects", []) + gemini_objects
    ))

    activity_result = ActivityDetector().detect(
        gemini_description=video_description,
        gemini_primary_activity=primary_activity,
        yolo_objects=all_detected_objects,
        yolo_confidence=yolo_results.get("confidence_map", {}),
    )

    content_category = activity_result["category"]
    final_activity   = activity_result["primary_activity"]
    # Use Gemini's description if activity_detector had its own suggestion
    if primary_activity and primary_activity != "Content creation":
        final_activity = primary_activity

    # ── STEP 6: Coaching — niche-specific, based on measured issues ──────────
    step(0.72, f"Building {content_category} coaching feedback from measured issues…")
    coach = mods["CreatorCoach"]()
    coaching_feedback = coach.generate_feedback(
        content_category=content_category,
        video_description=video_description,
        primary_activity=final_activity,
        visual_metrics=visual_metrics,
        hook_analysis=hook_analysis,
        audio_metrics=audio_metrics,
        detected_objects=all_detected_objects,
    )

    # ── STEP 7: PARALLEL — captions + hashtags ────────────────────────────────
    step(0.82, "Generating captions & hashtags…")

    captions = {}
    hashtags = []

    def run_captions():
        return mods["CaptionGenerator"]().generate(
            video_description, content_category, primary_activity=final_activity
        )

    def run_hashtags():
        return mods["HashtagGenerator"]().generate(
            video_description, content_category, primary_activity=final_activity
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_cap = executor.submit(run_captions)
        f_ht  = executor.submit(run_hashtags)
        captions = f_cap.result()
        hashtags = f_ht.result()

    # ── STEP 8: Thumbnail — OpenCV picks best frame ───────────────────────────
    step(0.95, "Selecting best thumbnail frame…")
    thumbnail = mods["ThumbnailSelector"]().select_best(frames, visual_metrics, session_id)

    progress.empty()
    status.empty()

    # ── ENRICHMENT: compute derived insights from existing data (no new APIs) ──
    viral_analysis  = _compute_viral_potential(visual_metrics, hook_analysis, audio_metrics, content_category, duration)
    key_moments     = _compute_key_moments(visual_metrics, hook_analysis, duration, all_detected_objects)
    retention_risks = _compute_retention_risks(visual_metrics, duration)
    hashtag_groups  = _group_hashtags(hashtags)
    # New intelligence features
    algorithm_score   = _compute_algorithm_score(viral_analysis, visual_metrics, audio_metrics)
    audience_psych    = _compute_audience_psychology(visual_metrics, hook_analysis, audio_metrics, content_category, video_description)
    platform_scores   = _compute_platform_scores(visual_metrics, hook_analysis, audio_metrics, content_category)
    editing_fixes     = _compute_editing_fixes(visual_metrics, audio_metrics)
    viral_clips       = _compute_viral_clips(visual_metrics, hook_analysis, duration, all_detected_objects)
    viral_titles      = _compute_viral_titles(video_description, content_category, final_activity)

    return {
        "session_id":          session_id,
        "video_description":   video_description,
        "primary_activity":    final_activity,
        "environment":         environment,
        "content_category":    content_category,
        "activity_confidence": activity_result.get("confidence", "medium"),
        "detected_objects":    all_detected_objects,
        "yolo_available":      yolo_results.get("yolo_available", False),
        "gemini_error":        understanding.get("gemini_error", "") if isinstance(understanding, dict) else "",
        "duration_seconds":    duration,
        "visual_analysis":     visual_metrics,
        "hook_analysis":       hook_analysis,
        "audio_analysis":      audio_metrics,
        "coaching_feedback":   coaching_feedback,
        "captions":            captions,
        "hashtags":            hashtags,
        "hashtag_groups":      hashtag_groups,
        "thumbnail":           thumbnail,
        "viral_analysis":      viral_analysis,
        "key_moments":         key_moments,
        "retention_risks":     retention_risks,
        "algorithm_score":     algorithm_score,
        "audience_psych":      audience_psych,
        "platform_scores":     platform_scores,
        "editing_fixes":       editing_fixes,
        "viral_clips":         viral_clips,
        "viral_titles":        viral_titles,
        "_frames":             frames,
    }


# ── Enrichment compute functions (pure Python, use existing metrics only) ─────

def _compute_viral_potential(v: dict, h: dict, a: dict, category: str, duration: float) -> dict:
    """Estimate viral potential from already-measured metrics. No new AI calls."""

    hook_score    = h.get("hook_score", 5.0)
    motion_energy = v.get("motion_energy", 30)
    stability     = v.get("stability_score", 60)
    brightness    = v.get("brightness_score", 50)
    contrast      = v.get("contrast_score", 50)
    silence_pct   = a.get("silence_percentage", 20)
    tempo         = a.get("tempo_bpm") or 0
    has_scene_chg = h.get("scene_change_detected", False)
    subject_vis   = h.get("subject_visible", True)
    motion_int    = h.get("motion_intensity", motion_energy / 10)  # hook motion_intensity

    # ── Score each dimension 0–10 ────────────────────────────────────────────
    hook_dim = round(min(hook_score, 10), 1)

    # FIXED Scroll-Stopping formula (per spec):
    # 0.4*hook + 0.3*motion_intensity_norm + 0.2*brightness_norm + 0.1*scene_change
    motion_int_norm  = min(motion_int / 10, 1.0) * 10          # already 0–10 or normalize
    brightness_norm  = min(brightness / 10, 10)                # brightness/10 on 0–10 scale
    scene_chg_score  = 10 if has_scene_chg else 5
    scroll_raw = (
        0.4 * hook_dim +
        0.3 * motion_int_norm +
        0.2 * brightness_norm +
        0.1 * scene_chg_score
    )
    scroll_dim = round(min(max(scroll_raw, 0), 10), 1)

    # Retention: stable + low silence + good contrast
    ret_raw = 5.0
    if stability >= 80:     ret_raw += 1.5
    if silence_pct < 15:    ret_raw += 1.5
    if silence_pct > 40:    ret_raw -= 2.0
    if contrast >= 40:      ret_raw += 1.0
    if tempo and 100 <= tempo <= 160: ret_raw += 1.0
    ret_dim = round(min(max(ret_raw, 0), 10), 1)

    # Shareability: content type affinity + hook
    share_affinity = {
        "Music Performance": 8.5, "Dance": 8.5, "Comedy": 9.0,
        "Sports": 8.0, "Fitness": 7.5, "Food & Cooking": 8.0,
        "Tech Review": 7.0, "Travel": 8.5, "Tutorial": 7.0,
        "Education": 6.5, "Gaming": 7.0, "Lifestyle": 6.0,
    }
    share_base = share_affinity.get(category, 6.5)
    share_dim  = round(min((share_base + hook_dim * 0.15), 10), 1)

    # Overall viral score = weighted average
    overall = round((hook_dim * 0.35 + scroll_dim * 0.25 + ret_dim * 0.25 + share_dim * 0.15), 1)

    # Human labels
    def _label(score):
        if score >= 8:   return "Strong"
        if score >= 6:   return "Good"
        if score >= 4:   return "Moderate"
        return "Weak"

    # Explanation — built from measured signals
    reasons = []
    if hook_dim >= 7:
        reasons.append("strong opening hook that stops the scroll")
    elif hook_dim < 5:
        reasons.append("weak hook that risks early viewer drop-off")
    if motion_energy > 50:
        reasons.append("high motion energy that keeps viewers watching")
    if has_scene_chg:
        reasons.append("scene change in the first 3 seconds adds visual variety")
    if silence_pct > 35:
        reasons.append("long silent gaps hurt pacing and may cause drop-off")
    if stability >= 80:
        reasons.append("stable camera gives a polished, professional feel")
    if tempo and 110 <= tempo <= 155:
        reasons.append(f"energetic audio tempo ({tempo:.0f} BPM) matches fast-paced content")
    if share_base >= 8:
        reasons.append(f"{category} content has high shareability on Reels/TikTok")

    explanation = (
        "This reel " + (", ".join(reasons[:3]) or "shows room for improvement") + "."
    )

    scroll_explanation = (
        "Scroll-stopping power is determined by hook strength, motion intensity, "
        "early scene change, and brightness of the opening frame. "
        f"Hook contributed {0.4*hook_dim:.1f}/4.0 pts, motion {0.3*motion_int_norm:.1f}/3.0 pts, "
        f"brightness {0.2*brightness_norm:.1f}/2.0 pts, scene change {0.1*scene_chg_score:.1f}/1.0 pts."
    )

    return {
        "overall":            overall,
        "hook":               {"score": hook_dim,   "label": _label(hook_dim)},
        "scroll_stop":        {"score": scroll_dim,  "label": _label(scroll_dim)},
        "scroll_explanation": scroll_explanation,
        "retention":          {"score": ret_dim,     "label": _label(ret_dim)},
        "shareability":       {"score": share_dim,   "label": _label(share_dim)},
        "explanation":        explanation,
        # expose for algorithm score computation
        "_hook_dim":      hook_dim,
        "_ret_dim":       ret_dim,
        "_scroll_dim":    scroll_dim,
    }


def _compute_key_moments(v: dict, h: dict, duration: float, objects: list) -> list:
    """
    Detect key moments from motion + scene changes.
    Returns list of {time_str, label, type} — no new API calls.
    """
    if duration <= 0:
        return []

    moments = []

    # Frame positions match the 10/25/40/55/70/90% extraction spec
    positions = [0.10, 0.25, 0.40, 0.55, 0.70, 0.90]
    motion_e  = v.get("motion_energy", 30)

    for i, pct in enumerate(positions):
        t = pct * duration
        mm = int(t // 60)
        ss = int(t % 60)
        time_str = f"{mm:02d}:{ss:02d}"

        # Opening — always a moment
        if i == 0:
            hook_label = h.get("hook_assessment", "")
            moments.append({"time": time_str, "label": "Opening / Hook", "type": "hook"})

        # Scene change detected in hook analysis
        elif i == 1 and h.get("scene_change_detected"):
            moments.append({"time": time_str, "label": "Scene change", "type": "transition"})

        # Infer activity moments from detected objects
        elif objects:
            obj_labels = {
                "sports ball": "Ball action",
                "tennis racket": "Racket swing",
                "basketball": "Basketball move",
                "guitar": "Guitar performance",
                "dumbbell": "Lift / exercise",
                "person": None,   # skip — too generic
            }
            for obj in objects[:5]:
                lbl = obj_labels.get(obj.lower())
                if lbl:
                    moments.append({"time": time_str, "label": lbl, "type": "action"})
                    break
            else:
                if motion_e > 50 and i % 2 == 0:
                    moments.append({"time": time_str, "label": "High-action segment", "type": "action"})

    # Peak moment
    if duration > 5:
        peak_pct = 0.55
        t = peak_pct * duration
        mm, ss = int(t // 60), int(t % 60)
        moments.append({"time": f"{mm:02d}:{ss:02d}", "label": "Mid-video momentum peak", "type": "peak"})

    # Deduplicate by time
    seen, out = set(), []
    for m in moments:
        if m["time"] not in seen:
            seen.add(m["time"])
            out.append(m)

    return sorted(out, key=lambda x: x["time"])[:8]


def _compute_retention_risks(v: dict, duration: float) -> list:
    """
    Flag segments where motion energy or silence indicates drop-off risk.
    Uses existing visual + audio metrics — no new computation.
    """
    risks = []
    motion_e  = v.get("motion_energy", 50)
    stability = v.get("stability_score", 70)
    noise     = v.get("noise_level", 20)

    if motion_e < 20 and duration > 8:
        risks.append({
            "segment": f"0:00 – {int(duration*0.4):02d}s",
            "issue":   "Low motion energy throughout the video",
            "fix":     "Speed up slow segments by 1.25×–1.5× or add B-roll cuts to maintain visual pace.",
        })
    elif motion_e < 35 and duration > 12:
        t_start = int(duration * 0.35)
        t_end   = int(duration * 0.60)
        risks.append({
            "segment": f"0:{t_start:02d} – 0:{t_end:02d}",
            "issue":   "Motion energy dips in the middle of the video — viewers may swipe away",
            "fix":     "Trim this segment or insert a quick cut to a different angle to re-engage attention.",
        })

    if stability < 45:
        risks.append({
            "segment": "Throughout",
            "issue":   "Heavy camera shake reduces watchability",
            "fix":     "Apply stabilization in CapCut (Stabilize) or Adobe Premiere (Warp Stabilizer).",
        })

    if noise > 55:
        risks.append({
            "segment": "Throughout",
            "issue":   "High visual noise (grain) makes the video feel low-quality",
            "fix":     "Film in better lighting, or apply Noise Reduction in DaVinci Resolve or CapCut.",
        })

    return risks


def _group_hashtags(hashtags: list) -> dict:
    """
    Split a flat hashtag list into High / Medium / Niche tiers.
    Uses simple length + keyword heuristics — no API calls.
    High-reach: short (≤12 chars), broad. Niche: long (>18 chars) or very specific.
    """
    high, medium, niche = [], [], []

    high_keywords = {
        "fitness","gym","workout","sports","music","dance","food","travel",
        "tech","gaming","viral","trending","reels","tiktok","reelsviral",
        "funny","comedy","lifestyle","fashion","beauty","education",
    }

    for tag in hashtags:
        clean = tag.lstrip("#").lower()
        length = len(clean)

        if clean in high_keywords or length <= 8:
            high.append(tag)
        elif length > 18 or clean.count("_") >= 2:
            niche.append(tag)
        else:
            medium.append(tag)

    # Balance tiers — aim for ~8 high, ~12 medium, ~5 niche
    while len(high) > 9 and medium:
        high_overflow = high.pop()
        medium.insert(0, high_overflow)
    while len(niche) > 7 and medium:
        niche_overflow = niche.pop()
        medium.append(niche_overflow)

    return {"high": high[:9], "medium": medium[:13], "niche": niche[:7]}


# ─────────────────────────────────────────────────────────────────────────────
# NEW FEATURE COMPUTE FUNCTIONS (pure Python / rule-based, no new API calls
# except _compute_viral_titles which calls Gemini text once)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_algorithm_score(viral: dict, v: dict, a: dict) -> dict:
    """
    Feature 2 — Estimated Algorithm Performance.
    Uses existing viral_analysis scores + audio quality metric.
    Formula per spec:
      algorithm_score = 0.35*hook + 0.25*retention + 0.20*scroll_stop
                      + 0.10*motion_energy + 0.10*audio_quality
    """
    hook_s    = viral.get("_hook_dim",   viral.get("hook",    {}).get("score", 5.0))
    ret_s     = viral.get("_ret_dim",    viral.get("retention",{}).get("score", 5.0))
    scroll_s  = viral.get("_scroll_dim", viral.get("scroll_stop",{}).get("score", 5.0))

    motion_e  = v.get("motion_energy", 30)
    motion_n  = min(motion_e / 10, 10)           # normalise to 0–10

    # Audio quality: penalise clipping / too-quiet / noisy
    aq = 7.0
    if a.get("clipping_detected"):          aq -= 2.5
    if a.get("volume_label") == "too_quiet": aq -= 2.0
    if a.get("noise_label") == "noisy":     aq -= 1.5
    if a.get("audio_type") == "none":       aq -= 3.0
    audio_q = max(0.0, aq)

    raw = (0.35 * hook_s + 0.25 * ret_s + 0.20 * scroll_s
           + 0.10 * motion_n + 0.10 * audio_q)
    score = round(min(max(raw, 0), 10), 1)

    if score >= 9:
        tier, reach = "Viral Potential",   "100K+ views"
    elif score >= 7:
        tier, reach = "High Reach",        "20K–100K views"
    elif score >= 5:
        tier, reach = "Moderate Reach",    "5K–30K views"
    elif score >= 3:
        tier, reach = "Low Reach",         "1K–5K views"
    else:
        tier, reach = "Weak Performance",  "Under 1K views"

    # Identify limiting factor
    metrics = {
        "hook strength":     hook_s,
        "retention score":   ret_s,
        "scroll-stop power": scroll_s,
        "motion energy":     motion_n,
        "audio quality":     audio_q,
    }
    weakest_label = min(metrics, key=metrics.get)
    weakest_val   = metrics[weakest_label]

    limiting_msgs = {
        "hook strength":     "low hook strength — the opening fails to capture attention quickly enough",
        "retention score":   "poor retention signals — silent gaps or shaky footage cause viewers to drop off",
        "scroll-stop power": "low scroll-stopping power — the video doesn't create enough visual impact in the first second",
        "motion energy":     "low motion energy — static footage has less algorithm favour on Reels/TikTok",
        "audio quality":     "audio issues — clipping, noise, or missing audio reduce platform distribution",
    }
    if weakest_val < 6:
        limiting = f"Main limiting factor: {limiting_msgs[weakest_label]}."
    else:
        limiting = "No major limiting factors — all signals are in a healthy range."

    return {
        "score":    score,
        "tier":     tier,
        "reach":    reach,
        "limiting": limiting,
        "_metrics": metrics,
    }


def _compute_audience_psychology(v: dict, h: dict, a: dict, category: str,
                                  description: str) -> dict:
    """
    Feature 3 — Audience Psychology Insights.
    Rule-based ratings per category + visual quality.
    No AI call required.
    """
    def _rate(val, hi=7, lo=4):
        if val >= hi: return "HIGH"
        if val >= lo: return "MEDIUM"
        return "LOW"

    brightness  = v.get("brightness_score", 50)
    contrast    = v.get("contrast_score", 50)
    motion_e    = v.get("motion_energy", 30)
    hook_s      = h.get("hook_score", 5.0)
    sharpness   = v.get("sharpness_score", 50)  # may not exist — default safely

    # Visual appeal: brightness + contrast + sharpness
    visual_raw = (brightness / 10 * 0.4 + contrast / 10 * 0.3 + min(sharpness, 100) / 10 * 0.3)
    visual_appeal = _rate(visual_raw, hi=6.5, lo=4)

    # Category-driven base ratings
    cat_map = {
        "Tutorial":       {"curiosity": 8, "learning": 9, "entertainment": 5},
        "Education":      {"curiosity": 8, "learning": 9, "entertainment": 4},
        "Tech Review":    {"curiosity": 8, "learning": 7, "entertainment": 5},
        "Music Performance": {"curiosity": 6, "learning": 3, "entertainment": 9},
        "Dance":          {"curiosity": 6, "learning": 4, "entertainment": 9},
        "Comedy":         {"curiosity": 5, "learning": 2, "entertainment": 10},
        "Sports":         {"curiosity": 6, "learning": 4, "entertainment": 8},
        "Fitness":        {"curiosity": 6, "learning": 7, "entertainment": 6},
        "Food & Cooking": {"curiosity": 7, "learning": 7, "entertainment": 7},
        "Travel":         {"curiosity": 8, "learning": 5, "entertainment": 8},
        "Gaming":         {"curiosity": 5, "learning": 4, "entertainment": 8},
        "Lifestyle":      {"curiosity": 5, "learning": 3, "entertainment": 6},
    }
    base = cat_map.get(category, {"curiosity": 5, "learning": 5, "entertainment": 5})

    # Boost curiosity if hook is strong
    cur_val = base["curiosity"] + (1.5 if hook_s >= 7 else 0)
    ent_val = base["entertainment"] + (motion_e / 100) * 2

    curiosity    = _rate(cur_val, hi=7, lo=4)
    learning     = _rate(base["learning"], hi=7, lo=4)
    entertainment= _rate(ent_val, hi=7, lo=4)

    # Emotion trigger
    triggers = {
        "Tutorial":       "Curiosity + Utility",
        "Education":      "Curiosity + Knowledge",
        "Tech Review":    "Curiosity + Utility",
        "Music Performance": "Emotion + Enjoyment",
        "Dance":          "Energy + Enjoyment",
        "Comedy":         "Amusement + Surprise",
        "Sports":         "Excitement + Inspiration",
        "Fitness":        "Motivation + Aspiration",
        "Food & Cooking": "Desire + Curiosity",
        "Travel":         "Wanderlust + Inspiration",
        "Gaming":         "Excitement + FOMO",
        "Lifestyle":      "Relatability + Aspiration",
    }
    trigger = triggers.get(category, "Interest + Curiosity")

    # Why they stay / may drop
    stay_map = {
        "Tutorial":       "They want to apply the technique shown immediately.",
        "Education":      "The information is new and practically useful.",
        "Tech Review":    "They need to decide whether to buy this product.",
        "Music Performance": "The sound is enjoyable and they want to hear the full performance.",
        "Dance":          "The choreography is visually compelling and they want to catch the full routine.",
        "Comedy":         "They want to reach the punchline.",
        "Sports":         "The action is exciting and they want to see the outcome.",
        "Fitness":        "They're looking for workout inspiration they can use today.",
        "Food & Cooking": "They want to see the final dish and remember the recipe.",
        "Travel":         "The scenery is beautiful and they're living vicariously through it.",
        "Gaming":         "The gameplay moment is tense or impressive.",
        "Lifestyle":      "The creator's life feels aspirational or relatable.",
    }
    stay = stay_map.get(category, "The content matches what they were looking for.")

    # Why they drop — from measured weak points
    drops = []
    if brightness < 28:
        drops.append("low brightness makes it hard to see what's happening")
    if motion_e < 15 and category not in ("Tutorial", "Education", "Tech Review"):
        drops.append("lack of movement feels static and unengaging")
    if v.get("stability_label") == "shaky":
        drops.append("camera shake is distracting and reduces watchability")
    if a.get("silence_percentage", 0) > 35:
        drops.append("long silent gaps break the viewing momentum")
    drop = ("Viewers may drop off because " + drops[0] + ".") if drops else \
           "No major drop-off triggers detected."

    return {
        "curiosity":     curiosity,
        "learning":      learning,
        "entertainment": entertainment,
        "visual_appeal": visual_appeal,
        "trigger":       trigger,
        "why_stay":      stay,
        "why_drop":      drop,
    }


def _compute_platform_scores(v: dict, h: dict, a: dict, category: str) -> dict:
    """
    Feature 4 — Platform Optimization scores.
    Instagram Reels, TikTok, YouTube Shorts — rule-based per spec.
    """
    hook_s   = h.get("hook_score", 5.0)
    motion_e = v.get("motion_energy", 30)
    stability= v.get("stability_score", 60)
    tempo    = a.get("tempo_bpm") or 0
    silence  = a.get("silence_percentage", 20)
    duration = 0   # not passed here — scores are metric-based

    # Base platform affinities per category
    platform_map = {
        # (instagram, tiktok, youtube_shorts)
        "Music Performance": (8.5, 8.0, 7.5),
        "Dance":             (8.5, 9.0, 7.5),
        "Comedy":            (8.0, 9.0, 7.0),
        "Sports":            (8.0, 8.0, 7.5),
        "Fitness":           (8.5, 7.5, 7.5),
        "Food & Cooking":    (8.5, 8.0, 7.0),
        "Tech Review":       (7.0, 7.5, 8.5),
        "Tutorial":          (7.5, 7.0, 8.5),
        "Education":         (7.0, 7.5, 8.5),
        "Travel":            (8.5, 8.0, 7.5),
        "Gaming":            (6.5, 8.0, 8.5),
        "Lifestyle":         (7.5, 7.5, 7.0),
    }
    ig_base, tt_base, yt_base = platform_map.get(category, (7.5, 7.5, 7.5))

    # Adjust based on technical quality
    def _adj(base):
        score = base
        if hook_s >= 8:   score += 0.5
        if hook_s < 5:    score -= 1.0
        if motion_e > 60: score += 0.3
        if stability < 40: score -= 0.7
        if silence > 40:   score -= 0.5
        if tempo and 100 <= tempo <= 160: score += 0.3
        return round(min(max(score, 0), 10), 1)

    ig = _adj(ig_base)
    tt = _adj(tt_base)
    yt = _adj(yt_base)

    best_platform = max([("Instagram Reels", ig), ("TikTok", tt), ("YouTube Shorts", yt)],
                        key=lambda x: x[1])[0]

    # Platform-specific tips
    tips = {
        "Instagram Reels": "Instagram favours high-quality visuals and aesthetic consistency. Use trending audio and post between 9am–11am or 7pm–9pm.",
        "TikTok": "TikTok rewards fast hooks and authentic energy. Use trending sounds and post 3–4× per week for algorithm favour.",
        "YouTube Shorts": "YouTube Shorts benefits from informative content with clear value. Optimize your title and thumbnail for search.",
    }

    return {
        "instagram": ig,
        "tiktok":    tt,
        "youtube":   yt,
        "best":      best_platform,
        "best_tip":  tips[best_platform],
    }


def _compute_editing_fixes(v: dict, a: dict) -> list:
    """
    Feature 5 — AI Editing Fix Suggestions.
    Rule-based — detects problems from existing metrics and maps to
    specific tool settings (CapCut, Premiere Pro, DaVinci Resolve).
    No AI call.
    """
    fixes = []

    brightness = v.get("brightness_score", 50)
    contrast   = v.get("contrast_score", 50)
    stability  = v.get("stability_label", "stable")
    noise      = v.get("noise_level", 20)

    # Lighting issues
    if brightness < 28:
        fixes.append({
            "issue": "Video Too Dark",
            "icon":  "🌑",
            "capcut": [("Brightness", "+25"), ("Contrast", "+10"), ("Exposure", "+0.3")],
            "premiere": [("Exposure", "+0.5"), ("Highlights", "+20"), ("Shadows", "+15")],
            "davinci": [("Lift", "+0.05"), ("Gamma", "+0.08")],
        })
    elif brightness > 78:
        fixes.append({
            "issue": "Video Overexposed",
            "icon":  "☀️",
            "capcut": [("Brightness", "-20"), ("Highlights", "-25"), ("Exposure", "-0.3")],
            "premiere": [("Exposure", "-0.4"), ("Highlights", "-30"), ("Recovery", "+20")],
            "davinci": [("Gain", "-0.06"), ("Highlight Roll-Off", "+0.2")],
        })

    if contrast < 20:
        fixes.append({
            "issue": "Low Contrast / Flat Image",
            "icon":  "🎨",
            "capcut": [("Contrast", "+20"), ("Saturation", "+10"), ("Sharpen", "+15")],
            "premiere": [("Contrast", "+20"), ("Vibrance", "+15")],
            "davinci": [("Contrast", "+0.10"), ("Saturation", "+0.15")],
        })

    # Camera shake
    if stability == "shaky":
        fixes.append({
            "issue": "Heavy Camera Shake",
            "icon":  "📷",
            "capcut": [("Stabilize", "Level 3"), ("Crop if needed", "5%")],
            "premiere": [("Warp Stabilizer", "Smooth Motion"), ("Smoothness", "75%")],
            "davinci": [("Stabilize", "Perspective Mode"), ("Strength", "0.8")],
        })
    elif stability == "minor_shake":
        fixes.append({
            "issue": "Minor Camera Shake",
            "icon":  "📷",
            "capcut": [("Stabilize", "Level 1–2")],
            "premiere": [("Warp Stabilizer", "Subspace Warp"), ("Smoothness", "50%")],
            "davinci": [("Stabilize", "Similarity Mode"), ("Strength", "0.5")],
        })

    # Noise / grain
    if noise > 55:
        fixes.append({
            "issue": "Heavy Grain / Video Noise",
            "icon":  "📡",
            "capcut": [("Noise Reduction", "Level 3"), ("Sharpen", "+5 after NR")],
            "premiere": [("Reduce Noise (Lumetri)", "Amount 40%")],
            "davinci": [("Temporal NR", "25%"), ("Spatial NR", "15%")],
        })
    elif noise > 35:
        fixes.append({
            "issue": "Mild Grain / Noise",
            "icon":  "📡",
            "capcut": [("Noise Reduction", "Level 1")],
            "premiere": [("Reduce Noise", "Amount 20%")],
            "davinci": [("Temporal NR", "10%")],
        })

    # Audio fixes
    if a.get("clipping_detected"):
        fixes.append({
            "issue": "Audio Clipping",
            "icon":  "🎙️",
            "capcut": [("Volume", "Reduce by 20%"), ("Compressor", "Threshold -12dB")],
            "premiere": [("Hard Limiter", "-1dBFS ceiling"), ("Gain", "-3 to -6dB")],
            "davinci": [("Fairlight Limiter", "Ceiling -1dBFS"), ("Gain", "-4dB")],
        })
    if a.get("volume_label") == "too_quiet":
        rms = a.get("rms_loudness", -30)
        boost = min(int(-18 - rms), 15) if rms else 10
        fixes.append({
            "issue": "Audio Too Quiet",
            "icon":  "🔊",
            "capcut": [("Volume", f"+{boost} boost"), ("Normalize", "to -14 LUFS")],
            "premiere": [("Normalize to", "-14 LUFS"), ("Gain", f"+{boost}dB")],
            "davinci": [("Normalize", "-14 LUFS integrated"), ("Gain", f"+{boost}dB")],
        })

    return fixes


def _compute_viral_clips(v: dict, h: dict, duration: float, objects: list) -> list:
    """
    Feature 6 — Auto Viral Clip Finder.
    Selects top 3 clip windows from motion spikes + scene change + objects.
    No AI call.
    """
    if duration <= 0:
        return []

    candidates = []
    positions  = [0.05, 0.10, 0.20, 0.30, 0.45, 0.55, 0.65, 0.80, 0.90]
    motion_e   = v.get("motion_energy", 30)
    hook_s     = h.get("hook_score", 5.0)

    def _ts(pct):
        t = pct * duration
        return f"{int(t//60):02d}:{int(t%60):02d}"

    # Clip 1 — hook clip (always first 0–4s if strong hook)
    clip_end_1 = min(4, duration)
    score1 = hook_s * 0.8 + (2 if h.get("scene_change_detected") else 0)
    candidates.append({
        "rank": score1, "start": _ts(0.0), "end": _ts(min(4/duration, 1)),
        "label": "Hook / Opening", "reason": "Strong hook moment — highest stop-scroll potential",
        "type": "hook"
    })

    # Clip 2 — highest motion segment (around 25–50%)
    score2 = (motion_e / 10) + hook_s * 0.3
    obj_boost = 0
    activity_objs = {"sports ball", "guitar", "dumbbell", "tennis racket", "basketball",
                     "skateboard", "microphone", "food"}
    for obj in objects:
        if obj.lower() in activity_objs:
            obj_boost = 2
            break
    score2 += obj_boost
    candidates.append({
        "rank": score2, "start": _ts(0.25), "end": _ts(min(0.25 + 3/duration, 1)),
        "label": "Peak Action",
        "reason": "Highest motion energy window — best for engagement mid-reel",
        "type": "action"
    })

    # Clip 3 — information / visual highlight (55–75%)
    score3 = 5.0 + (motion_e / 20)
    candidates.append({
        "rank": score3, "start": _ts(0.55), "end": _ts(min(0.55 + 3/duration, 1)),
        "label": "Visual Highlight",
        "reason": "Mid-to-late visual highlight — good for loop or standalone clip",
        "type": "peak"
    })

    # Sort by rank, take top 3
    top3 = sorted(candidates, key=lambda x: x["rank"], reverse=True)[:3]
    # Re-number and clean output
    result = []
    for i, c in enumerate(top3, 1):
        result.append({
            "clip_num": i,
            "start":    c["start"],
            "end":      c["end"],
            "label":    c["label"],
            "reason":   c["reason"],
        })
    return result


def _compute_viral_titles(description: str, category: str, activity: str) -> list:
    """
    Feature 7 — Viral Title Generator.
    The ONE permitted Gemini text call (lightweight — text only, no vision).
    Falls back to rule-based titles if API fails.
    """
    import os
    from modules.gemini_client import get_model

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return _fallback_titles(category, activity)

    act_line = f"Primary activity: {activity}" if activity and activity != "Content creation" else ""
    prompt = f"""You are a viral content strategist writing titles for Instagram Reels and TikTok.

CONTENT:
Category: {category}
{act_line}
Description: {description[:300]}

Write 5 scroll-stopping video titles that would make someone stop and watch.

Rules:
- Each title must be specific to the actual content — no generic titles
- Use power words: Hidden, Secret, Wrong, Actually, Never, Always, Instantly, Stop
- Titles should be 6–12 words
- Do not use hashtags
- Sound like a top creator, not a marketing bot

Return ONLY a JSON array of 5 strings, no explanation:
["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"]"""

    try:
        model = get_model()
        import re, json
        resp = model.generate_content(prompt)
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.text.strip())
        titles = json.loads(text)
        return [t for t in titles if isinstance(t, str) and t.strip()][:5]
    except Exception:
        return _fallback_titles(category, activity)


def _fallback_titles(category: str, activity: str) -> list:
    """Rule-based title fallbacks per category."""
    _titles = {
        "Music Performance": [
            f"I Played This {activity or 'Riff'} Every Day For 30 Days (Here's What Happened)",
            "The Guitar Technique Nobody Talks About",
            "This Music Practice Method Changed Everything",
            "Stop Practising Wrong — Do This Instead",
            "Hidden Performance Trick That Took Me 5 Years to Learn",
        ],
        "Sports": [
            "The Drill That Instantly Improved My Game",
            "Stop Training Wrong — Fix This First",
            "Hidden Sports Technique Most Athletes Never Learn",
            "I Did This Drill Every Day For 30 Days",
            "The One Move That Changed My Performance Forever",
        ],
        "Fitness": [
            "You Are Doing This Exercise Wrong (Fix It Now)",
            "3 Form Mistakes That Are Killing Your Gains",
            "The Rep Range Nobody Talks About",
            "Stop Wasting Time At The Gym — Do This Instead",
            "Hidden Technique That Doubles Your Results",
        ],
        "Tech Review": [
            "Honest Review After 30 Days — Here's The Truth",
            "Stop Buying This Until You Watch This Video",
            "Hidden Features Nobody Tells You About",
            "I Tested Every Setting — This Is What Actually Works",
            "The Setting That Instantly Boosts Performance",
        ],
        "Tutorial": [
            "You've Been Doing This Wrong This Whole Time",
            "The 60-Second Trick That Changes Everything",
            "Stop Wasting Hours — Use This Method Instead",
            "Hidden Step That 99% Of Creators Skip",
            "This Simple Change Instantly Improves Your Results",
        ],
        "Food & Cooking": [
            "The Secret Ingredient Chefs Don't Tell You About",
            "Stop Making This Cooking Mistake",
            "This Recipe Takes 15 Minutes And Tastes Like a Restaurant",
            "Hidden Technique That Makes Everything Taste Better",
            "The One Step You're Probably Skipping In The Kitchen",
        ],
    }
    return _titles.get(category, [
        f"The {category} Technique Nobody Talks About",
        f"Stop Doing {category} Wrong",
        f"Hidden {category} Secret That Changes Everything",
        f"I Tried This {category} Method For 30 Days",
        f"This {category} Trick Took Me Years to Learn",
    ])


# ── Render helpers ────────────────────────────────────────────────────────────
# Uses native Streamlit components wherever possible to avoid HTML parsing bugs.
# Raw HTML is only used for simple single-line tags — never multiline f-strings
# with HTML comments, which break Streamlit on Windows.

def _esc(s):
    import html as _h
    return _h.escape(str(s))

def _dot(label):
    good = {"good","stable","clean","none"}
    bad  = {"shaky","noisy","too_dark","overexposed","too_loud","too_quiet","detected","subject_too_small","subject_off_center"}
    l = str(label).lower()
    if l in good:  return "🟢"
    if l in bad:   return "🔴"
    if any(w in l for w in ("warn","minor","moderate")): return "🟡"
    return "⚪"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Overview card
# ─────────────────────────────────────────────────────────────────────────────
def render_overview(data):
    feedback   = data["coaching_feedback"]
    score      = feedback["overall_score"]
    cat        = data["content_category"]
    activity   = data.get("primary_activity", "")
    desc       = str(data.get("video_description", ""))
    environment= data.get("environment", "")
    summary    = str(feedback.get("overall_summary", ""))
    color      = score_color(score)
    objects    = data.get("detected_objects", [])
    yolo_ok    = data.get("yolo_available", False)
    confidence = data.get("activity_confidence", "medium")

    if score >= 8:   verdict, vc = "Excellent", "#6BCB77"
    elif score >= 6.5: verdict, vc = "Good",    "#C8FF57"
    elif score >= 5:   verdict, vc = "Needs Work","#FFD93D"
    else:              verdict, vc = "Major Issues","#FF4757"

    c1, c2 = st.columns([1, 4])
    with c1:
        st.markdown(
            f'<div style="width:105px;height:105px;border-radius:50%;border:5px solid {color};'
            f'display:flex;flex-direction:column;align-items:center;justify-content:center;margin:4px auto">'
            f'<span style="font-size:2.1rem;font-weight:800;color:{color};line-height:1;font-family:Syne,sans-serif">{score:.1f}</span>'
            f'<span style="font-size:0.58rem;opacity:0.5;text-transform:uppercase;letter-spacing:0.1em">/ 10</span>'
            f'</div>'
            f'<div style="text-align:center;font-size:0.75rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:{vc};margin-top:6px">{verdict}</div>',
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(f"### {_esc(cat)} Reel")
        conf_color = {"high": "#6BCB77", "medium": "#C8FF57", "low": "#FFD93D"}.get(confidence, "#C8FF57")
        st.markdown(
            f'<span style="background:rgba(87,200,255,0.12);color:#57C8FF;border:1px solid rgba(87,200,255,0.2);'
            f'border-radius:100px;padding:3px 14px;font-size:0.75rem;font-weight:600;margin-right:8px">{_esc(cat)}</span>'
            f'<span style="background:rgba(200,255,87,0.1);color:{conf_color};border:1px solid rgba(200,255,87,0.2);'
            f'border-radius:100px;padding:3px 12px;font-size:0.7rem;font-weight:600">{confidence.upper()} CONFIDENCE</span>',
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if activity and activity != "Content creation":
            st.markdown(f"**Primary activity:** {_esc(activity)}")
        st.markdown(f"*{_esc(summary)}*")

    st.divider()

    # Video description
    st.markdown('<p style="font-size:0.65rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#C8FF57;margin-bottom:6px">WHAT IS HAPPENING IN THIS VIDEO</p>', unsafe_allow_html=True)

    gemini_error = data.get("gemini_error", "")
    is_fallback = (
        "Gemini Vision analysis failed" in desc or
        "GEMINI_API_KEY not set" in desc or
        "Video content detected" in desc or
        len(desc.strip()) < 40
    )

    if is_fallback:
        if "GEMINI_API_KEY not set" in desc or not os.getenv("GEMINI_API_KEY"):
            st.error(
                "**Gemini API key not found — video description unavailable.**\n\n"
                "1. Open `backend/.env`\n"
                "2. Add: `GEMINI_API_KEY=your_key_here`\n"
                "3. Get a free key at https://aistudio.google.com/app/apikey\n"
                "4. Restart Streamlit: `Ctrl+C` then `streamlit run app.py`"
            )
        else:
            st.warning(
                f"**Gemini Vision could not describe this video.**\n\n"
                f"Error: `{gemini_error or desc}`\n\n"
                "The category was still detected from YOLOv8 object detection above. "
                "Check your internet connection and that the Gemini API key is valid."
            )
    else:
        st.markdown(
            f'<div style="background:#141920;border-left:4px solid #C8FF57;border-radius:0 10px 10px 0;'
            f'padding:16px 20px;font-size:1rem;line-height:1.85;color:rgba(255,255,255,0.9)">{_esc(desc)}</div>',
            unsafe_allow_html=True
        )

    # Detected objects + environment row
    st.markdown("<br>", unsafe_allow_html=True)
    col_o, col_e = st.columns([3, 2])

    with col_o:
        if objects:
            st.markdown('<p style="font-size:0.62rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:8px">DETECTED OBJECTS</p>', unsafe_allow_html=True)
            chips = " ".join(
                f'<span style="background:#141920;border:1px solid rgba(255,255,255,0.1);'
                f'border-radius:6px;padding:3px 10px;font-size:0.82rem;color:rgba(255,255,255,0.65);'
                f'margin:2px;display:inline-block">{_esc(o)}</span>'
                for o in objects[:15]
            )
            yolo_note = " 🔍 YOLOv8" if yolo_ok else " (Gemini-detected)"
            st.markdown(f'<div style="line-height:2.1">{chips}</div><div style="font-size:0.68rem;color:rgba(255,255,255,0.25);margin-top:4px">{yolo_note}</div>', unsafe_allow_html=True)

    with col_e:
        if environment and environment != "Unknown":
            st.markdown('<p style="font-size:0.62rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:8px">ENVIRONMENT</p>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.88rem;color:rgba(255,255,255,0.6);line-height:1.6">{_esc(environment)}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Technical metrics (3 tabs instead of 3 crowded columns)
# ─────────────────────────────────────────────────────────────────────────────
def render_metrics_row(data):
    v = data["visual_analysis"]
    h = data["hook_analysis"]
    a = data["audio_analysis"]

    tab1, tab2, tab3 = st.tabs(["🎥  Visual Quality", "⚡  Hook (First 3s)", "🎵  Audio"])

    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        items = [
            ("Brightness",       f"{v['brightness_score']:.0f} / 100",  v["brightness_label"]),
            ("Contrast",         f"{v['contrast_score']:.0f} / 100",    v["contrast_label"]),
            ("Camera Stability", f"{v['stability_score']:.0f} / 100",   v["stability_label"]),
            ("Noise Level",      v["noise_label"].replace("_"," ").title(), v["noise_label"]),
            ("Framing",          v["framing_label"].replace("_"," ").title(), v["framing_label"]),
            ("Motion Energy",    f"{v['motion_energy']:.0f} / 100",     "neutral"),
        ]
        for label, val, status in items:
            dot = _dot(status)
            ca, cb = st.columns([3,2])
            with ca: st.markdown(f'<span style="font-size:0.95rem;color:rgba(255,255,255,0.6)">{label}</span>', unsafe_allow_html=True)
            with cb: st.markdown(f'<span style="font-size:0.95rem;font-weight:600">{dot} {val}</span>', unsafe_allow_html=True)
            st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.05);margin:4px 0'>", unsafe_allow_html=True)

    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        hook_score = h["hook_score"]
        has_hook   = h["has_strong_hook"]

        if has_hook:
            st.success(f"**Strong Hook** — Score: {hook_score}/10")
        else:
            st.error(f"**Weak Hook** — Score: {hook_score}/10")

        st.progress(hook_score / 10)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'> {_esc(h["hook_assessment"])}')
        st.markdown("<br>", unsafe_allow_html=True)

        items2 = [
            ("Scene Change in Opening",  "Yes" if h["scene_change_detected"] else "No",  "good" if h["scene_change_detected"] else "warn"),
            ("Subject Clearly Visible",  "Yes" if h["subject_visible"] else "No",         "good" if h["subject_visible"] else "bad"),
            ("Motion Intensity",         f"{h['motion_intensity']:.1f}",                "good" if h["motion_intensity"] > 15 else "warn"),
        ]
        for label, val, status in items2:
            dot = _dot(status)
            ca, cb = st.columns([3,2])
            with ca: st.markdown(f'<span style="font-size:0.95rem;color:rgba(255,255,255,0.6)">{label}</span>', unsafe_allow_html=True)
            with cb: st.markdown(f'<span style="font-size:0.95rem;font-weight:600">{dot} {val}</span>', unsafe_allow_html=True)
            st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.05);margin:4px 0'>", unsafe_allow_html=True)

    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        tempo_str = f"{a['tempo_bpm']:.0f} BPM" if a.get("tempo_bpm") else "N/A"
        items3 = [
            ("Audio Type",   a["audio_type"].replace("+"," + ").title(),      "neutral"),
            ("Volume Level", a["volume_label"].replace("_"," ").title(),       a["volume_label"]),
            ("Background Noise", a["noise_label"].replace("_"," ").title(),   a["noise_label"]),
            ("Clipping",     "Detected ⚠️" if a["clipping_detected"] else "None ✓", "bad" if a["clipping_detected"] else "good"),
            ("Tempo",        tempo_str,                                         "neutral"),
            ("Silent Gaps",  f"{a['silence_percentage']:.0f}%",             "good" if a["silence_percentage"] < 20 else "warn"),
        ]
        for label, val, status in items3:
            dot = _dot(status)
            ca, cb = st.columns([3,2])
            with ca: st.markdown(f'<span style="font-size:0.95rem;color:rgba(255,255,255,0.6)">{label}</span>', unsafe_allow_html=True)
            with cb: st.markdown(f'<span style="font-size:0.95rem;font-weight:600">{dot} {val}</span>', unsafe_allow_html=True)
            st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.05);margin:4px 0'>", unsafe_allow_html=True)

        if a.get("issues"):
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Audio Issues Detected:**")
            for iss in a["issues"]:
                st.warning(str(iss))


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Postlytics
# ─────────────────────────────────────────────────────────────────────────────
def render_coaching_section(feedback):
    persona  = str(feedback.get("creator_persona", ""))
    works    = feedback.get("what_works_well", [])
    improve  = feedback.get("what_needs_improvement", [])

    st.markdown(f'<p style="font-size:0.82rem;color:rgba(255,255,255,0.45);font-style:italic;margin-bottom:16px">Reviewed by: {_esc(persona)}</p>', unsafe_allow_html=True)

    if works:
        st.markdown("#### ✅ What Is Working Well")
        for w in works:
            st.success(str(w))
        st.markdown("<br>", unsafe_allow_html=True)

    if improve:
        st.markdown("#### ⚠️ What Needs Improvement")
        st.markdown('<p style="font-size:0.8rem;color:rgba(255,255,255,0.4);margin-bottom:12px">Sorted by priority — fix HIGH items first for maximum impact.</p>', unsafe_allow_html=True)

        priority_order = {"high": 0, "medium": 1, "low": 2}
        improve_sorted = sorted(improve, key=lambda x: priority_order.get(str(x.get("priority","low")).lower(), 2))

        for imp in improve_sorted:
            priority = str(imp.get("priority", "medium")).lower()
            cat      = str(imp.get("category", "General"))
            text     = str(imp.get("feedback", imp.get("issue", "")))

            label = f"**[{priority.upper()}] {cat}**"

            if priority == "high":
                st.error(f"{label}\n\n{text}")
            elif priority == "medium":
                st.warning(f"{label}\n\n{text}")
            else:
                st.info(f"{label}\n\n{text}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION: Viral Potential Analysis
# ─────────────────────────────────────────────────────────────────────────────
def render_viral_potential(vp: dict):
    overall = vp.get("overall", 0)
    color   = score_color(overall)

    # Overall score + explanation
    c1, c2 = st.columns([1, 4])
    with c1:
        st.markdown(
            f'<div style="width:95px;height:95px;border-radius:50%;border:4px solid {color};'
            f'display:flex;flex-direction:column;align-items:center;justify-content:center;margin:4px auto">'
            f'<span style="font-size:1.9rem;font-weight:800;color:{color};line-height:1;font-family:Syne,sans-serif">{overall}</span>'
            f'<span style="font-size:0.55rem;opacity:0.5;text-transform:uppercase;letter-spacing:0.1em">/ 10</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    with c2:
        explanation = vp.get("explanation", "")
        st.markdown(f'<p style="font-size:1rem;line-height:1.75;color:rgba(255,255,255,0.85);margin:0">{_esc(explanation)}</p>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Four dimension cards
    dims = [
        ("⚡ Hook Strength",         vp["hook"]),
        ("🛑 Scroll-Stopping Power", vp["scroll_stop"]),
        ("🔁 Retention Potential",   vp["retention"]),
        ("📤 Shareability",          vp["shareability"]),
    ]
    cols = st.columns(4)
    label_colors = {"Strong": "#6BCB77", "Good": "#C8FF57", "Moderate": "#FFD93D", "Weak": "#FF4757"}

    for col, (title, dim) in zip(cols, dims):
        lbl   = dim["label"]
        score = dim["score"]
        lc    = label_colors.get(lbl, "#C8FF57")
        with col:
            st.markdown(
                f'<div style="background:#0E1218;border:1px solid rgba(255,255,255,0.08);border-radius:12px;'
                f'padding:16px 14px;text-align:center">'
                f'<div style="font-size:0.7rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;'
                f'color:rgba(255,255,255,0.4);margin-bottom:8px">{title}</div>'
                f'<div style="font-size:1.6rem;font-weight:800;color:{lc};font-family:Syne,sans-serif;line-height:1">{score}</div>'
                f'<div style="font-size:0.75rem;font-weight:700;color:{lc};margin-top:4px;text-transform:uppercase;letter-spacing:0.06em">{lbl}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION: Hook Analysis (First 3 Seconds)
# ─────────────────────────────────────────────────────────────────────────────
def render_hook_analysis(h: dict, v: dict):
    hook_score   = h.get("hook_score", 0)
    assessment   = h.get("hook_assessment", "")
    scene_change = h.get("scene_change_detected", False)
    subject_vis  = h.get("subject_visible", True)
    motion_int   = h.get("motion_intensity", 0)
    brightness   = v.get("brightness_score", 50)

    color = score_color(hook_score)

    col_score, col_detail = st.columns([1, 3])
    with col_score:
        st.markdown(
            f'<div style="background:#0E1218;border:1px solid rgba(255,255,255,0.08);border-radius:14px;'
            f'padding:24px 16px;text-align:center">'
            f'<div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;'
            f'color:rgba(255,255,255,0.35);margin-bottom:10px">Hook Score</div>'
            f'<div style="font-size:2.8rem;font-weight:800;color:{color};font-family:Syne,sans-serif;line-height:1">{hook_score}</div>'
            f'<div style="font-size:0.65rem;opacity:0.4;margin-top:4px">out of 10</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with col_detail:
        st.markdown(f'<p style="font-size:0.97rem;line-height:1.75;color:rgba(255,255,255,0.8)">{_esc(assessment)}</p>', unsafe_allow_html=True)
        st.progress(hook_score / 10)
        st.markdown("<br>", unsafe_allow_html=True)

        # Signal checklist
        signals = [
            ("Scene change in first 3s", scene_change,  "Yes ✓" if scene_change else "No",     scene_change),
            ("Subject clearly visible",  subject_vis,   "Yes ✓" if subject_vis  else "No",     subject_vis),
            ("Motion intensity",         motion_int > 15, f"{motion_int:.1f}",                  motion_int > 15),
            ("Opening brightness",       35 <= brightness <= 75, f"{brightness:.0f}/100",        35 <= brightness <= 75),
        ]
        for label, is_good, val_str, _ in signals:
            icon = "🟢" if is_good else "🔴"
            ca, cb = st.columns([3, 2])
            with ca: st.markdown(f'<span style="font-size:0.9rem;color:rgba(255,255,255,0.6)">{label}</span>', unsafe_allow_html=True)
            with cb: st.markdown(f'<span style="font-size:0.9rem;font-weight:600">{icon} {val_str}</span>', unsafe_allow_html=True)
            st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.05);margin:3px 0'>", unsafe_allow_html=True)

    # Hook suggestion
    st.markdown("<br>", unsafe_allow_html=True)
    if hook_score < 5:
        st.error("💡 **Hook Tip:** Start with your most visually dynamic moment — a close-up, a jump cut, or a reaction shot. Viewers decide whether to swipe in the first 1.5 seconds.")
    elif hook_score < 7:
        st.warning("💡 **Hook Tip:** The opening works but could be stronger. Try leading with a tighter shot on the subject or cutting directly to the most exciting action.")
    else:
        st.success("✅ **Strong Hook:** The opening grabs attention effectively. This is one of the most important factors for watch time.")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION: Retention Risk Detection
# ─────────────────────────────────────────────────────────────────────────────
def render_retention_risks(risks: list):
    if not risks:
        st.success("✅ **No significant retention risks detected.** The video maintains consistent energy throughout.")
        return

    for r in risks:
        st.markdown(
            f'<div style="background:#1a0e0e;border:1px solid rgba(255,71,87,0.3);border-radius:12px;'
            f'padding:16px 20px;margin-bottom:12px">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">'
            f'<span style="font-size:1rem">⚠️</span>'
            f'<span style="font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;'
            f'color:#FF4757">Retention Risk</span>'
            f'<span style="background:rgba(255,71,87,0.15);color:#FF4757;border-radius:6px;'
            f'padding:2px 10px;font-size:0.72rem;font-weight:600">{_esc(r["segment"])}</span>'
            f'</div>'
            f'<p style="font-size:0.92rem;color:rgba(255,255,255,0.8);margin:0 0 8px 0">{_esc(r["issue"])}</p>'
            f'<p style="font-size:0.85rem;color:#C8FF57;margin:0">💡 {_esc(r["fix"])}</p>'
            f'</div>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION: Key Moment Detection
# ─────────────────────────────────────────────────────────────────────────────
def render_key_moments(moments: list):
    if not moments:
        st.caption("Key moment detection requires video duration data.")
        return

    type_colors = {
        "hook":       "#C8FF57",
        "transition": "#57C8FF",
        "action":     "#FF9F43",
        "peak":       "#FF6B9D",
    }
    type_icons = {
        "hook":       "🎯",
        "transition": "✂️",
        "action":     "⚡",
        "peak":       "🔥",
    }

    cols = st.columns(min(len(moments), 4))
    for i, m in enumerate(moments[:8]):
        col = cols[i % 4]
        tc  = type_colors.get(m["type"], "#C8FF57")
        ti  = type_icons.get(m["type"], "📍")
        with col:
            st.markdown(
                f'<div style="background:#0E1218;border:1px solid rgba(255,255,255,0.08);'
                f'border-left:3px solid {tc};border-radius:10px;padding:12px 14px;margin-bottom:8px">'
                f'<div style="font-size:1.1rem;font-weight:800;color:{tc};font-family:Syne,sans-serif;line-height:1">'
                f'{ti} {m["time"]}</div>'
                f'<div style="font-size:0.78rem;color:rgba(255,255,255,0.6);margin-top:4px">{_esc(m["label"])}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION: Technical Analysis (creator-friendly labels)
# ─────────────────────────────────────────────────────────────────────────────
def render_technical_analysis(data: dict):
    v = data["visual_analysis"]
    h = data["hook_analysis"]
    a = data["audio_analysis"]

    # Creator-friendly label converters
    def _bright_label(score):
        if score >= 75: return ("Overexposed", "🔴")
        if score >= 55: return ("Good",         "🟢")
        if score >= 35: return ("Good",         "🟢")
        if score >= 20: return ("Dark",         "🟡")
        return ("Too Dark", "🔴")

    def _contrast_label(score):
        if score >= 55: return ("High",   "🟢")
        if score >= 30: return ("Good",   "🟢")
        if score >= 15: return ("Low",    "🟡")
        return ("Flat", "🔴")

    def _stable_label(label):
        m = {"stable": ("Stable","🟢"), "minor_shake": ("Some Shake","🟡"), "shaky": ("Unstable","🔴")}
        return m.get(label, ("OK","⚪"))

    def _noise_label(label):
        m = {"clean": ("Clean","🟢"), "slight_noise": ("Slight Grain","🟡"),
             "noisy": ("Noisy","🔴"), "none": ("Clean","🟢")}
        return m.get(label, ("OK","⚪"))

    def _vol_label(label):
        m = {"good": ("Balanced","🟢"), "too_quiet": ("Too Quiet","🔴"),
             "too_loud": ("Too Loud","🔴"), "clipping": ("Clipping","🔴")}
        return m.get(label, ("OK","⚪"))

    tab_vis, tab_hook, tab_audio = st.tabs(["🎥  Visual Quality", "⚡  Hook (First 3s)", "🎵  Audio"])

    with tab_vis:
        st.markdown("<br>", unsafe_allow_html=True)
        b_lbl, b_dot = _bright_label(v["brightness_score"])
        c_lbl, c_dot = _contrast_label(v["contrast_score"])
        s_lbl, s_dot = _stable_label(v["stability_label"])
        n_lbl, n_dot = _noise_label(v["noise_label"])
        fl = v["framing_label"].replace("_"," ").title()
        f_dot = "🟢" if v["framing_label"] == "good" else ("🔴" if "small" in v["framing_label"] else "🟡")

        items = [
            ("Lighting Quality",  b_lbl, b_dot, f"Raw: {v['brightness_score']:.0f}/100"),
            ("Image Contrast",    c_lbl, c_dot, f"Raw: {v['contrast_score']:.0f}/100"),
            ("Camera Stability",  s_lbl, s_dot, f"Raw: {v['stability_score']:.0f}/100"),
            ("Video Grain/Noise", n_lbl, n_dot, f"Noise level: {v['noise_level']:.0f}/100"),
            ("Subject Framing",   fl,    f_dot, "Based on subject position in frame"),
            ("Motion Energy",     f"{v['motion_energy']:.0f}/100", "⚪", "Average motion across all frames"),
        ]
        for label, val, dot, tip in items:
            ca, cb = st.columns([3, 2])
            with ca:
                st.markdown(
                    f'<span style="font-size:0.95rem;color:rgba(255,255,255,0.7)">{label}</span>'
                    f'<span style="font-size:0.7rem;color:rgba(255,255,255,0.2);margin-left:6px">({tip})</span>',
                    unsafe_allow_html=True
                )
            with cb:
                st.markdown(f'<span style="font-size:0.95rem;font-weight:600">{dot} {val}</span>', unsafe_allow_html=True)
            st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.05);margin:4px 0'>", unsafe_allow_html=True)

    with tab_hook:
        st.markdown("<br>", unsafe_allow_html=True)
        hs = h["hook_score"]
        if h["has_strong_hook"]:
            st.success(f"**Strong Hook** — Score: {hs}/10")
        else:
            st.error(f"**Weak Hook** — Score: {hs}/10")
        st.progress(hs / 10)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'> {_esc(h["hook_assessment"])}')

    with tab_audio:
        st.markdown("<br>", unsafe_allow_html=True)
        v_lbl, v_dot = _vol_label(a["volume_label"])
        cl_dot = "🔴" if a["clipping_detected"] else "🟢"
        cl_lbl = "Detected ⚠️" if a["clipping_detected"] else "Clean ✓"
        n_lbl2, n_dot2 = ("Noisy","🔴") if a["noise_label"] == "noisy" else ("Clean","🟢")
        tempo_str = f"{a['tempo_bpm']:.0f} BPM" if a.get("tempo_bpm") else "N/A"

        items3 = [
            ("Audio Type",      a["audio_type"].replace("+"," + ").title(), "⚪", ""),
            ("Volume Level",    v_lbl,  v_dot, f"RMS: {a.get('rms_loudness',0):.0f} dB"),
            ("Clipping",        cl_lbl, cl_dot, "Distortion when audio peaks"),
            ("Background Noise",n_lbl2, n_dot2, ""),
            ("Tempo",           tempo_str, "⚪", "Energy of background music"),
            ("Silent Gaps",     f"{a['silence_percentage']:.0f}%", "🟡" if a["silence_percentage"] > 20 else "🟢", "Percentage of video with silence"),
        ]
        for label, val, dot, tip in items3:
            ca, cb = st.columns([3, 2])
            with ca:
                st.markdown(
                    f'<span style="font-size:0.95rem;color:rgba(255,255,255,0.7)">{label}</span>'
                    + (f'<span style="font-size:0.7rem;color:rgba(255,255,255,0.2);margin-left:6px">({tip})</span>' if tip else ""),
                    unsafe_allow_html=True
                )
            with cb:
                st.markdown(f'<span style="font-size:0.95rem;font-weight:600">{dot} {val}</span>', unsafe_allow_html=True)
            st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.05);margin:4px 0'>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION: Captions with strategy insight
# ─────────────────────────────────────────────────────────────────────────────
def render_captions_section(captions, category=""):
    # Caption strategy tip per niche
    strategy_tips = {
        "Music Performance": ("Short & emotional — let the music speak first.", "Story Style"),
        "Sports":            ("Short and punchy — match the fast-paced energy of sports content.", "Viral One-Liner"),
        "Fitness":           ("Motivational tone — speak to the transformation.", "Scroll-Stopping"),
        "Tech Review":       ("Informative opener — state the main verdict immediately.", "Question Caption"),
        "Dance":             ("Energy-first — short caption, all the energy in the video.", "Viral One-Liner"),
        "Food & Cooking":    ("Make them hungry with one sentence before showing the dish.", "Story Style"),
        "Tutorial":          ("Tell them exactly what they'll learn — saves are your goal.", "Scroll-Stopping"),
        "Travel":            ("Paint the picture first — transport them before they watch.", "Story Style"),
        "Comedy":            ("One line that teases the punchline without giving it away.", "Viral One-Liner"),
    }
    tip, rec_style = strategy_tips.get(category, ("Match the tone of your content — authentic captions outperform promotional ones.", "Scroll-Stopping"))

    st.markdown(
        f'<div style="background:#0E1218;border:1px solid rgba(200,255,87,0.15);border-radius:12px;'
        f'padding:14px 18px;margin-bottom:20px">'
        f'<div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;'
        f'color:#C8FF57;margin-bottom:6px">Recommended Caption Strategy for {_esc(category)}</div>'
        f'<p style="font-size:0.9rem;color:rgba(255,255,255,0.75);margin:0 0 6px 0">{_esc(tip)}</p>'
        f'<div style="font-size:0.78rem;color:rgba(255,255,255,0.4)">Best performing style: '
        f'<span style="color:#C8FF57;font-weight:600">{_esc(rec_style)}</span></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    styles = [
        ("scroll_stopping", "🔥 Scroll-Stopping",  "Opens strong — makes people stop mid-scroll"),
        ("viral_one_liner",  "⚡ Viral One-Liner",   "Single punchy line made for shares"),
        ("question",         "❓ Question Caption",  "Triggers comments and debate"),
        ("story",            "📖 Story Style",       "First-person context that builds connection"),
    ]
    key_fallbacks = {
        "scroll_stopping": ["engaging", "scroll_stopping"],
        "viral_one_liner":  ["viral_short", "viral_one_liner"],
        "question":         ["question_based", "question"],
        "story":            ["story_style", "story"],
    }
    col1, col2 = st.columns(2)
    cols_list = [col1, col2, col1, col2]
    for (key, label, hint), col in zip(styles, cols_list):
        text = ""
        for k in key_fallbacks.get(key, [key]):
            text = captions.get(k, "")
            if text:
                break
        with col:
            with st.expander(label, expanded=True):
                st.caption(hint)
                if text:
                    st.markdown(
                        f'<div style="font-size:0.95rem;line-height:1.75;padding:8px 0;'
                        f'color:rgba(255,255,255,0.85)">{_esc(text)}</div>',
                        unsafe_allow_html=True
                    )
                    st.code(text, language=None)
                else:
                    st.caption("Caption not available")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION: Grouped Hashtags
# ─────────────────────────────────────────────────────────────────────────────
def render_hashtags_section(hashtags, hashtag_groups=None):
    if hashtag_groups and any(hashtag_groups.values()):
        groups = [
            ("🚀 High Reach", hashtag_groups.get("high", []),   "#FF6B9D", "Millions of posts — maximum discoverability"),
            ("🎯 Mid Reach",  hashtag_groups.get("medium", []), "#57C8FF", "100K–1M posts — targeted community reach"),
            ("💎 Niche",      hashtag_groups.get("niche", []),  "#C8FF57", "Under 100K — deep niche authority"),
        ]
        for group_label, tags, color, desc in groups:
            if not tags:
                continue
            st.markdown(
                f'<div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:0.1em;color:{color};margin:16px 0 8px 0">'
                f'{group_label} <span style="font-weight:400;color:rgba(255,255,255,0.3);'
                f'text-transform:none;letter-spacing:0">{desc}</span></div>',
                unsafe_allow_html=True
            )
            chips = " ".join(
                f'<span style="background:#0E1218;border:1px solid {color}33;border-radius:6px;'
                f'padding:5px 13px;font-size:0.85rem;color:{color};margin:3px;'
                f'display:inline-block;font-weight:500">{_esc(t)}</span>'
                for t in tags
            )
            st.markdown(f'<div style="line-height:2.4">{chips}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Copy all hashtags:**")
        st.code(" ".join(hashtags), language=None)
    else:
        # Flat fallback
        st.caption("25 optimised hashtags — mix of high-volume, mid-tier, and niche tags")
        chips = " ".join(
            f'<span style="background:#141920;border:1px solid rgba(255,255,255,0.1);'
            f'border-radius:6px;padding:5px 13px;font-size:0.85rem;color:#57C8FF;'
            f'margin:3px;display:inline-block;font-weight:500">{_esc(h)}</span>'
            for h in hashtags
        )
        st.markdown(f'<div style="line-height:2.4;margin-bottom:16px">{chips}</div>', unsafe_allow_html=True)
        st.markdown("**Copy all hashtags:**")
        st.code(" ".join(hashtags), language=None)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION: Thumbnail with why-it-works breakdown
# ─────────────────────────────────────────────────────────────────────────────
def render_thumbnail_section(thumbnail, frames):
    from pathlib import Path as _Path

    frame_path_str = thumbnail.get("frame_path", "")
    frame_path = _Path(frame_path_str) if frame_path_str else None
    if not frame_path or not frame_path.exists():
        idx = thumbnail.get("frame_index", 0)
        if frames and idx < len(frames):
            frame_path = _Path(str(frames[idx]))

    col1, col2 = st.columns([1, 1])

    with col1:
        if frame_path and frame_path.exists():
            try:
                from PIL import Image as _PIL
                img = _PIL.open(str(frame_path))
                st.image(img, caption="Best thumbnail frame", width=300)
            except Exception:
                try:
                    st.image(str(frame_path), width=300)
                except Exception as e:
                    st.error(f"Preview error: {e}")
        else:
            st.info("Thumbnail preview unavailable — frame file was cleaned up.")

    with col2:
        st.markdown("**Why this frame was selected:**")
        reason = thumbnail.get("reason", "Best available frame")
        st.markdown(
            f'<div style="background:#0E1218;border-radius:10px;padding:14px 16px;'
            f'font-size:0.9rem;line-height:1.7;color:rgba(255,255,255,0.75);margin-bottom:12px">'
            f'{_esc(reason)}</div>',
            unsafe_allow_html=True
        )

        # Why-it-works breakdown
        st.markdown(
            '<div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;'
            'letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:8px">Quality signals</div>',
            unsafe_allow_html=True
        )
        bd = thumbnail.get("_score_breakdown", {}) or {}
        signals = [
            ("Sharpness",      bd.get("sharpness_raw", 0) > 150,  "In focus" if bd.get("sharpness_raw",0)>150 else "Slightly soft"),
            ("Brightness",     bd.get("brightness", 0) >= 14,     "Well exposed" if bd.get("brightness",0)>=14 else "Check exposure"),
            ("Face visible",   bd.get("faces", 0) > 0,            "Face detected (boosts CTR)" if bd.get("faces",0)>0 else "No face detected"),
            ("Contrast",       bd.get("contrast", 0) >= 8,        "Good contrast" if bd.get("contrast",0)>=8 else "Low contrast"),
            ("Color vibrancy", bd.get("vibrancy", 0) >= 4,        "Vibrant colors" if bd.get("vibrancy",0)>=4 else "Muted colors"),
        ]
        for label, is_good, val in signals:
            icon = "✅" if is_good else "⚠️"
            ca, cb = st.columns([2, 3])
            with ca: st.markdown(f'<span style="font-size:0.82rem;color:rgba(255,255,255,0.5)">{label}</span>', unsafe_allow_html=True)
            with cb: st.markdown(f'<span style="font-size:0.82rem">{icon} {val}</span>', unsafe_allow_html=True)

        tip = thumbnail.get("overlay_text_suggestion", "")
        if tip:
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"💡 **Overlay tip:** {tip}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption(f"Position: {thumbnail.get('timestamp_note', '')}")
        if frame_path and frame_path.exists():
            try:
                with open(str(frame_path), "rb") as f:
                    img_bytes = f.read()
                st.download_button("⬇️  Download Best Thumbnail", data=img_bytes,
                                   file_name="thumbnail.jpg", mime="image/jpeg")
            except Exception as e:
                st.error(f"Download error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# CREATOR GROWTH INTELLIGENCE — render functions
# ─────────────────────────────────────────────────────────────────────────────

def render_algorithm_score(alg: dict):
    """Feature 2 — Estimated Algorithm Performance."""
    score = alg.get("score", 0)
    tier  = alg.get("tier", "")
    reach = alg.get("reach", "")
    limiting = alg.get("limiting", "")
    color = score_color(score)

    tier_colors = {
        "Viral Potential":  "#6BCB77",
        "High Reach":       "#C8FF57",
        "Moderate Reach":   "#FFD93D",
        "Low Reach":        "#FF9F43",
        "Weak Performance": "#FF4757",
    }
    tc = tier_colors.get(tier, "#C8FF57")

    col_score, col_detail = st.columns([1, 3])
    with col_score:
        st.markdown(
            f'<div style="background:#0E1218;border:1px solid rgba(255,255,255,0.08);'
            f'border-radius:14px;padding:22px 16px;text-align:center">'
            f'<div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:8px">Algorithm Score</div>'
            f'<div style="font-size:2.8rem;font-weight:800;color:{color};'
            f'font-family:Syne,sans-serif;line-height:1">{score}</div>'
            f'<div style="font-size:0.62rem;opacity:0.4;margin-top:4px">out of 10</div>'
            f'<div style="margin-top:12px;background:{tc}22;border:1px solid {tc}44;'
            f'border-radius:8px;padding:6px 10px">'
            f'<div style="font-size:0.78rem;font-weight:700;color:{tc}">{_esc(tier)}</div>'
            f'<div style="font-size:0.7rem;color:rgba(255,255,255,0.5);margin-top:2px">'
            f'Est. {_esc(reach)}</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )
    with col_detail:
        # Metric bars
        metrics = alg.get("_metrics", {})
        if metrics:
            st.markdown('<p style="font-size:0.65rem;font-weight:700;text-transform:uppercase;'
                        'letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:10px">'
                        'Score Breakdown</p>', unsafe_allow_html=True)
            for label, val in metrics.items():
                pct = int(val / 10 * 100)
                bar_color = "#6BCB77" if val >= 7 else ("#FFD93D" if val >= 5 else "#FF4757")
                ca, cb, cc = st.columns([3, 5, 1])
                with ca: st.markdown(f'<span style="font-size:0.82rem;color:rgba(255,255,255,0.6)">{label.title()}</span>', unsafe_allow_html=True)
                with cb:
                    st.markdown(
                        f'<div style="background:#1a1f2a;border-radius:4px;height:8px;margin-top:8px">'
                        f'<div style="background:{bar_color};width:{pct}%;height:8px;border-radius:4px"></div>'
                        f'</div>', unsafe_allow_html=True
                    )
                with cc: st.markdown(f'<span style="font-size:0.82rem;font-weight:600;color:{bar_color}">{val:.1f}</span>', unsafe_allow_html=True)

        if limiting:
            st.markdown("<br>", unsafe_allow_html=True)
            if "no major" in limiting.lower():
                st.success(f"✅ {limiting}")
            else:
                st.warning(f"⚠️ {limiting}")


def render_audience_psychology(psych: dict):
    """Feature 3 — Audience Psychology Insights."""
    rating_color = {"HIGH": "#6BCB77", "MEDIUM": "#FFD93D", "LOW": "#FF4757"}

    col1, col2 = st.columns([2, 3])
    with col1:
        metrics = [
            ("🧠 Curiosity",      psych.get("curiosity", "MEDIUM")),
            ("📚 Learning Value", psych.get("learning", "MEDIUM")),
            ("🎭 Entertainment",  psych.get("entertainment", "MEDIUM")),
            ("👁️ Visual Appeal",  psych.get("visual_appeal", "MEDIUM")),
        ]
        for label, rating in metrics:
            rc = rating_color.get(rating, "#FFD93D")
            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)">'
                f'<span style="font-size:0.9rem;color:rgba(255,255,255,0.7)">{label}</span>'
                f'<span style="background:{rc}22;color:{rc};border:1px solid {rc}44;'
                f'border-radius:6px;padding:2px 12px;font-size:0.75rem;font-weight:700">{rating}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    with col2:
        trigger = psych.get("trigger", "")
        stay    = psych.get("why_stay", "")
        drop    = psych.get("why_drop", "")

        st.markdown(
            f'<div style="background:#0E1218;border-radius:12px;padding:16px 18px;margin-bottom:10px">'
            f'<div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.1em;color:#C8FF57;margin-bottom:6px">Viewer Emotion Trigger</div>'
            f'<div style="font-size:1rem;font-weight:700;color:rgba(255,255,255,0.9)">{_esc(trigger)}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.success(f"**Why viewers stay:** {stay}")
        if "no major" in drop.lower():
            st.success(f"**Drop-off risk:** {drop}")
        else:
            st.warning(f"**Why viewers may drop:** {drop}")


def render_platform_scores(plat: dict):
    """Feature 4 — Platform Optimization."""
    platforms = [
        ("📸 Instagram Reels", plat.get("instagram", 0), "#E1306C"),
        ("🎵 TikTok",          plat.get("tiktok",    0), "#69C9D0"),
        ("▶️ YouTube Shorts",  plat.get("youtube",   0), "#FF0000"),
    ]
    best = plat.get("best", "")
    tip  = plat.get("best_tip", "")

    cols = st.columns(3)
    for col, (label, score, color) in zip(cols, platforms):
        is_best = label.split(" ", 1)[-1].strip() in best or any(w in best for w in label.split())
        with col:
            border = f"border:2px solid {color}" if is_best else "border:1px solid rgba(255,255,255,0.08)"
            badge  = f'<div style="font-size:0.65rem;font-weight:700;color:{color};margin-top:4px">★ BEST FIT</div>' if is_best else ""
            st.markdown(
                f'<div style="background:#0E1218;{border};border-radius:14px;'
                f'padding:20px 16px;text-align:center">'
                f'<div style="font-size:0.75rem;font-weight:600;color:rgba(255,255,255,0.5);'
                f'margin-bottom:10px">{label}</div>'
                f'<div style="font-size:2.4rem;font-weight:800;color:{color};'
                f'font-family:Syne,sans-serif;line-height:1">{score}</div>'
                f'<div style="font-size:0.62rem;opacity:0.4;margin-top:2px">/ 10</div>'
                f'{badge}</div>',
                unsafe_allow_html=True
            )

    if tip:
        st.markdown("<br>", unsafe_allow_html=True)
        st.info(f"💡 **{best} Tip:** {tip}")


def render_editing_fixes(fixes: list):
    """Feature 5 — AI Editing Fix Suggestions."""
    if not fixes:
        st.success("✅ No significant editing issues detected. The footage looks clean.")
        return

    for fix in fixes:
        issue   = fix.get("issue", "")
        icon    = fix.get("icon", "🔧")
        capcut  = fix.get("capcut", [])
        prem    = fix.get("premiere", [])
        dav     = fix.get("davinci", [])

        with st.expander(f"{icon} {issue}", expanded=True):
            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown('<p style="font-size:0.68rem;font-weight:700;color:#C8FF57;'
                            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">CapCut</p>',
                            unsafe_allow_html=True)
                for setting, value in capcut:
                    st.markdown(
                        f'<div style="background:#0E1218;border-radius:7px;padding:7px 12px;'
                        f'margin-bottom:5px;font-size:0.82rem">'
                        f'<span style="color:rgba(255,255,255,0.5)">{_esc(setting)}</span>'
                        f'<span style="float:right;font-weight:700;color:#C8FF57">{_esc(value)}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            with c2:
                st.markdown('<p style="font-size:0.68rem;font-weight:700;color:#57C8FF;'
                            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">Premiere Pro</p>',
                            unsafe_allow_html=True)
                for setting, value in prem:
                    st.markdown(
                        f'<div style="background:#0E1218;border-radius:7px;padding:7px 12px;'
                        f'margin-bottom:5px;font-size:0.82rem">'
                        f'<span style="color:rgba(255,255,255,0.5)">{_esc(setting)}</span>'
                        f'<span style="float:right;font-weight:700;color:#57C8FF">{_esc(value)}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            with c3:
                st.markdown('<p style="font-size:0.68rem;font-weight:700;color:#FF9F43;'
                            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">DaVinci Resolve</p>',
                            unsafe_allow_html=True)
                for setting, value in dav:
                    st.markdown(
                        f'<div style="background:#0E1218;border-radius:7px;padding:7px 12px;'
                        f'margin-bottom:5px;font-size:0.82rem">'
                        f'<span style="color:rgba(255,255,255,0.5)">{_esc(setting)}</span>'
                        f'<span style="float:right;font-weight:700;color:#FF9F43">{_esc(value)}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )


def render_viral_clips(clips: list):
    """Feature 6 — Auto Viral Clip Finder."""
    if not clips:
        st.caption("Clip detection requires video duration data.")
        return

    clip_colors = ["#C8FF57", "#57C8FF", "#FF9F43"]
    for i, clip in enumerate(clips):
        color = clip_colors[i % 3]
        st.markdown(
            f'<div style="background:#0E1218;border-left:4px solid {color};'
            f'border-radius:0 12px 12px 0;padding:16px 20px;margin-bottom:10px">'
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">'
            f'<span style="background:{color}22;color:{color};border-radius:6px;'
            f'padding:3px 12px;font-size:0.7rem;font-weight:700">CLIP {clip["clip_num"]}</span>'
            f'<span style="font-size:0.85rem;font-weight:700;color:{color};font-family:Syne,sans-serif">'
            f'{clip["start"]} – {clip["end"]}</span>'
            f'<span style="font-size:0.8rem;color:rgba(255,255,255,0.6)">{_esc(clip["label"])}</span>'
            f'</div>'
            f'<p style="font-size:0.88rem;color:rgba(255,255,255,0.7);margin:0">'
            f'{_esc(clip["reason"])}</p>'
            f'</div>',
            unsafe_allow_html=True
        )


def render_viral_titles(titles: list):
    """Feature 7 — Viral Title Ideas."""
    if not titles:
        st.caption("Title generation unavailable.")
        return

    for i, title in enumerate(titles, 1):
        st.markdown(
            f'<div style="background:#0E1218;border:1px solid rgba(200,255,87,0.12);'
            f'border-radius:10px;padding:14px 18px;margin-bottom:8px;'
            f'display:flex;align-items:flex-start;gap:12px">'
            f'<span style="font-size:0.7rem;font-weight:700;color:#C8FF57;min-width:22px;'
            f'margin-top:2px">#{i}</span>'
            f'<span style="font-size:0.95rem;color:rgba(255,255,255,0.88);line-height:1.5">'
            f'{_esc(title)}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown("<br>", unsafe_allow_html=True)
    all_titles = "\n".join(f"{i}. {t}" for i, t in enumerate(titles, 1))
    st.code(all_titles, language=None)

col_logo, col_badge = st.columns([5, 1])
with col_logo:
    st.markdown('<div style="display:flex;align-items:center;gap:12px;padding-bottom:12px"><span style="font-size:2rem">🎬</span><span style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;letter-spacing:-0.5px">Postlytics</span></div>', unsafe_allow_html=True)
with col_badge:
    st.markdown('<div style="text-align:right;padding-top:10px"><span style="background:rgba(200,255,87,0.1);color:#C8FF57;border:1px solid rgba(200,255,87,0.2);border-radius:100px;padding:4px 12px;font-size:0.7rem;font-weight:600;letter-spacing:0.06em">AI-POWERED</span></div>', unsafe_allow_html=True)

st.divider()

if "result" not in st.session_state:
    st.session_state.result = None
if "show_results" not in st.session_state:
    st.session_state.show_results = False


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD PAGE
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.show_results:
    st.markdown("""
    <div style="font-family:Syne,sans-serif;font-size:2.6rem;font-weight:800;letter-spacing:-2px;line-height:1.1;margin-bottom:0.4rem">
      Your reel, <span style="color:#C8FF57">professionally</span><br>reviewed in seconds.
    </div>
    <div style="color:rgba(255,255,255,0.5);font-size:1.05rem;margin-bottom:2rem">
      Upload before you post. Get honest, niche-specific feedback from an AI that thinks like a top creator in your space.
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Drop your reel here",
        type=["mp4", "mov", "webm", "avi"],
        label_visibility="collapsed",
        help="Supports MP4, MOV, WebM, AVI — max 200MB",
    )

    if uploaded_file:
        size_mb = len(uploaded_file.getbuffer()) / 1024 / 1024
        st.success(f"📎 **{uploaded_file.name}** · {size_mb:.1f} MB — ready to analyze")
        if st.button("🔍 Analyze My Reel"):
            with st.spinner(""):
                result = run_analysis(uploaded_file)
            st.session_state.result = result
            st.session_state.show_results = True
            st.rerun()
    else:
        st.markdown('<div style="text-align:center;padding:20px 0;color:rgba(255,255,255,0.25);font-size:0.85rem">Supports MP4 · MOV · WebM · AVI · Max 200MB</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div style="font-size:0.72rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,255,255,0.25);margin-bottom:16px">What you get</div>', unsafe_allow_html=True)
    features = [
        ("🎥", "Visual Quality", "Brightness, contrast, stability, framing"),
        ("⚡", "Hook Score",     "First 3 seconds — will viewers stay?"),
        ("🎵", "Audio Analysis", "Volume, noise, clipping, tempo"),
        ("🧠", "Postlytics",  "Niche-specific feedback & fixes"),
        ("✍️", "4 Captions",    "Engaging, viral, story, question styles"),
        ("#",  "25 Hashtags",   "Optimized mix for maximum reach"),
        ("🖼️", "Thumbnail",     "Best frame chosen by AI scoring"),
    ]
    f_cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(features):
        with f_cols[i % 4]:
            st.markdown(f"""
            <div style="background:#0E1218;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px;margin-bottom:12px">
              <div style="font-size:1.4rem;margin-bottom:8px">{icon}</div>
              <div style="font-family:Syne,sans-serif;font-size:0.88rem;font-weight:700;margin-bottom:4px">{title}</div>
              <div style="font-size:0.78rem;color:rgba(255,255,255,0.4);line-height:1.5">{desc}</div>
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RESULTS PAGE — 10 Sections
# ══════════════════════════════════════════════════════════════════════════════
else:
    data = st.session_state.result

    col_title, col_back = st.columns([4, 1])
    with col_title:
        st.markdown('<h2 style="font-family:Syne,sans-serif;font-size:2rem;font-weight:800;letter-spacing:-1px">Analysis <span style="color:#C8FF57">Complete</span></h2>', unsafe_allow_html=True)
    with col_back:
        if st.button("← Analyze Another"):
            st.session_state.result = None
            st.session_state.show_results = False
            st.rerun()

    # ── 1. OVERVIEW ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📋 Overview")
    render_overview(data)

    # ── 2. AI VIDEO UNDERSTANDING ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🤖 AI Video Understanding")
    st.caption("What Gemini Vision + YOLOv8 detected in your reel")
    cat        = data["content_category"]
    confidence = data.get("activity_confidence", "medium")
    objects    = data.get("detected_objects", [])
    activity   = data.get("primary_activity", "")
    environment= data.get("environment", "")
    yolo_ok    = data.get("yolo_available", False)
    conf_pct   = {"high": 92, "medium": 74, "low": 51}.get(confidence, 74)
    conf_color = {"high": "#6BCB77", "medium": "#C8FF57", "low": "#FFD93D"}.get(confidence, "#C8FF57")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div style="background:#0E1218;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:18px">'
            f'<div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:8px">Detected Category</div>'
            f'<div style="font-size:1.35rem;font-weight:800;color:#57C8FF;font-family:Syne,sans-serif">{_esc(cat)}</div>'
            f'<div style="font-size:0.78rem;color:{conf_color};font-weight:600;margin-top:6px">Confidence: {conf_pct}%</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with c2:
        act_display = activity if activity and activity != "Content creation" else "—"
        st.markdown(
            f'<div style="background:#0E1218;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:18px">'
            f'<div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:8px">Primary Activity</div>'
            f'<div style="font-size:1.05rem;font-weight:700;color:rgba(255,255,255,0.85);font-family:Syne,sans-serif;line-height:1.35">{_esc(act_display)}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with c3:
        env_display = environment if environment and environment != "Unknown" else "Not detected"
        st.markdown(
            f'<div style="background:#0E1218;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:18px">'
            f'<div style="font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:rgba(255,255,255,0.3);margin-bottom:8px">Environment</div>'
            f'<div style="font-size:0.95rem;font-weight:600;color:rgba(255,255,255,0.75);line-height:1.4">{_esc(env_display)}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    if objects:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<p style="font-size:0.62rem;font-weight:700;letter-spacing:0.12em;'
            'text-transform:uppercase;color:rgba(255,255,255,0.3);margin-bottom:8px">'
            f'DETECTED OBJECTS {"(YOLOv8)" if yolo_ok else "(Gemini)"}</p>',
            unsafe_allow_html=True
        )
        chips = " ".join(
            f'<span style="background:#141920;border:1px solid rgba(255,255,255,0.1);'
            f'border-radius:6px;padding:4px 12px;font-size:0.82rem;color:rgba(255,255,255,0.65);'
            f'margin:2px;display:inline-block">{_esc(o)}</span>'
            for o in objects[:15]
        )
        st.markdown(f'<div style="line-height:2.2">{chips}</div>', unsafe_allow_html=True)

    # Detected activities list (from activity_result)
    activity_result = getattr(st.session_state, "_last_activity_result", None)

    # ── 3. VIRAL POTENTIAL ANALYSIS ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🚀 Viral Potential Analysis")
    st.caption("Estimated from hook strength, motion energy, content type, pacing, and audio — no additional AI calls")
    render_viral_potential(data.get("viral_analysis", {}))

    # ── 4. HOOK ANALYSIS ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## ⚡ Hook Analysis — First 3 Seconds")
    st.caption("The opening 3 seconds determine whether viewers swipe or stay")
    render_hook_analysis(data.get("hook_analysis", {}), data.get("visual_analysis", {}))

    # ── 5. POSTLYTICS ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🧠 Postlytics")
    render_coaching_section(data["coaching_feedback"])

    # ── 6. TECHNICAL ANALYSIS ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Technical Analysis")
    st.caption("Measured by OpenCV (visual) and Librosa (audio)")
    render_technical_analysis(data)

    # ── 6b. RETENTION RISKS ───────────────────────────────────────────────────
    st.markdown("### ⚠️ Retention Risk Detection")
    st.caption("Segments where viewer drop-off is likely based on motion and pacing data")
    render_retention_risks(data.get("retention_risks", []))

    # ── 6c. KEY MOMENTS ───────────────────────────────────────────────────────
    st.markdown("### 🎯 Key Moments")
    st.caption("Notable moments detected from motion spikes and object detection")
    render_key_moments(data.get("key_moments", []))

    # ── 7. CREATOR GROWTH INTELLIGENCE ───────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🧬 Creator Growth Intelligence")
    st.caption("Advanced creator insights — algorithm prediction, audience psychology, platform fit, editing fixes, viral clips & titles")

    cgi_tab1, cgi_tab2, cgi_tab3, cgi_tab4, cgi_tab5 = st.tabs([
        "📈 Algorithm Performance",
        "🧠 Audience Psychology",
        "🌐 Platform Optimization",
        "✂️ Viral Clip Finder",
        "🏷️ Viral Title Ideas",
    ])

    with cgi_tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        render_algorithm_score(data.get("algorithm_score", {}))
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🔧 Editing Fix Suggestions")
        st.caption("Specific tool settings to fix detected issues in CapCut, Premiere Pro, and DaVinci Resolve")
        render_editing_fixes(data.get("editing_fixes", []))

    with cgi_tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        render_audience_psychology(data.get("audience_psych", {}))

    with cgi_tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        render_platform_scores(data.get("platform_scores", {}))

    with cgi_tab4:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Best 3-second clip windows based on motion spikes, hook strength, and object detection")
        render_viral_clips(data.get("viral_clips", []))

    with cgi_tab5:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("AI-generated scroll-stopping titles for this specific reel")
        render_viral_titles(data.get("viral_titles", []))

    # ── 8. CAPTIONS ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## ✍️ Caption Suggestions")
    render_captions_section(data["captions"], category=data.get("content_category", ""))

    # ── 9. HASHTAGS ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## # Hashtag Strategy")
    render_hashtags_section(data["hashtags"], hashtag_groups=data.get("hashtag_groups"))

    # ── 10. THUMBNAIL ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🖼️ Best Thumbnail")
    render_thumbnail_section(data["thumbnail"], data.get("_frames", []))

    st.markdown("---")
    st.caption("CreatorCoach AI · Analysis powered by Gemini Vision + YOLOv8 + OpenCV + Librosa")
