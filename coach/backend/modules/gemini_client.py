# -*- coding: utf-8 -*-
"""
Gemini Client — Shared singleton with auto-model-detection
───────────────────────────────────────────────────────────
All Gemini modules import get_model() from here.

DETECTION ORDER:
  1. GEMINI_MODEL env var  →  use it if set
  2. genai.list_models()   →  find best flash/pro model for this API key
  3. Hardcoded fallback list  →  try known names until one works

This means the code NEVER hardcodes a model name and NEVER crashes
due to SDK version differences or renamed endpoints.

Usage in any module:
    from modules.gemini_client import get_model, get_model_name
    model = get_model()
    response = model.generate_content([prompt, img1, img2])
"""

import os
import google.generativeai as genai

# Module-level cache — initialised once, reused forever
_model: genai.GenerativeModel | None = None
_model_name: str = ""


# ── Model name candidates tried in order if auto-detect fails ────────────────
_FALLBACK_NAMES = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-pro",
    "gemini-1.5-pro-latest",
    "gemini-1.0-pro-vision",
    "gemini-pro-vision",
]


def _auto_detect_model(api_key: str) -> str:
    """
    Call genai.list_models() and return the best model name available
    for this API key that supports generateContent.

    Priority: flash > pro > anything else (newer version > older).
    """
    genai.configure(api_key=api_key)

    try:
        all_models = list(genai.list_models())
    except Exception as e:
        print(f"[GeminiClient] list_models() failed ({e}), skipping to fallback names")
        all_models = []

    # Filter to models that support generateContent (required for Vision)
    capable = [
        m for m in all_models
        if "generateContent" in (m.supported_generation_methods or [])
    ]

    if capable:
        # Prefer flash (fast + cheap), then pro, then anything
        for keyword in ["flash", "pro"]:
            pool = [m for m in capable if keyword in m.name.lower()]
            if pool:
                # Sort descending → newer version wins (1.5 > 1.0)
                best = sorted(pool, key=lambda m: m.name, reverse=True)[0]
                print(f"[GeminiClient] Auto-detected model: {best.name}")
                return best.name

        # Fallback: take whatever is available
        best = sorted(capable, key=lambda m: m.name, reverse=True)[0]
        print(f"[GeminiClient] Auto-detected model (fallback pool): {best.name}")
        return best.name

    # list_models returned nothing useful — try hardcoded names one by one
    print("[GeminiClient] No models from list_models(), probing fallback names...")
    for name in _FALLBACK_NAMES:
        try:
            probe = genai.GenerativeModel(name)
            # Minimal probe: generate with empty content raises 400 not 404
            probe.generate_content("ping")
        except Exception as e:
            err = str(e)
            if "404" in err or "not found" in err.lower():
                # Model name doesn't exist for this API key — skip
                continue
            # Any other error (400 bad request, 429 quota, etc.) means the
            # model name IS valid, just the request was bad.
            print(f"[GeminiClient] Found working model via probe: {name} ({err[:60]})")
            return name
    raise RuntimeError(
        "No compatible Gemini model found. "
        "Check your GEMINI_API_KEY is valid and your network is up."
    )


def get_model() -> genai.GenerativeModel:
    """
    Return a shared GenerativeModel instance, initialised on first call.
    Thread-safe for reads; call from main thread before spawning workers
    to guarantee the singleton is warm.
    """
    global _model, _model_name

    if _model is not None:
        return _model

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Add it to backend/.env and restart Streamlit."
        )

    # Honour explicit override, otherwise auto-detect
    env_name = os.getenv("GEMINI_MODEL", "").strip()
    if env_name:
        genai.configure(api_key=api_key)
        _model_name = env_name
        print(f"[GeminiClient] Using model from GEMINI_MODEL env: {_model_name}")
    else:
        _model_name = _auto_detect_model(api_key)

    _model = genai.GenerativeModel(_model_name)
    print(f"[GeminiClient] Model ready: {_model_name}")
    return _model


def get_model_name() -> str:
    """Return the selected model name (call get_model() first)."""
    return _model_name or os.getenv("GEMINI_MODEL", "not initialised yet")


def reset() -> None:
    """Force re-detection on next get_model() call. Useful for tests."""
    global _model, _model_name
    _model = None
    _model_name = ""