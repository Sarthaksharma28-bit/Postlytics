# -*- coding: utf-8 -*-
"""
Content Understanding — Multi-frame Gemini Vision
──────────────────────────────────────────────────
Sends ALL 6 frames in ONE request:
    model.generate_content(["prompt", pil_img1, pil_img2, ...pil_img6])

No deprecated APIs. No hardcoded model names.
Model is auto-detected by gemini_client.py at startup.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from modules.gemini_client import get_model, get_model_name

PROMPT = """You are analyzing frames from a short-form social media video (Instagram Reel / TikTok).

These frames represent the video from start to finish.

Your tasks:
1. Describe exactly what is happening in the video.
2. Identify the EXACT main activity (e.g. "playing acoustic guitar", "playing tennis", "doing deadlifts", "reviewing an iPhone").
3. List every object, instrument, equipment, or product visible.
4. Describe the environment (indoor/outdoor, room type, setting, lighting).

CRITICAL RULES:
- Be specific. Never say "lifestyle content" or "creating content".
- CORRECT: "A person is playing an acoustic guitar while seated on a stool in a bedroom studio."
- WRONG: "A person is creating lifestyle content."
- If you see sports equipment → describe the sport.
- If you see musical instruments → describe the performance.
- Ignore background music tempo — describe only what you SEE in the frames.

Respond in EXACTLY this format:

Video Description:
[3-5 sentences describing exactly what is happening]

Primary Activity:
[one line — the exact main action, e.g. "Playing acoustic guitar", "Playing tennis", "Doing push-ups"]

Detected Objects:
[comma-separated list of every visible object, instrument, equipment]

Environment:
[one sentence — where is this filmed]"""


class ContentUnderstandingModule:

    def __init__(self):
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self._ready = bool(self._api_key)

    def understand(
        self,
        frame_descriptions: List[str],   # kept for compat, ignored
        audio_metrics: Dict,
        frame_paths: List[Path] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point — always returns a dict, never raises.
        Tries Gemini Vision; falls back to error dict on failure.
        """
        if not self._ready:
            return _error("GEMINI_API_KEY not set in backend/.env", audio_metrics)

        if not frame_paths:
            return _error("No frames provided", audio_metrics)

        result, err = self._vision(frame_paths, audio_metrics)
        return result if result else _error(err, audio_metrics)

    # ── Gemini Vision call ────────────────────────────────────────────────────
    def _vision(
        self,
        frame_paths: List[Path],
        audio_metrics: Dict,
    ) -> Tuple[Optional[Dict], str]:
        """
        Load PIL images, send to Gemini in ONE call.
        Returns (parsed_dict, "") on success or (None, error_str) on failure.
        """
        # --- Load PIL images ---
        try:
            from PIL import Image as PILImage
        except ImportError:
            return None, "Pillow not installed. Run: pip install Pillow"

        selected = _pick_frames(frame_paths, 6)
        images, failed = [], []
        for fp in selected:
            try:
                img = PILImage.open(str(fp)).convert("RGB")
                img.thumbnail((768, 768))
                images.append(img)
            except Exception as e:
                failed.append(str(e))

        if not images:
            return None, f"Could not load frames: {failed}"

        # --- Build prompt with audio context ---
        audio_ctx = _audio_note(audio_metrics)
        full_prompt = (
            PROMPT
            + f"\n\nAudio context (for reference only — do NOT let this override "
              f"what you see visually): {audio_ctx}"
        )

        # --- Single Gemini call: [prompt_str, pil_img, pil_img, ...] ---
        try:
            model = get_model()   # auto-detected model from gemini_client
            print(f"[ContentUnderstanding] Calling Gemini ({get_model_name()}) "
                  f"with {len(images)} frames")
            response = model.generate_content([full_prompt] + images)
            raw = response.text.strip()
            print(f"[ContentUnderstanding] Response received ({len(raw)} chars)")
            return _parse(raw), ""
        except Exception as e:
            return None, f"Gemini API error: {e}"

    # ── Legacy compat ─────────────────────────────────────────────────────────
    def detect_category(self, video_description: str) -> str:
        from modules.activity_detector import ActivityDetector
        r = ActivityDetector().detect(
            gemini_description=video_description,
            gemini_primary_activity="",
            yolo_objects=[],
            yolo_confidence={},
        )
        return r["category"]


# ── Module-level helpers ──────────────────────────────────────────────────────

def _pick_frames(paths: List[Path], n: int) -> List[Path]:
    if len(paths) <= n:
        return list(paths)
    step = len(paths) / n
    return [paths[int(i * step)] for i in range(n)]


def _audio_note(m: Dict) -> str:
    parts = [f"audio type: {m.get('audio_type','unknown')}"]
    if m.get("tempo_bpm"):
        parts.append(f"tempo {m['tempo_bpm']:.0f} BPM")
    parts.append(f"volume: {m.get('volume_label','unknown')}")
    return ", ".join(parts)


def _parse(raw: str) -> Dict[str, Any]:
    """Parse Gemini's structured text response into a dict."""
    out = {
        "video_description": "",
        "primary_activity":  "",
        "detected_objects":  [],
        "environment":       "",
        "gemini_error":      "",
    }
    section_map = {
        "video description:": "video_description",
        "primary activity:":  "primary_activity",
        "detected objects:":  "detected_objects",
        "environment:":       "environment",
    }
    current, buf = None, []

    for line in raw.split("\n"):
        s, lo = line.strip(), line.strip().lower()
        matched = False
        for key, field in section_map.items():
            if lo.startswith(key):
                if current and buf:
                    out[current] = " ".join(buf).strip()
                current = field
                after = s[len(key):].strip()
                buf = [after] if after else []
                matched = True
                break
        if not matched and current and s:
            buf.append(s)

    if current and buf:
        out[current] = " ".join(buf).strip()

    # objects → list
    raw_obj = out["detected_objects"]
    if isinstance(raw_obj, str) and raw_obj:
        out["detected_objects"] = [
            o.strip().lower()
            for o in raw_obj.replace(";", ",").split(",") if o.strip()
        ]

    if not out["video_description"] and len(raw) > 30:
        out["video_description"] = raw[:600]
    if not out["primary_activity"]:
        out["primary_activity"] = "Content creation"

    return out


def _error(err: str, audio_metrics: Dict) -> Dict[str, Any]:
    atype = audio_metrics.get("audio_type", "unknown")
    note = ""
    if atype == "music":
        bpm = audio_metrics.get("tempo_bpm")
        note = f" Background music at {bpm:.0f} BPM." if bpm else " Background music."
    elif atype == "speech":
        note = " Speech in audio."
    return {
        "video_description": f"Gemini Vision unavailable: {err}{note}",
        "primary_activity":  "Content creation",
        "detected_objects":  [],
        "environment":       "Unknown",
        "gemini_error":      err,
    }