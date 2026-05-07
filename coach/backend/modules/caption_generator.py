# -*- coding: utf-8 -*-
"""Caption Generator — uses shared gemini_client (auto-detected model)."""

import os
import json
import re
from typing import Dict
from modules.gemini_client import get_model

FALLBACKS: Dict[str, Dict] = {
    "Music Performance": {
        "scroll_stopping": "The riff that's been stuck in my head all week 🎸",
        "viral_one_liner":  "When the chord progression just hits different.",
        "question":         "Which part of this would you loop on repeat?",
        "story":            "Started this one at midnight and couldn't put the guitar down. Some songs write themselves.",
    },
    "Sports": {
        "scroll_stopping": "Training session caught on camera 🔥",
        "viral_one_liner":  "The grind never stops.",
        "question":         "How many hours a day do you train?",
        "story":            "Every rep, every session — this is what it takes.",
    },
    "Fitness": {
        "scroll_stopping": "Form check ✅ Full reps, no ego 💪",
        "viral_one_liner":  "Consistency > intensity. Every single time.",
        "question":         "How many sets are you hitting today?",
        "story":            "Started from zero. This is what 6 months of showing up looks like.",
    },
    "Tech Review": {
        "scroll_stopping": "Honest review — no sponsor, no filter 📱",
        "viral_one_liner":  "Is this actually worth it? Watch till the end.",
        "question":         "Would you spend your money on this?",
        "story":            "I tested this for 2 weeks so you don't have to make the wrong call.",
    },
    "Dance": {
        "scroll_stopping": "New choreo just dropped 🕺",
        "viral_one_liner":  "The transition at 0:08 tho.",
        "question":         "Can you nail that first 8-count?",
        "story":            "Choreographed this in one night. The body remembers what the mind forgets.",
    },
    "Food & Cooking": {
        "scroll_stopping": "Made this in 15 minutes and it slaps 🍳",
        "viral_one_liner":  "Recipe so easy it feels illegal.",
        "question":         "Would you try this tonight?",
        "story":            "My mum taught me this recipe and I've been making it every week since.",
    },
    "Tutorial": {
        "scroll_stopping": "Save this — you'll need it later 💾",
        "viral_one_liner":  "Wish someone told me this earlier.",
        "question":         "Did you already know this trick?",
        "story":            "Took me 3 years to learn this. Watch and save yourself the time.",
    },
    "Travel": {
        "scroll_stopping": "This place doesn't look real 🌍",
        "viral_one_liner":  "Put this on your list immediately.",
        "question":         "Would you visit here?",
        "story":            "I almost didn't book this trip. Best decision I've ever made.",
    },
}
_DEFAULT = {
    "scroll_stopping": "Dropping this before the weekend 🔥",
    "viral_one_liner":  "This one's for the feed.",
    "question":         "What do you think of this?",
    "story":            "Been working on this for a while. Here it is.",
}


class CaptionGenerator:

    def __init__(self):
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def generate(
        self,
        video_description: str,
        content_category: str,
        primary_activity: str = "",
    ) -> Dict[str, str]:

        if not self._api_key:
            return FALLBACKS.get(content_category, _DEFAULT)
        if not video_description or "unavailable" in video_description.lower():
            return FALLBACKS.get(content_category, _DEFAULT)

        act = f"Primary activity: {primary_activity}" if primary_activity and primary_activity != "Content creation" else ""

        prompt = f"""You are writing Instagram Reel / TikTok captions for a {content_category} video.

VIDEO CONTENT:
{act}
Description: {video_description}

Write 4 captions — each must be directly about THIS specific video. No generic filler.

1. SCROLL_STOPPING: Makes people stop scrolling. 1-2 sentences + 1-2 relevant emojis.
2. VIRAL_ONE_LINER: Single punchy sentence under 10 words. Maximum impact.
3. QUESTION: 1 sentence ending with a genuine question to drive comments.
4. STORY: 2-3 sentences in first person with context or backstory about this content.

Rules:
- Reference the actual activity from the description
- No hashtags (added separately)
- No "excited to share" or "hope you enjoy"
- Sound like a real creator, not a marketing bot

Return ONLY valid JSON (no markdown fences):
{{"scroll_stopping":"...","viral_one_liner":"...","question":"...","story":"..."}}"""

        try:
            model = get_model()
            resp = model.generate_content(prompt)
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.text.strip())
            data = json.loads(text)
            return {k: data.get(k, "") for k in ["scroll_stopping","viral_one_liner","question","story"]}
        except Exception:
            return FALLBACKS.get(content_category, _DEFAULT)