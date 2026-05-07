# -*- coding: utf-8 -*-
"""
Postlytics — niche-specific feedback via Gemini
────────────────────────────────────────────────────
Pipeline:
  1. Detect ALL technical issues from measured data (pure Python — no AI)
  2. Detect strengths from measured data
  3. Ask Gemini to WRITE feedback referencing ONLY those detected issues
  4. Gemini is a WRITER here — never an analyzer

Uses shared gemini_client so no hardcoded model names anywhere.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional

from modules.gemini_client import get_model, get_model_name

# ── Niche personas ────────────────────────────────────────────────────────────
NICHE = {
    "Music Performance": {
        "persona": "a professional music creator and audio engineer with 2M+ followers",
        "focus":   ["instrument visibility in frame", "audio clarity and mix quality",
                    "performance energy and eye contact", "room acoustics and background aesthetics",
                    "microphone placement", "lighting on performer and instrument"],
    },
    "Sports": {
        "persona": "a professional sports content creator and athlete",
        "focus":   ["athlete and action clearly visible", "full-body framing during key moments",
                    "camera angle showing technique", "motion clarity at peak action",
                    "background energy", "editing pace and highlight timing"],
    },
    "Fitness": {
        "persona": "an elite fitness creator and certified personal trainer",
        "focus":   ["exercise form clearly visible", "full-body framing throughout movement",
                    "camera angle showing correct technique", "lighting on the body",
                    "rep and set clarity", "motivational energy in delivery"],
    },
    "Tech Review": {
        "persona": "a top tech reviewer known for clear, honest product reviews",
        "focus":   ["product clearly centered and visible", "close-up shots of key features",
                    "text overlays for specs", "hands and product framing",
                    "clean uncluttered background", "audio clarity for voiceover"],
    },
    "Dance": {
        "persona": "a professional dancer and choreographer with viral reels",
        "focus":   ["full body visible in frame at all times", "music sync and beat timing",
                    "camera angle showing the full routine", "clean background",
                    "facial expression and energy", "cuts landing on the beat"],
    },
    "Gaming": {
        "persona": "a top gaming content creator and streamer",
        "focus":   ["screen content clearly visible", "facecam framing",
                    "commentary audio clarity", "highlight moment timing",
                    "energy and authentic reactions"],
    },
    "Tutorial": {
        "persona": "a viral educational creator who makes complex topics simple",
        "focus":   ["steps clearly visible and easy to follow", "text overlays for key points",
                    "hands and demonstration clearly framed", "audio clarity for instructions",
                    "pacing — not too fast, not too slow"],
    },
    "Food & Cooking": {
        "persona": "a professional food creator known for viral recipe reels",
        "focus":   ["food and ingredients clearly visible", "close-up shots of key steps",
                    "overhead or 45-degree camera angle", "lighting directly on the food",
                    "satisfying final plating shot"],
    },
    "Travel": {
        "persona": "a full-time travel creator",
        "focus":   ["scenery framing and composition", "color grading and vibrancy",
                    "movement and immersive energy", "natural lighting",
                    "location context shown clearly"],
    },
    "Beauty & Fashion": {
        "persona": "a professional beauty and fashion creator",
        "focus":   ["face lighting quality — no harsh shadows", "product clearly visible",
                    "full face/outfit in frame", "color accuracy and white balance",
                    "before/after or transformation structure"],
    },
    "Education": {
        "persona": "a viral education creator",
        "focus":   ["concept clarity", "visual aids or text overlays", "strong hook",
                    "clear takeaway at end", "audio clarity"],
    },
    "Comedy": {
        "persona": "a viral comedy creator who understands timing",
        "focus":   ["facial expression clearly visible", "punchline timing",
                    "audio clarity for dialogue", "scene variety", "energy"],
    },
    "Lifestyle": {
        "persona": "a top lifestyle creator",
        "focus":   ["aesthetic consistency", "story arc and narrative flow",
                    "visual variety", "color palette cohesion", "authentic moments"],
    },
}

DEFAULT_NICHE = {
    "persona": "a professional social media creator",
    "focus":   ["visual quality", "hook strength", "audio quality", "framing"],
}


class CreatorCoachModule:

    def __init__(self):
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def generate_feedback(
        self,
        content_category: str,
        video_description: str,
        primary_activity: str,
        visual_metrics: Dict,
        hook_analysis: Dict,
        audio_metrics: Dict,
        detected_objects: List[str] = None,
    ) -> Dict[str, Any]:

        niche   = NICHE.get(content_category, DEFAULT_NICHE)
        is_music = content_category in ("Music Performance", "Dance")

        issues    = self._issues(visual_metrics, hook_analysis, audio_metrics, is_music)
        strengths = self._strengths(visual_metrics, hook_analysis, audio_metrics)
        score     = self._score(visual_metrics, hook_analysis, audio_metrics)

        feedback = self._write(
            niche, content_category, primary_activity,
            video_description, issues, strengths, detected_objects or [],
        )

        if feedback:
            return {
                "creator_persona":       niche["persona"],
                "what_works_well":       feedback.get("what_works_well", strengths),
                "what_needs_improvement":feedback.get("what_needs_improvement", []),
                "overall_score":         score,
                "overall_summary":       feedback.get("overall_summary", f"Score: {score}/10"),
            }
        return self._direct(niche["persona"], issues, strengths, score)

    # ── Gemini writes the coaching text ──────────────────────────────────────
    def _write(
        self,
        niche: Dict, category: str, activity: str,
        description: str, issues: List, strengths: List,
        objects: List[str],
    ) -> Optional[Dict]:

        if not self._api_key:
            return None

        issues_text = "\n".join(
            f"- [{i['category']}] {i['problem']} | Fix: {i['fix']} | Priority: {i['priority']}"
            for i in issues
        ) or "- No major technical issues detected"

        prompt = f"""You are {niche['persona']} reviewing a {category} reel.

