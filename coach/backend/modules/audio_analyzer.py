"""
Audio Analysis Module
─────────────────────────────────────────────
Uses Librosa to extract audio features from the extracted WAV file.

Extracts:
  - RMS loudness (dBFS)
  - Tempo (BPM)
  - Spectral centroid
  - Noise estimation
  - Silence percentage
  - Clipping detection

Classifies audio type: music / speech / speech+music / ambient / none
"""

import os
import numpy as np
from pathlib import Path
from typing import Dict, Any

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


class AudioAnalyzer:

    def analyze(self, audio_path: Path) -> Dict[str, Any]:
        """
        Full audio analysis pipeline.
        Returns a dict conforming to AudioMetrics schema.
        """
        if not audio_path.exists() or audio_path.stat().st_size < 100:
            return self._no_audio_result()

        if not LIBROSA_AVAILABLE:
            return self._fallback_result()

        try:
            y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        except Exception as e:
            return self._no_audio_result()

        if len(y) == 0:
            return self._no_audio_result()

        # ── RMS Loudness ──────────────────────────────────────────────────────
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = float(np.mean(rms))
        rms_db = float(librosa.amplitude_to_db(np.array([rms_mean]))[0])

        # ── Clipping detection ────────────────────────────────────────────────
        clipping = bool(np.any(np.abs(y) >= 0.99))

        # ── Tempo / BPM ───────────────────────────────────────────────────────
        try:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            tempo_bpm = float(tempo)
        except Exception:
            tempo_bpm = None

        # ── Spectral Centroid ─────────────────────────────────────────────────
        spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        avg_centroid = float(np.mean(spec_centroid))

        # ── Silence detection ─────────────────────────────────────────────────
        silence_threshold = 0.01
        silence_pct = float(np.mean(np.abs(y) < silence_threshold) * 100)

        # ── Noise estimation (via spectral flatness) ──────────────────────────
        flatness = librosa.feature.spectral_flatness(y=y)[0]
        avg_flatness = float(np.mean(flatness))  # 0=tonal, 1=noisy
        noise_level = avg_flatness * 100

        # ── Audio type classification ─────────────────────────────────────────
        audio_type = self._classify_audio_type(
            tempo_bpm, avg_centroid, avg_flatness, silence_pct, rms_db
        )

        # ── Volume label ──────────────────────────────────────────────────────
        volume_label = self._label_volume(rms_db, clipping)

        # ── Noise label ───────────────────────────────────────────────────────
        noise_label = "noisy" if noise_level > 50 else (
            "moderate_noise" if noise_level > 25 else "clean"
        )

        # ── Issues list ───────────────────────────────────────────────────────
        issues = self._detect_issues(rms_db, clipping, noise_level, silence_pct, audio_type)

        return {
            "audio_type": audio_type,
            "rms_loudness": round(rms_db, 1),
            "volume_label": volume_label,
            "tempo_bpm": round(tempo_bpm, 1) if tempo_bpm else None,
            "spectral_centroid": round(avg_centroid, 1),
            "noise_level": round(noise_level, 1),
            "noise_label": noise_label,
            "silence_percentage": round(silence_pct, 1),
            "clipping_detected": clipping,
            "issues": issues,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Audio type classifier
    # ─────────────────────────────────────────────────────────────────────────
    def _classify_audio_type(
        self,
        tempo: float,
        centroid: float,
        flatness: float,
        silence_pct: float,
        rms_db: float
    ) -> str:
        """
        Heuristic classification based on extracted audio features.
        
        Logic:
        - silence_pct > 80% → "none"
        - high tempo + low flatness + low centroid → music
        - low tempo + moderate centroid + higher flatness → speech
        - mixed → speech+music
        - very low signal → ambient
        """
        if silence_pct > 80:
            return "none"

        if rms_db < -40:
            return "ambient"

        has_rhythm = tempo is not None and tempo > 60
        is_tonal = flatness < 0.1        # low flatness = tonal/musical
        high_centroid = centroid > 3000  # speech tends to have higher centroid

        if is_tonal and has_rhythm and not high_centroid:
            return "music"
        elif high_centroid and not has_rhythm:
            return "speech"
        elif has_rhythm and high_centroid:
            return "speech+music"
        elif is_tonal:
            return "music"
        else:
            return "speech"

    # ─────────────────────────────────────────────────────────────────────────
    # Issue detection
    # ─────────────────────────────────────────────────────────────────────────
    def _detect_issues(
        self,
        rms_db: float,
        clipping: bool,
        noise_level: float,
        silence_pct: float,
        audio_type: str,
    ) -> list:
        issues = []

        if clipping:
            issues.append(
                f"Audio clipping detected (peaks hit 0 dBFS, RMS: {rms_db:.0f} dB) — "
                "this causes harsh digital distortion. Lower your recording gain by 20-30% "
                "or reduce the volume in your editing app."
            )

        if rms_db < -32:
            issues.append(
                f"Volume too quiet ({rms_db:.0f} dB RMS) — viewers on phone speakers will "
                "struggle to hear. Boost the audio track by at least {min(int(-20 - rms_db), 15)} dB in editing."
            )
        elif rms_db < -26:
            issues.append(
                f"Volume slightly low ({rms_db:.0f} dB RMS) — consider boosting by 6-8 dB "
                "so it sits comfortably on mobile speakers."
            )

        if rms_db > -4 and not clipping:
            issues.append(
                f"Volume very high ({rms_db:.0f} dB RMS) — riding close to clipping threshold. "
                "Lower the gain slightly to give yourself headroom."
            )

        if noise_level > 55 and audio_type in ("speech", "speech+music"):
            issues.append(
                f"Significant background noise detected (flatness: {noise_level:.0f}/100) — "
                "this competes with your voice. Try recording in a smaller room, "
                "using a lapel mic, or applying noise reduction in CapCut / Adobe Premiere."
            )
        elif noise_level > 30 and audio_type == "speech":
            issues.append(
                f"Mild background noise in speech ({noise_level:.0f}/100) — "
                "may be noticeable on headphones. A noise reduction pass in editing would clean this up."
            )

        if silence_pct > 40 and audio_type not in ("none", "ambient"):
            issues.append(
                f"{silence_pct:.0f}% of the video is silent — too many dead-air gaps slow "
                "the pacing and lose viewer attention. Tighten the edit or add background music."
            )
        elif silence_pct > 25 and audio_type == "speech":
            issues.append(
                f"Noticeable pauses in speech ({silence_pct:.0f}% silence) — "
                "consider trimming long gaps between sentences to keep energy up."
            )

        if audio_type == "none":
            issues.append(
                "No audio signal detected — silent videos perform significantly worse on all platforms. "
                "Add a voiceover, background music, or ambient sound."
            )

        return issues

    def _label_volume(self, rms_db: float, clipping: bool) -> str:
        if clipping:    return "too_loud"
        if rms_db > -6: return "too_loud"
        if rms_db < -30: return "too_quiet"
        return "good"

    def _no_audio_result(self):
        return {
            "audio_type": "none",
            "rms_loudness": -60.0,
            "volume_label": "too_quiet",
            "tempo_bpm": None,
            "spectral_centroid": 0.0,
            "noise_level": 0.0,
            "noise_label": "clean",
            "silence_percentage": 100.0,
            "clipping_detected": False,
            "issues": ["No audio detected in video"],
        }

    def _fallback_result(self):
        return {
            "audio_type": "unknown",
            "rms_loudness": -20.0,
            "volume_label": "good",
            "tempo_bpm": None,
            "spectral_centroid": 2000.0,
            "noise_level": 20.0,
            "noise_label": "clean",
            "silence_percentage": 10.0,
            "clipping_detected": False,
            "issues": ["Librosa not available — audio analysis limited"],
        }