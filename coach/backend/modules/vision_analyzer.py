# -*- coding: utf-8 -*-
"""
Vision Analysis Module
─────────────────────────────────────────────
Primary:  LLaVA via Ollama (local)
Fallback: Gemini Vision (if LLaVA times out or fails)

Why sequential instead of all-parallel:
  Ollama on a regular laptop can only process 1-2 LLaVA requests at a time.
  Sending 8 simultaneously causes most to queue and timeout.
  Sequential with a short timeout per frame + Gemini fallback is more reliable.

Flow:
  1. Try each frame with LLaVA (30s timeout per frame)
  2. If LLaVA fails/times out on a frame -> use Gemini for that frame
  3. If Gemini also not configured -> use OpenCV color/brightness description
"""

import base64
import os
import io
from pathlib import Path
from typing import List

import httpx
import google.generativeai as genai

VISION_BACKEND      = os.getenv("VISION_BACKEND", "ollama")
OLLAMA_BASE_URL     = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")
# Keys read inside __init__ to ensure .env is already loaded
GEMINI_MODEL        = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
NUM_FRAMES          = int(os.getenv("NUM_FRAMES", "6"))

# Shorter timeout so we fail fast and fall back to Gemini quickly
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "45"))

FRAME_PROMPT = (
    "Look at this image carefully and describe exactly what is happening. "
    "Include: who is in the frame (person, their appearance, what sport/activity/action they are doing), "
    "what objects are visible (ball, equipment, instrument, food, phone, etc), "
    "the environment (indoor/outdoor, court, gym, kitchen, street, etc), "
    "lighting quality, and camera angle. "
    "Be very specific. Do NOT say 'a person' -- describe what they are actually doing."
)


class VisionAnalyzer:

    def __init__(self, max_frames: int = NUM_FRAMES):
        self.max_frames = max_frames
        self._gemini_model = None
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        if GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self._gemini_model = genai.GenerativeModel(GEMINI_MODEL)
            except Exception:
                pass

    def analyze_frames(self, frame_paths: List[Path]) -> List[str]:
        if not frame_paths:
            return []

        # Subsample evenly
        if len(frame_paths) > self.max_frames:
            step = len(frame_paths) / self.max_frames
            frame_paths = [frame_paths[int(i * step)] for i in range(self.max_frames)]

        results = []
        for i, fp in enumerate(frame_paths):
            desc = self._describe_with_fallback(fp, i)
            results.append(desc)

        return results

    def _describe_with_fallback(self, frame_path: Path, idx: int) -> str:
        """
        Try in order:
          1. Configured backend (ollama/openai)
          2. Gemini Vision (fast fallback using already-configured API key)
          3. OpenCV color description (last resort, no AI needed)
        """
        # Step 1: try primary backend
        if VISION_BACKEND == "ollama":
            result = self._try_ollama(frame_path)
            if result and not result.startswith("["):
                return result
        elif VISION_BACKEND == "openai":
            result = self._try_openai(frame_path)
            if result and not result.startswith("["):
                return result

        # Step 2: Gemini Vision fallback
        if self._gemini_model:
            result = self._try_gemini(frame_path, idx)
            if result and not result.startswith("["):
                return result

        # Step 3: OpenCV fallback — at least describe the colors/brightness
        return self._opencv_fallback(frame_path, idx)

    # ── Backend: Ollama LLaVA ─────────────────────────────────────────────────
    def _try_ollama(self, frame_path: Path) -> str:
        try:
            img_b64 = self._encode_image(frame_path)
            payload = {
                "model": "llava",
                "prompt": FRAME_PROMPT,
                "images": [img_b64],
                "stream": False,
            }
            with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
                resp = client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
                resp.raise_for_status()
                text = resp.json().get("response", "").strip()
                return text if text else "[ollama: empty response]"
        except httpx.TimeoutException:
            return "[ollama: timed out]"
        except Exception as e:
            return f"[ollama: {str(e)[:60]}]"

    # ── Backend: Gemini Vision ────────────────────────────────────────────────
    def _try_gemini(self, frame_path: Path, idx: int) -> str:
        try:
            from PIL import Image as PILImage
            img = PILImage.open(str(frame_path))
            img.thumbnail((768, 768))
            response = self._gemini_model.generate_content([FRAME_PROMPT, img])
            text = response.text.strip()
            return text if text else "[gemini: empty response]"
        except Exception as e:
            return f"[gemini vision: {str(e)[:60]}]"

    # ── Backend: OpenAI GPT-4o ────────────────────────────────────────────────
    def _try_openai(self, frame_path: Path) -> str:
        try:
            img_b64 = self._encode_image(frame_path)
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "gpt-4o",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": FRAME_PROMPT},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{img_b64}",
                            "detail": "low"
                        }},
                    ],
                }],
                "max_tokens": 300,
            }
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload, headers=headers
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[openai: {str(e)[:60]}]"

    # ── Last resort: OpenCV pixel analysis ───────────────────────────────────
    def _opencv_fallback(self, frame_path: Path, idx: int) -> str:
        """Describe the frame using only pixel data — no AI needed."""
        try:
            import cv2
            import numpy as np
            img = cv2.imread(str(frame_path))
            if img is None:
                return f"Frame {idx+1}: Could not load image."
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            brightness = float(np.mean(hsv[:, :, 2])) / 255 * 100
            h, w = img.shape[:2]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            b_desc = "bright" if brightness > 60 else ("dark" if brightness < 30 else "moderately lit")
            s_desc = "sharp" if sharpness > 200 else ("slightly blurry" if sharpness > 50 else "blurry")
            return (
                f"Frame {idx+1}: {b_desc.capitalize()}, {s_desc} scene "
                f"({w}x{h}px, brightness: {brightness:.0f}%). "
                f"[Vision AI unavailable — enable Ollama or add GEMINI_API_KEY for full analysis]"
            )
        except Exception:
            return f"Frame {idx+1}: Frame captured. [Vision AI unavailable for detailed analysis]"

    # ── Helper ────────────────────────────────────────────────────────────────
    def _encode_image(self, frame_path: Path) -> str:
        try:
            from PIL import Image
            img = Image.open(str(frame_path))
            img.thumbnail((640, 640))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except ImportError:
            with open(frame_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")