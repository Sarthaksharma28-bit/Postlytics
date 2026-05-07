"""
Video Processing Module
─────────────────────────────────────────────
Responsibilities:
  1. Save uploaded video
  2. Extract one frame per second using OpenCV
  3. Extract audio track using FFmpeg
  4. Analyze visual quality metrics (brightness, contrast, noise, stability, framing)
  5. Analyze hook strength from first 3 frames
"""

import subprocess
import shutil
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


def _find_ffmpeg() -> str:
    """
    Return the ffmpeg executable path.
    Search order:
      1. System PATH  (works if ffmpeg is properly installed)
      2. imageio-ffmpeg bundled binary (pip install imageio-ffmpeg)
    Raises RuntimeError with clear instructions if not found.
    """
    # 1. Check PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    # 2. Try imageio-ffmpeg (ships its own ffmpeg binary)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass

    raise RuntimeError(
        "FFmpeg not found. Fix with one of two ways:\n"
        "  Option A (easiest): pip install imageio-ffmpeg\n"
        "  Option B: Install FFmpeg from https://www.gyan.dev/ffmpeg/builds/ "
        "and add the bin/ folder to your Windows PATH."
    )


class VideoProcessor:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.frames_dir = session_dir / "frames"
        self.frames_dir.mkdir(exist_ok=True)

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: process()
    # ─────────────────────────────────────────────────────────────────────────
    def process(self, video_path: Path) -> Dict[str, Any]:
        """
        Extract frames (1/sec) and audio from the video.
        Returns metadata dict with frame paths, audio path, fps, duration.
        """
        frames, fps, duration = self._extract_frames(video_path)
        audio_path = self._extract_audio(video_path)
        return {
            "frames": frames,
            "audio_path": audio_path,
            "fps": fps,
            "duration": duration,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Frame Extraction
    # ─────────────────────────────────────────────────────────────────────────
    # Architecture spec: extract frames at exactly these % positions
    FRAME_POSITIONS = [0.10, 0.25, 0.40, 0.55, 0.70, 0.90]

    def _extract_frames(self, video_path: Path, num_frames: int = 6):
        """
        Extract exactly 6 frames at 10/25/40/55/70/90% of video duration.
        These positions are specified in the architecture doc to ensure
        full coverage of the reel from start to finish.
        """
        if not CV2_AVAILABLE:
            return self._extract_frames_ffmpeg(video_path)

        cap = cv2.VideoCapture(str(video_path))
        fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration     = total_frames / fps

        # Use spec positions; fall back to evenly-spaced if video is very short
        if total_frames >= 6:
            target_indices = [
                max(0, min(int(p * total_frames), total_frames - 1))
                for p in self.FRAME_POSITIONS
            ]
        else:
            target_indices = list(range(total_frames))

        frame_paths = []
        for saved_idx, frame_idx in enumerate(target_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue
            frame_path = self.frames_dir / f"frame_{saved_idx:04d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            frame_paths.append(frame_path)

        cap.release()
        return frame_paths, fps, duration

    def _extract_frames_ffmpeg(self, video_path: Path, num_frames: int = 6):
        """Fallback: use ffmpeg to extract 6 frames at spec positions (10/25/40/55/70/90%)."""
        ffmpeg = _find_ffmpeg()

        # Get duration
        try:
            probe = subprocess.run(
                [ffmpeg.replace("ffmpeg", "ffprobe"), "-v", "error",
                 "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                capture_output=True, text=True
            )
            duration = float(probe.stdout.strip()) if probe.stdout.strip() else 15.0
        except Exception:
            duration = 15.0

        # Extract each frame at the exact spec timestamp
        frame_paths = []
        for idx, pct in enumerate(self.FRAME_POSITIONS):
            t = pct * duration
            out_path = self.frames_dir / f"frame_{idx:04d}.jpg"
            cmd = [
                ffmpeg, "-ss", str(t), "-i", str(video_path),
                "-vframes", "1", "-q:v", "2",
                str(out_path), "-y", "-loglevel", "error"
            ]
            try:
                subprocess.run(cmd, check=True)
                if out_path.exists():
                    frame_paths.append(out_path)
            except Exception:
                pass

        return sorted(frame_paths), 30.0, duration

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Audio Extraction
    # ─────────────────────────────────────────────────────────────────────────
    def _extract_audio(self, video_path: Path) -> Path:
        """Extract audio track to WAV using FFmpeg."""
        audio_path = self.session_dir / "audio.wav"
        try:
            ffmpeg = _find_ffmpeg()
        except RuntimeError as e:
            # FFmpeg not available — return empty audio file, audio analysis will skip
            audio_path.touch()
            return audio_path

        cmd = [
            ffmpeg, "-i", str(video_path),
            "-vn",                         # no video
            "-acodec", "pcm_s16le",        # WAV PCM
            "-ar", "44100",                # 44.1kHz
            "-ac", "1",                    # mono
            str(audio_path),
            "-y", "-loglevel", "error"
        ]
        try:
            subprocess.run(cmd, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # FFmpeg failed or not found — return empty file so audio analysis
            # gracefully skips rather than crashing the whole pipeline
            audio_path.touch()
        return audio_path

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: analyze_visual_quality()
    # ─────────────────────────────────────────────────────────────────────────
    def analyze_visual_quality(self, frames: List[Path]) -> Dict[str, Any]:
        """
        Analyze brightness, contrast, noise, stability, framing, motion energy
        across all extracted frames.
        """
        if not frames:
            return self._default_visual_metrics()

        brightness_values = []
        contrast_values = []
        noise_values = []
        motion_values = []
        prev_gray = None

        for frame_path in frames:
            if not CV2_AVAILABLE:
                break
            img = cv2.imread(str(frame_path))
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Brightness: mean of V channel (0–255 → 0–100)
            brightness = float(np.mean(hsv[:, :, 2])) / 2.55
            brightness_values.append(brightness)

            # Contrast: std deviation of grayscale (normalized)
            contrast = float(np.std(gray)) / 1.28
            contrast_values.append(min(contrast, 100))

            # Noise: Laplacian variance (higher = more detail, lower = blurry/noisy)
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            noise_values.append(laplacian_var)

            # Motion: frame difference from previous
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                motion_values.append(float(np.mean(diff)))
            prev_gray = gray

        # ── Compute averages ──────────────────────────────────────────────────
        avg_brightness = float(np.mean(brightness_values)) if brightness_values else 50.0
        avg_contrast = float(np.mean(contrast_values)) if contrast_values else 50.0
        avg_noise = float(np.mean(noise_values)) if noise_values else 100.0
        avg_motion = float(np.mean(motion_values)) if motion_values else 0.0

        # ── Stability: measure variance of motion (low variance = stable) ─────
        motion_variance = float(np.var(motion_values)) if len(motion_values) > 1 else 0.0
        stability_score = max(0.0, 100.0 - min(motion_variance / 2.0, 100.0))

        # ── Framing: check if subject dominates center ─────────────────────────
        framing_label = self._analyze_framing(frames[len(frames)//2] if frames else None)

        # Normalize noise: high Laplacian var = sharp = low noise score
        normalized_noise = max(0.0, 100.0 - min(avg_noise / 50.0, 100.0))

        return {
            "brightness_score": round(avg_brightness, 1),
            "brightness_label": self._label_brightness(avg_brightness),
            "contrast_score": round(avg_contrast, 1),
            "contrast_label": self._label_contrast(avg_contrast),
            "noise_level": round(normalized_noise, 1),
            "noise_label": self._label_noise(normalized_noise),
            "stability_score": round(stability_score, 1),
            "stability_label": self._label_stability(stability_score),
            "framing_label": framing_label,
            "motion_energy": round(min(avg_motion, 100), 1),
        }

    def _analyze_framing(self, frame_path) -> str:
        """Check if main subject is visible and well-framed."""
        if not CV2_AVAILABLE or frame_path is None:
            return "good"
        img = cv2.imread(str(frame_path))
        if img is None:
            return "good"
        h, w = img.shape[:2]
        # Check center region has non-uniform content (subject present)
        center = img[h//4:3*h//4, w//4:3*w//4]
        center_std = float(np.std(center))
        if center_std < 15:
            return "subject_off_center"
        # Check if image is mostly one color (empty frame / subject too small)
        full_std = float(np.std(img))
        if full_std < 20:
            return "subject_too_small"
        return "good"

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: analyze_hook()
    # ─────────────────────────────────────────────────────────────────────────
    def analyze_hook(self, hook_frames: List[Path]) -> Dict[str, Any]:
        """
        Analyze the first 3 seconds (frames) for hook strength.
        Returns hook assessment dict.
        """
        if not hook_frames or not CV2_AVAILABLE:
            return self._default_hook()

        motion_values = []
        prev_gray = None
        scene_change = False

        for frame_path in hook_frames:
            img = cv2.imread(str(frame_path))
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                motion = float(np.mean(diff))
                motion_values.append(motion)
                # Scene change: very large difference between frames
                if motion > 40:
                    scene_change = True
            prev_gray = gray

        avg_motion = float(np.mean(motion_values)) if motion_values else 0.0

        # Check subject visibility in first frame
        subject_visible = self._analyze_framing(hook_frames[0]) == "good"

        # Hook score: combination of motion, scene change, subject visibility
        hook_score = 0.0
        if avg_motion > 20:   hook_score += 3.0
        elif avg_motion > 10: hook_score += 1.5
        if scene_change:      hook_score += 2.5
        if subject_visible:   hook_score += 2.5
        if avg_motion > 5:    hook_score += 1.0
        hook_score = min(hook_score, 10.0)

        has_strong_hook = hook_score >= 6.0

        if hook_score >= 8:
            assessment = "Strong opening — the first 3 seconds are visually engaging with clear subject and movement."
        elif hook_score >= 6:
            assessment = "Decent hook with some visual energy, but could be more attention-grabbing."
        elif hook_score >= 4:
            assessment = "Weak hook — the opening 3 seconds lack visual variety or clear subject focus."
        else:
            assessment = "Very weak hook — the reel opens with minimal movement and low visual impact, likely causing early swipe-offs."

        return {
            "has_strong_hook": has_strong_hook,
            "motion_intensity": round(avg_motion, 2),
            "scene_change_detected": scene_change,
            "subject_visible": subject_visible,
            "hook_score": round(hook_score, 1),
            "hook_assessment": assessment,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Label Helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _label_brightness(self, val: float) -> str:
        if val > 75: return "overexposed"
        if val < 30: return "too_dark"
        return "good"

    def _label_contrast(self, val: float) -> str:
        if val < 20: return "low_contrast"
        if val > 85: return "high_contrast"
        return "good"

    def _label_noise(self, val: float) -> str:
        if val > 60: return "noisy"
        if val > 35: return "moderate_noise"
        return "clean"

    def _label_stability(self, val: float) -> str:
        if val >= 80: return "stable"
        if val >= 55: return "minor_shake"
        return "shaky"

    def _default_visual_metrics(self):
        return {
            "brightness_score": 50.0, "brightness_label": "good",
            "contrast_score": 50.0,   "contrast_label": "good",
            "noise_level": 20.0,      "noise_label": "clean",
            "stability_score": 80.0,  "stability_label": "stable",
            "framing_label": "good",  "motion_energy": 10.0,
        }

    def _default_hook(self):
        return {
            "has_strong_hook": False, "motion_intensity": 0.0,
            "scene_change_detected": False, "subject_visible": True,
            "hook_score": 5.0, "hook_assessment": "Hook analysis unavailable.",
        }