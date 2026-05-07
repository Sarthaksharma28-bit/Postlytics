"""
Thumbnail Selector Module
─────────────────────────────────────────────
Scores every frame with OpenCV and picks the best one as thumbnail.

Criteria:
  - Sharpness  (Laplacian variance — blurry frames score low)
  - Brightness (ideal 80-180 on 0-255 scale)
  - Subject visibility (center region must have content)
  - Contrast   (std deviation of grayscale)
  - Position   (avoid first/last frames — often fade-in/out)

Returns the actual frame Path so the caller can display + download it directly.
"""

import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class ThumbnailSelector:

    def select_best(
        self,
        frames: List[Path],
        visual_metrics: Dict,
        session_id: str
    ) -> Dict[str, Any]:
        if not frames:
            return self._no_thumbnail()

        best_path, best_idx, reason = self._score_and_select(frames)

        # Copy to a persistent location for download
        out_dir = Path("static") / "thumbnails"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{session_id}_thumbnail.jpg"
        shutil.copy2(str(best_path), str(dest))

        # Duration estimate: frames are evenly spaced, so idx * (duration/total)
        # We don't have duration here so store frame index as a note
        total = len(frames)
        timestamp_note = f"frame {best_idx + 1} of {total}"

        return {
            "frame_index": best_idx,           # index into the frames list
            "frame_path": str(best_path),       # absolute path — used for preview + download
            "dest_path": str(dest),             # copy in static/ — used for web URL
            "timestamp_note": timestamp_note,
            "reason": reason,
            "overlay_text_suggestion": self._suggest_overlay(visual_metrics),
        }

    # ─────────────────────────────────────────────────────────────────────────
    def _score_and_select(self, frames: List[Path]):
        if not CV2_AVAILABLE:
            mid = len(frames) // 2
            return frames[mid], mid, "Selected from middle of video"

        scored = []
        for i, fp in enumerate(frames):
            s, breakdown = self._score_frame(fp, i, len(frames))
            scored.append((s, i, fp, breakdown))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_idx, best_path, breakdown = scored[0]
        return best_path, best_idx, self._build_reason(breakdown)

    def _score_frame(self, frame_path: Path, idx: int, total: int):
        score = 0.0
        breakdown = {}

        img = cv2.imread(str(frame_path))
        if img is None:
            return 0.0, {}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = img.shape[:2]

        # ── Sharpness (most important — blurry = bad thumbnail) ───────────────
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        # Give sharpness the most weight — a blurry thumbnail hurts CTR badly
        sharpness = min(lap_var / 40.0, 40.0)
        score += sharpness
        breakdown["sharpness"] = sharpness
        breakdown["sharpness_raw"] = lap_var

        # ── Brightness — ideal range 85-175 (not too dark, not blown out) ─────
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        brightness = float(np.mean(hsv[:, :, 2]))
        if 85 <= brightness <= 175:
            b_score = 25.0
        elif 65 <= brightness <= 200:
            b_score = 14.0
        elif 50 <= brightness <= 220:
            b_score = 7.0
        else:
            b_score = 0.0  # too dark or blown out
        score += b_score
        breakdown["brightness"] = b_score
        breakdown["brightness_raw"] = brightness

        # ── Face detection bonus — faces = higher CTR ─────────────────────────
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                face_bonus = min(len(faces) * 15.0, 20.0)
                score += face_bonus
                breakdown["faces"] = face_bonus
            else:
                breakdown["faces"] = 0.0
        except Exception:
            breakdown["faces"] = 0.0

        # ── Subject visibility — center region must have content ──────────────
        center = gray[h//4:3*h//4, w//4:3*w//4]
        c_std = float(np.std(center))
        subj = min(c_std / 2.5, 18.0)
        score += subj
        breakdown["subject"] = subj

        # ── Contrast ──────────────────────────────────────────────────────────
        contrast = min(float(np.std(gray)) / 4.5, 15.0)
        score += contrast
        breakdown["contrast"] = contrast

        # ── Color vibrancy (saturated frames look better as thumbnails) ───────
        saturation = float(np.mean(hsv[:, :, 1]))
        vibrancy = min(saturation / 12.0, 10.0)
        score += vibrancy
        breakdown["vibrancy"] = vibrancy

        # ── Avoid first and last 10% (often fade/black frames) ────────────────
        rel = idx / max(total - 1, 1)
        if 0.10 <= rel <= 0.90:
            score += 10.0
            breakdown["position"] = 10.0
        else:
            breakdown["position"] = 0.0

        return score, breakdown

    def _build_reason(self, breakdown: Dict) -> str:
        parts = []
        if breakdown.get("faces", 0) > 0:
            parts.append("face clearly visible (highest CTR)")
        if breakdown.get("sharpness_raw", 0) > 300:
            parts.append("sharp and in focus")
        elif breakdown.get("sharpness_raw", 0) > 100:
            parts.append("reasonably sharp")
        if breakdown.get("brightness", 0) >= 25:
            parts.append("well-exposed")
        if breakdown.get("vibrancy", 0) > 6:
            parts.append("vibrant colors")
        if breakdown.get("contrast", 0) > 10:
            parts.append("good contrast")
        return "Selected for: " + (", ".join(parts) if parts else "best available frame")

    def _suggest_overlay(self, visual_metrics: Dict) -> str:
        # Pick contextual overlay tip based on visual issues
        if visual_metrics.get("framing_label") == "subject_too_small":
            return "Crop tighter or zoom in before adding text overlay"
        if visual_metrics.get("brightness_label") == "too_dark":
            return "Brighten this frame in editing before using as thumbnail"
        return "Add a bold 1-3 word hook text overlay to increase click-through rate"

    def _no_thumbnail(self):
        return {
            "frame_index": 0,
            "frame_path": "",
            "dest_path": "",
            "timestamp_note": "N/A",
            "reason": "No frames available",
            "overlay_text_suggestion": None,
        }