VIDEO CONTENT:
Activity: {activity}
Description: {description}
Visible objects: {', '.join(objects[:10]) if objects else 'not available'}

MEASURED TECHNICAL ISSUES (from OpenCV + Librosa — reference only these):
{issues_text}

MEASURED STRENGTHS:
{chr(10).join(f'- {s}' for s in strengths)}

NICHE FOCUS AREAS FOR {category.upper()}:
{chr(10).join(f'- {f}' for f in niche['focus'])}

Write specific, actionable creator feedback. Rules:
- ONLY reference issues listed above — do not invent other problems
- Write like an experienced creator giving honest advice to a friend
- Make every suggestion specific to {category} and the activity ({activity})
- Never suggest "record in a quiet room" for music or dance content
- 2-3 sentences per improvement point

Respond ONLY with valid JSON (no markdown, no code fences):
{{
  "what_works_well": ["strength 1", "strength 2", "strength 3"],
  "what_needs_improvement": [
    {{"category": "name", "feedback": "2-3 sentence advice", "priority": "high|medium|low"}}
  ],
  "overall_summary": "2 honest sentences about this reel and its main opportunity"
}}"""

        try:
            model = get_model()
            response = model.generate_content(prompt)
            text = response.text.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            return json.loads(text)
        except Exception:
            return None

    # ── Pure-Python issue detection ───────────────────────────────────────────
    def _issues(self, v: Dict, h: Dict, a: Dict, is_music: bool) -> List[Dict]:
        out = []

        b = v.get("brightness_score", 50)
        if b > 78:
            out.append({"category":"Lighting","priority":"high",
                "problem":"Video is overexposed — highlights blown out",
                "fix":"Reduce exposure or move away from direct light"})
        elif b < 28:
            out.append({"category":"Lighting","priority":"high",
                "problem":"Video is too dark — subject is hard to see",
                "fix":"Add a ring light, move near a window, or boost ISO"})

        if v.get("contrast_score", 50) < 20:
            out.append({"category":"Visual Quality","priority":"medium",
                "problem":"Very low contrast — image looks flat",
                "fix":"Increase contrast in your editing app"})

        if v.get("noise_level", 0) > 60:
            out.append({"category":"Video Quality","priority":"medium",
                "problem":"Heavy grain/noise — filmed in low light",
                "fix":"Film in brighter conditions or apply noise reduction"})

        sl = v.get("stability_label","stable")
        if sl == "shaky":
            out.append({"category":"Stability","priority":"high",
                "problem":"Significant camera shake throughout",
                "fix":"Use a tripod, gimbal, or prop your phone"})
        elif sl == "minor_shake":
            out.append({"category":"Stability","priority":"medium",
                "problem":"Minor camera shake visible",
                "fix":"Use a tripod or enable OIS in camera settings"})

        fl = v.get("framing_label","good")
        if fl == "subject_too_small":
            out.append({"category":"Framing","priority":"high",
                "problem":"Subject too small in frame",
                "fix":"Move closer to camera or zoom in"})
        elif fl == "subject_off_center":
            out.append({"category":"Framing","priority":"medium",
                "problem":"Subject is not centered",
                "fix":"Reposition so subject fills the center third"})

        hs = h.get("hook_score", 5)
        if hs < 4:
            out.append({"category":"Hook","priority":"high",
                "problem":"Very weak opening — viewers swipe away in first 2 seconds",
                "fix":"Start with your best moment or a close-up jump cut"})
        elif hs < 6.5:
            out.append({"category":"Hook","priority":"medium",
                "problem":"Opening lacks a strong visual hook",
                "fix":"Show the most exciting part in the first second"})

        if a.get("clipping_detected"):
            out.append({"category":"Audio","priority":"high",
                "problem":"Audio is clipping — harsh digital distortion",
                "fix":"Lower recording gain by 20-30%"})

        if a.get("volume_label") == "too_quiet":
            rms = a.get("rms_loudness", -30)
            out.append({"category":"Audio","priority":"high",
                "problem":"Audio too quiet — hard to hear on phone speakers",
                "fix":f"Boost audio by {min(int(-20-rms),15)} dB in editing"})

        if a.get("noise_label") == "noisy" and not is_music:
            out.append({"category":"Audio","priority":"medium",
                "problem":"Background noise competes with speech",
                "fix":"Record in a quieter space or use a lapel mic"})

        if a.get("silence_percentage", 0) > 40:
            out.append({"category":"Pacing","priority":"medium",
                "problem":"Too many silent gaps slow down the pacing",
                "fix":"Cut dead air between sentences in editing"})

        if a.get("audio_type") == "none":
            out.append({"category":"Audio","priority":"high",
                "problem":"No audio detected — silent videos perform poorly",
                "fix":"Add voiceover, background music, or ambient sound"})

        return out

    def _strengths(self, v: Dict, h: Dict, a: Dict) -> List[str]:
        out = []
        b = v.get("brightness_score", 50)
        if 35 <= b <= 72:
            out.append(f"Lighting is well-balanced ({b:.0f}/100) — exposure looks good on mobile")
        if v.get("stability_score", 0) >= 80:
            out.append(f"Camera is stable ({v['stability_score']:.0f}/100) — smooth footage looks professional")
        if v.get("contrast_score", 0) >= 40:
            out.append(f"Good visual contrast ({v['contrast_score']:.0f}/100) — subject stands out clearly")
        hs = h.get("hook_score", 0)
        if hs >= 7:
            out.append(f"Strong hook ({hs}/10) — opening 3 seconds are visually engaging")
        if a.get("volume_label") == "good" and a.get("audio_type") != "none":
            out.append("Audio volume is well-balanced — comes through clearly on all devices")
        if not out:
            out.append("The video has solid foundations — apply the improvements below for maximum reach")
        return out[:4]

    def _score(self, v: Dict, h: Dict, a: Dict) -> float:
        s = 10.0
        b = v.get("brightness_score", 50)
        if b > 78 or b < 28:   s -= 1.2
        elif b > 72 or b < 33: s -= 0.5
        if v.get("contrast_score", 50) < 20:    s -= 0.7
        if v.get("noise_level", 0) > 60:        s -= 1.0
        elif v.get("noise_level", 0) > 35:      s -= 0.4
        sl = v.get("stability_label","stable")
        if sl == "shaky":       s -= 1.5
        elif sl == "minor_shake": s -= 0.6
        fl = v.get("framing_label","good")
        if fl == "subject_too_small":    s -= 1.0
        elif fl == "subject_off_center": s -= 0.6
        hs = h.get("hook_score", 5.0)
        if hs < 4:      s -= 2.0
        elif hs < 6.5:  s -= 1.0
        elif hs < 7.5:  s -= 0.3
        if not h.get("subject_visible", True): s -= 0.5
        if a.get("clipping_detected"):           s -= 1.2
        if a.get("volume_label") == "too_quiet": s -= 1.0
        if a.get("noise_label") == "noisy":      s -= 0.5
        if a.get("audio_type") == "none":        s -= 0.8
        if a.get("silence_percentage", 0) > 35:  s -= 0.4
        return round(max(0.0, min(10.0, s)), 1)

    def _direct(self, persona, issues, strengths, score) -> Dict:
        return {
            "creator_persona": persona,
            "what_works_well": strengths,
            "what_needs_improvement": [
                {"category": i["category"], "feedback": f"{i['problem']}. {i['fix']}",
                 "priority": i["priority"]}
                for i in issues
            ],
            "overall_score": score,
            "overall_summary": (
                f"This reel scores {score}/10. "
                + ("Fix the high-priority items first." if score < 7
                   else "Strong foundation — polish with the improvements above.")
            ),
        }