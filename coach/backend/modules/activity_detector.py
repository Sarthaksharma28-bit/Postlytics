# -*- coding: utf-8 -*-
"""
Activity Detection Module  — v3 (Podcast / Interview fix)
─────────────────────────────────────────────────────────────────────────────
Fuses Gemini description + primary_activity + YOLO objects → category.

FIXES IN v3 (on top of v2):
────────────────────────────
Bug A  "microphone" was hardwired to Music Performance in OBJECT_OVERRIDES.
       Microphones are shared objects used in podcasts, interviews, lectures,
       speeches, and news reporting — not only singing.
       Fix: microphone moved to AMBIGUOUS_OBJECTS. Phase 1 now skips
       ambiguous objects and lets Phase 2 keyword scoring decide context.

Bug B  "Podcast / Interview" category was completely absent from KEYWORD_MAP.
       Fix: full Podcast keyword set added (primary + secondary, 30+ terms).

Bug C  "Podcast / Interview" was absent from ACTIVITY_RULES.
       Fix: Podcast rule added at priority 1 (equal to Music) so rule fusion
       also handles it when keyword scoring is borderline.

Bug D  Phase 1 YOLO override was context-blind — fired on "microphone" before
       reading the description, overriding correct context.
       Fix: AMBIGUOUS_OBJECTS set — objects that mean different things in
       different contexts are excluded from Phase 1 and resolved in Phase 2.

Bug E  OBJECT_ALIASES mapped "mic stand", "lapel mic", "microphone stand" all
       to "microphone", feeding them into the wrong Music override.
       Fix: podcast-context mic aliases removed; only "singing mic" kept as
       a Music-specific alias.

UNCHANGED from v2:
──────────────────
- YOLO override still fires first for unambiguous objects (guitar, barbell,
  sports ball, etc.) that have only one meaning.
- Pipeline call signature is identical — no changes to app.py required.
- Gemini Vision code is untouched.
"""

from typing import Dict, Any, List, Optional, Tuple


# =============================================================================
# AMBIGUOUS OBJECTS  (Bug D fix)
# These objects appear in multiple categories and must NOT trigger a Phase 1
# override — context from the description must decide their category.
# =============================================================================

AMBIGUOUS_OBJECTS = {
    "microphone",    # podcast/interview/lecture AND singing
    "camera",        # vlogging/travel/tutorial AND photography review
    "chair",         # literally everywhere
    "table",         # everywhere
    "book",          # tutorial, education, lifestyle
    "laptop",        # tech review, gaming, tutorial, work vlog
    "phone",         # tech review, lifestyle, social media content
}


# =============================================================================
# OBJECT OVERRIDES
# ONLY unambiguous physical objects that have exactly ONE content meaning.
# Ambiguous objects (microphone, camera, laptop) are excluded here — they
# are handled by keyword scoring with description context.
# =============================================================================

OBJECT_OVERRIDES = {
    # Sports equipment — completely unambiguous
    "sports ball":    ("Sports",           "Sports / athletic activity"),
    "basketball":     ("Sports",           "Playing basketball"),
    "football":       ("Sports",           "Playing football / soccer"),
    "tennis racket":  ("Sports",           "Playing tennis"),
    "frisbee":        ("Sports",           "Sports / athletic activity"),
    "baseball bat":   ("Sports",           "Playing cricket / baseball"),
    "skateboard":     ("Sports",           "Skateboarding"),
    "bicycle":        ("Sports",           "Cycling"),
    "surfboard":      ("Sports",           "Surfing"),
    "skis":           ("Sports",           "Skiing"),
    "snowboard":      ("Sports",           "Snowboarding"),
    "boxing glove":   ("Sports",           "Boxing / martial arts"),

    # Music instruments — unambiguous (instruments only, NOT microphone)
    "guitar":         ("Music Performance","Playing guitar"),
    "violin":         ("Music Performance","Playing violin"),
    "cello":          ("Music Performance","Playing cello"),
    "piano":          ("Music Performance","Playing piano"),
    "drums":          ("Music Performance","Playing drums"),
    "saxophone":      ("Music Performance","Playing saxophone"),
    "trumpet":        ("Music Performance","Playing trumpet"),
    "ukulele":        ("Music Performance","Playing ukulele"),
    "banjo":          ("Music Performance","Playing banjo"),
    "flute":          ("Music Performance","Playing flute"),
    "amplifier":      ("Music Performance","Music performance"),
    # NOTE: "microphone" intentionally removed — it is in AMBIGUOUS_OBJECTS

    # Fitness equipment — unambiguous
    "barbell":        ("Fitness",          "Weight training"),
    "dumbbell":       ("Fitness",          "Weight training"),
    "yoga mat":       ("Fitness",          "Yoga / stretching"),
    "treadmill":      ("Fitness",          "Cardio / running"),
    "punching bag":   ("Fitness",          "Boxing / martial arts training"),
    "resistance band":("Fitness",          "Resistance training"),
}


# =============================================================================
# MULTI-WORD OBJECT ALIASES  (Bug E fix)
# Only map aliases that are genuinely unambiguous.
# Podcast-context mic aliases removed; only instrument-specific ones kept.
# =============================================================================

OBJECT_ALIASES = {
    # Guitar variants -> guitar (all unambiguously musical)
    "acoustic guitar":   "guitar",
    "electric guitar":   "guitar",
    "classical guitar":  "guitar",
    "bass guitar":       "guitar",
    "guitar pick":       "guitar",
    "guitar strings":    "guitar",
    "guitar fretboard":  "guitar",
    "music stand":       "guitar",   # strong contextual signal for music

    # Drum variants -> drums
    "drum kit":          "drums",
    "drum set":          "drums",
    "snare drum":        "drums",
    "bass drum":         "drums",
    "drum sticks":       "drums",

    # Keyboard variants -> keyboard (will hit Music only if context supports)
    "grand piano":       "piano",
    "upright piano":     "piano",
    "electric keyboard": "keyboard",
    "synthesizer":       "keyboard",

    # Amplifier variants
    "guitar amp":        "amplifier",

    # Microphone: ONLY singing-specific aliases kept (Bug E fix)
    # "mic stand" removed — podcasters also use mic stands
    # "microphone stand" removed — podcasters also use them
    # "lapel mic" removed — interview/lecture context
    "singing mic":       "microphone",   # phrasing implies performance context

    # Sports
    "tennis ball":       "sports ball",
    "soccer ball":       "sports ball",
    "boxing gloves":     "boxing glove",

    # Fitness
    "weight plates":     "barbell",
    "weight rack":       "barbell",
    "pull-up bar":       "barbell",
    "exercise mat":      "yoga mat",
    "gym mat":           "yoga mat",
}


def _normalize_objects(raw_objects: List[str]) -> List[str]:
    """
    Expand Gemini multi-word objects to canonical OBJECT_OVERRIDES keys.
    Filters out ambiguous objects so they don't fire Phase 1.
    """
    normalized = set()
    for obj in raw_objects:
        obj_lower = obj.strip().lower()

        # Skip ambiguous objects — they'll be handled by keyword scoring
        if obj_lower in AMBIGUOUS_OBJECTS:
            normalized.add(obj_lower)  # keep for Phase 2 obj_bonus but not Phase 1
            continue

        # Direct alias lookup
        if obj_lower in OBJECT_ALIASES:
            normalized.add(OBJECT_ALIASES[obj_lower])
            continue

        # Substring match: 'acoustic guitar strings' contains 'acoustic guitar'
        matched = False
        for alias, canonical in OBJECT_ALIASES.items():
            if alias in obj_lower:
                normalized.add(canonical)
                matched = True
        if not matched:
            normalized.add(obj_lower)

    return list(normalized)


# =============================================================================
# KEYWORD MAP  (Bug B fix — Podcast / Interview added; all categories expanded)
# primary   = weighted ×2 (strong, specific signal)
# secondary = weighted ×1 (supporting context)
# =============================================================================

KEYWORD_MAP: Dict[str, Dict[str, List[str]]] = {

    # ── Podcast / Interview  (Bug B: brand new category) ─────────────────────
    "Podcast / Interview": {
        "primary": [
            "podcast",
            "interview",
            "podcast session",
            "podcast episode",
            "podcast recording",
            "speaking into a microphone",
            "speaking into the microphone",
            "speaking directly into",
            "speaking to the microphone",
            "interview session",
            "interview format",
            "being interviewed",
            "discussing",
            "commentary",
            "host",
            "guest speaker",
            "talking head",
            "sit-down interview",
            "press conference",
            "news anchor",
            "journalist",
            "radio show",
            "talk show",
            "storytelling session",
        ],
        "secondary": [
            "speaking",
            "talking",
            "conversation",
            "dialogue",
            "monologue",
            "narration",
            "debate",
            "panel",
            "moderator",
            "presenter",
            "anchor",
            "reporter",
            "microphone",
            "mic",
            "studio",
            "desk",
            "headphones",
            "audio recording",
            "recording session",
            "direct to camera",
            "addressing the audience",
            "opinion",
            "analysis",
            "thoughts on",
        ],
    },

    # ── Music Performance ─────────────────────────────────────────────────────
    "Music Performance": {
        "primary": [
            "playing guitar",
            "playing piano",
            "playing drums",
            "playing violin",
            "playing bass",
            "playing keyboard",
            "playing saxophone",
            "playing trumpet",
            "playing ukulele",
            "playing acoustic guitar",
            "playing electric guitar",
            "strumming guitar",
            "strumming",
            "fretboard",
            "chord progression",
            "music performance",
            "live performance",
            "concert performance",
            "singing",
            "vocalist",
            "vocals",
            "performing music",
            "musician",
            "live music",
            "singing into a microphone",  # phrase — distinguishes from podcast
            "singing into the microphone",
            "performing on stage",
            "band performance",
        ],
        "secondary": [
            "guitar",
            "acoustic",
            "piano",
            "drums",
            "violin",
            "saxophone",
            "trumpet",
            "keyboard",
            "bass",
            "ukulele",
            "banjo",
            "flute",
            "amplifier",
            "instrument",
            "melody",
            "chord",
            "strum",
            "riff",
            "solo",
            "band",
            "ensemble",
            "stage",
            "music studio",
            "concert",
            "gig",
            "rehearsal",
            "rhythm",
            "beat",
            "song",
            "lyrics",
            "singer",
            "performer",
            "composer",
            "bassist",
        ],
    },

    # ── Fitness ───────────────────────────────────────────────────────────────
    "Fitness": {
        "primary": [
            "workout",
            "exercise routine",
            "fitness routine",
            "training session",
            "push-up",
            "pushup",
            "pull-up",
            "deadlift",
            "squat",
            "bench press",
            "bicep curl",
            "shoulder press",
            "lunges",
            "burpee",
            "plank",
            "weight lifting",
            "weight training",
            "strength training",
            "cardio workout",
            "hiit",
            "circuit training",
        ],
        "secondary": [
            "exercise",
            "gym",
            "fitness",
            "yoga",
            "stretching",
            "lifting",
            "dumbbell",
            "barbell",
            "weights",
            "rep",
            "sets",
            "muscle",
            "abs",
            "core",
            "glutes",
            "biceps",
            "trainer",
            "training",
            "sweat",
            "treadmill",
            "running",
            "jogging",
            "sprint",
        ],
    },

    # ── Education / Tutorial ──────────────────────────────────────────────────
    "Tutorial": {
        "primary": [
            "how to",
            "step by step",
            "tutorial",
            "teaching",
            "explaining how",
            "let me show you",
            "beginner guide",
            "complete guide",
            "in this video i will show",
            "follow these steps",
        ],
        "secondary": [
            "teach",
            "explain",
            "tips",
            "trick",
            "learn",
            "lesson",
            "demonstration",
            "walkthrough",
            "guide",
            "instructions",
            "showing",
            "process",
            "method",
            "technique",
            "steps",
        ],
    },

    "Education": {
        "primary": [
            "explaining",
            "educational",
            "learning about",
            "did you know",
            "science of",
            "history of",
            "facts about",
            "understanding",
            "lecture",
            "classroom",
        ],
        "secondary": [
            "knowledge",
            "information",
            "fact",
            "science",
            "history",
            "learn",
            "study",
            "concept",
            "theory",
            "research",
            "professor",
            "student",
        ],
    },

    # ── Sports ────────────────────────────────────────────────────────────────
    "Sports": {
        "primary": [
            "playing basketball",
            "playing football",
            "playing soccer",
            "playing tennis",
            "playing cricket",
            "playing badminton",
            "dribbling",
            "dunking",
            "shooting hoops",
            "scoring a goal",
            "serving",
            "batting",
            "bowling",
            "throwing",
            "catching",
            "skateboarding",
            "surfing",
            "skiing",
            "snowboarding",
        ],
        "secondary": [
            "sport",
            "athlete",
            "match",
            "game",
            "tournament",
            "competition",
            "court",
            "pitch",
            "field",
            "stadium",
            "team",
            "player",
            "goal",
            "score",
            "basketball",
            "football",
            "soccer",
            "cricket",
            "tennis",
            "badminton",
            "volleyball",
        ],
    },

    # ── Dance ─────────────────────────────────────────────────────────────────
    "Dance": {
        "primary": [
            "dancing",
            "choreography",
            "dance routine",
            "dance performance",
            "breakdancing",
            "hip hop dance",
            "ballet",
            "contemporary dance",
            "salsa",
            "tango",
            "freestyle dance",
            "dance moves",
        ],
        "secondary": [
            "danc",
            "choreograph",
            "groove",
            "twerk",
            "shuffle",
            "pirouette",
            "spin",
            "dancer",
            "hip hop",
            "footwork",
            "body movement",
        ],
    },

    # ── Comedy ────────────────────────────────────────────────────────────────
    "Comedy": {
        "primary": [
            "comedy skit",
            "funny video",
            "prank video",
            "joke telling",
            "stand up comedy",
            "sketch comedy",
            "comedic",
        ],
        "secondary": [
            "comedy",
            "funny",
            "joke",
            "prank",
            "hilarious",
            "skit",
            "laugh",
            "humor",
            "reaction",
            "parody",
        ],
    },

    # ── Tech Review ───────────────────────────────────────────────────────────
    "Tech Review": {
        "primary": [
            "reviewing",
            "unboxing",
            "tech review",
            "product review",
            "iphone review",
            "android review",
            "laptop review",
            "first look",
            "hands on",
            "testing the",
        ],
        "secondary": [
            "review",
            "unbox",
            "iphone",
            "android",
            "samsung",
            "apple",
            "macbook",
            "laptop",
            "gadget",
            "tech",
            "device",
            "specs",
            "features",
            "camera quality",
            "battery life",
            "phone",
            "tablet",
            "smartwatch",
            "earbuds",
        ],
    },

    # ── Gaming ────────────────────────────────────────────────────────────────
    "Gaming": {
        "primary": [
            "playing video game",
            "gameplay",
            "game stream",
            "first person shooter",
            "battle royale",
            "rpg gameplay",
        ],
        "secondary": [
            "gaming",
            "game",
            "stream",
            "console",
            "controller",
            "fps",
            "multiplayer",
            "esports",
            "minecraft",
            "fortnite",
            "valorant",
            "fifa",
            "cod",
            "gta",
        ],
    },

    # ── Food & Cooking ────────────────────────────────────────────────────────
    "Food & Cooking": {
        "primary": [
            "cooking",
            "baking",
            "recipe",
            "preparing food",
            "making pasta",
            "chopping",
            "stirring",
            "frying",
            "sauteing",
            "grilling",
            "food preparation",
            "meal prep",
        ],
        "secondary": [
            "cook",
            "bake",
            "food",
            "dish",
            "ingredient",
            "kitchen",
            "chop",
            "stir",
            "fry",
            "boil",
            "grill",
            "roast",
            "flavour",
            "taste",
            "restaurant",
            "plate",
            "chef",
        ],
    },

    # ── Travel ────────────────────────────────────────────────────────────────
    "Travel": {
        "primary": [
            "travel vlog",
            "visiting",
            "exploring",
            "travel to",
            "road trip",
            "backpacking",
            "travel diary",
        ],
        "secondary": [
            "travel",
            "trip",
            "explore",
            "city",
            "beach",
            "mountain",
            "destination",
            "landmark",
            "sightseeing",
            "hotel",
            "airport",
            "adventure",
            "landscape",
            "country",
            "culture",
        ],
    },

    # ── Beauty & Fashion ──────────────────────────────────────────────────────
    "Beauty & Fashion": {
        "primary": [
            "makeup tutorial",
            "skincare routine",
            "fashion haul",
            "ootd",
            "outfit of the day",
            "get ready with me",
            "grwm",
        ],
        "secondary": [
            "makeup",
            "foundation",
            "lipstick",
            "eyeliner",
            "beauty",
            "skincare",
            "fashion",
            "style",
            "outfit",
            "clothing",
            "haul",
            "aesthetic",
            "glam",
            "contour",
            "blush",
        ],
    },

    # ── Lifestyle ─────────────────────────────────────────────────────────────
    "Lifestyle": {
        "primary": [
            "day in my life",
            "morning routine",
            "night routine",
            "vlog",
        ],
        "secondary": [
            "lifestyle",
            "routine",
            "daily",
            "life",
            "personal",
        ],
    },
}


# =============================================================================
# Category -> relevant objects for bonus scoring in Phase 2
# =============================================================================

_CATEGORY_OBJECTS: Dict[str, List[str]] = {
    "Music Performance":  ["guitar", "piano", "drums", "violin", "saxophone",
                           "trumpet", "amplifier", "ukulele", "banjo"],
    "Podcast / Interview":["microphone"],   # microphone boosts Podcast score
    "Fitness":            ["barbell", "dumbbell", "yoga mat", "treadmill", "punching bag"],
    "Sports":             ["sports ball", "basketball", "tennis racket", "frisbee",
                           "skateboard", "bicycle", "surfboard"],
    "Tech Review":        ["laptop", "cell phone", "tablet", "camera", "monitor"],
    "Gaming":             ["monitor", "keyboard", "mouse", "remote", "tv"],
    "Food & Cooking":     ["bowl", "fork", "knife", "spoon", "dining table"],
}


# =============================================================================
# ACTIVITY RULES (Phase 3 — rule-based fusion, deeper fallback)
# Bug C fix: Podcast rule added at priority 1
# =============================================================================

ACTIVITY_RULES = [
    # Podcast / Interview — priority 1, equal to Music (Bug C fix)
    (1, "Podcast / Interview", "Podcast / interview recording",
     {"objects": ["microphone"],
      "desc": ["podcast", "interview", "speaking into", "speaking directly",
               "discussing", "commentary", "host", "guest", "talk show",
               "radio show", "monologue", "narration", "press conference"]}),

    # Music — requires instrument object OR strong description evidence
    (1, "Music Performance", "Playing guitar",
     {"objects": ["guitar", "amplifier"],
      "desc": ["guitar", "strum", "chord", "acoustic", "fretboard"]}),
    (1, "Music Performance", "Playing piano",
     {"objects": ["piano", "keyboard"],
      "desc": ["piano", "keyboard", "playing piano", "keys"]}),
    (1, "Music Performance", "Playing drums",
     {"objects": ["drums"],
      "desc": ["drums", "drumming", "percussion", "drum kit"]}),
    (1, "Music Performance", "Singing",
     {"objects": [],
      "desc": ["singing into", "singing on stage", "vocalist", "vocal performance"]}),
    (1, "Music Performance", "Instrumental performance",
     {"objects": ["guitar", "piano", "drums", "violin", "saxophone",
                  "trumpet", "amplifier", "ukulele"],
      "desc": ["playing guitar", "playing piano", "playing drums", "playing violin",
               "performing music", "music performance", "musician", "instrument",
               "acoustic guitar", "electric guitar", "strumming", "fretboard",
               "chord", "melody", "riff", "concert", "band", "vocalist"]}),

    # Dance
    (2, "Dance", "Dancing",
     {"objects": [],
      "desc": ["danc", "choreograph", "breakdanc", "hip hop move", "twerk", "shuffle"]}),

    # Fitness
    (3, "Fitness", "Weight training",
     {"objects": ["barbell", "dumbbell"],
      "desc": ["deadlift", "squat", "bench press", "curl", "weight", "rep"]}),
    (3, "Fitness", "Yoga",
     {"objects": ["yoga mat"],
      "desc": ["yoga", "stretch", "pose", "asana", "flexibility"]}),
    (3, "Fitness", "Workout",
     {"objects": ["yoga mat", "barbell", "dumbbell", "treadmill", "punching bag"],
      "desc": ["workout", "exercise", "fitness", "gym", "training", "push-up", "plank",
               "squat", "deadlift", "burpee", "hiit", "strength training"]}),

    # Sports
    (4, "Sports", "Playing basketball",
     {"objects": ["basketball", "sports ball"],
      "desc": ["basketball", "dribble", "dunk", "hoop"]}),
    (4, "Sports", "Playing football / soccer",
     {"objects": ["sports ball", "football"],
      "desc": ["football", "soccer", "kick", "goal"]}),
    (4, "Sports", "Playing tennis",
     {"objects": ["tennis racket"],
      "desc": ["tennis", "racket", "serve", "court"]}),
    (4, "Sports", "Sports / athletic activity",
     {"objects": ["sports ball", "basketball", "tennis racket", "frisbee",
                  "skateboard", "bicycle", "surfboard", "skis", "snowboard"],
      "desc": ["sport", "athlete", "match", "game", "tournament", "competition"]}),

    # Tech
    (5, "Tech Review", "Tech review / unboxing",
     {"objects": ["laptop", "cell phone", "tablet", "camera", "monitor"],
      "desc": ["review", "unbox", "iphone", "android", "samsung", "apple",
               "laptop", "gadget", "tech", "device", "specs"]}),

    # Gaming
    (6, "Gaming", "Playing video games",
     {"objects": ["tv", "monitor", "keyboard", "mouse", "remote"],
      "desc": ["gaming", "gameplay", "game", "stream", "console", "controller"]}),

    # Food
    (7, "Food & Cooking", "Cooking",
     {"objects": ["bowl", "fork", "knife", "spoon", "dining table"],
      "desc": ["cook", "recipe", "chop", "bake", "stir", "fry", "ingredient", "food"]}),

    # Beauty
    (8, "Beauty & Fashion", "Makeup / beauty",
     {"objects": [],
      "desc": ["makeup", "foundation", "lipstick", "eyeliner", "beauty", "skincare"]}),
    (8, "Beauty & Fashion", "Fashion",
     {"objects": [],
      "desc": ["outfit", "fashion", "style", "haul", "ootd", "clothing"]}),

    # Tutorial
    (9, "Tutorial", "Tutorial",
     {"objects": ["laptop", "book"],
      "desc": ["how to", "tutorial", "step by step", "teach", "explain", "tips"]}),

    # Comedy
    (10, "Comedy", "Comedy / skit",
     {"objects": [],
      "desc": ["comedy", "funny", "joke", "skit", "prank", "hilarious"]}),

    # Travel
    (11, "Travel", "Travel",
     {"objects": ["suitcase", "backpack"],
      "desc": ["travel", "trip", "explore", "city", "beach", "mountain", "destination"]}),
]


# =============================================================================
# MAIN CLASSIFIER
# =============================================================================

class ActivityDetector:

    def detect(
        self,
        gemini_description: str,
        gemini_primary_activity: str,
        yolo_objects: List[str],
        yolo_confidence: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Determine activity and category from all available signals.
        Call signature unchanged — no changes to app.py required.

        Pipeline:
          Phase 1: Unambiguous YOLO object override (guitar -> Music, etc.)
          Phase 2: Weighted keyword scoring against description + activity
          Phase 3: Rule-based fusion fallback
          Phase 4: Safe fallback -> Lifestyle
        """
        # Normalise objects (multi-word aliases + ambiguous filtering)
        norm_objects = _normalize_objects(list(yolo_objects))
        obj_set      = set(norm_objects)

        # Prepend primary_activity so it contributes to all text scoring
        combined_text = " ".join(filter(None, [
            gemini_primary_activity,
            gemini_description,
        ])).strip()
        desc_lower = combined_text.lower()

        # ── PHASE 1: Unambiguous YOLO object override ─────────────────────────
        # Only fires for objects that have exactly ONE content meaning.
        # Ambiguous objects (microphone, camera, laptop) are excluded.
        phase1 = self._phase1_yolo(obj_set, yolo_confidence)
        if phase1:
            return phase1

        # ── PHASE 2: Weighted keyword scoring ────────────────────────────────
        phase2 = self._phase2_keywords(desc_lower, obj_set, gemini_primary_activity)
        if phase2:
            return phase2

        # ── PHASE 3: Rule-based fusion fallback ──────────────────────────────
        phase3 = self._phase3_rules(desc_lower, obj_set, gemini_primary_activity)
        if phase3:
            return phase3

        # ── PHASE 4: Safe fallback ────────────────────────────────────────────
        return {
            "primary_activity": gemini_primary_activity or "Content creation",
            "category":         "Lifestyle",
            "confidence":       "low",
            "evidence":         [],
            "matched_objects":  list(obj_set),
            "detection_method": "fallback",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1 — Unambiguous object override
    # ─────────────────────────────────────────────────────────────────────────

    def _phase1_yolo(
        self,
        obj_set: set,
        yolo_confidence: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        """
        Fires ONLY for objects in OBJECT_OVERRIDES (ambiguous ones excluded).
        """
        yolo_category, yolo_activity, yolo_evidence = None, None, []

        for obj_name, (cat, act) in OBJECT_OVERRIDES.items():
            if obj_name in obj_set:
                if yolo_category is None:
                    yolo_category = cat
                    yolo_activity = act
                    yolo_evidence.append(obj_name)
                elif cat == yolo_category:
                    yolo_evidence.append(obj_name)

        if not (yolo_category and yolo_evidence):
            return None

        conf_val   = max((yolo_confidence.get(e, 0.5) for e in yolo_evidence), default=0.5)
        confidence = "high" if conf_val >= 0.5 else "medium"
        return {
            "primary_activity": yolo_activity,
            "category":         yolo_category,
            "confidence":       confidence,
            "evidence":         yolo_evidence,
            "matched_objects":  list(obj_set),
            "detection_method": "yolo_override",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 2 — Weighted keyword scoring
    # ─────────────────────────────────────────────────────────────────────────

    def _phase2_keywords(
        self,
        desc: str,
        obj_set: set,
        primary_activity: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Score every category by primary (×2) + secondary (×1) keyword hits
        plus an object presence bonus. Winner must clear minimum threshold.
        """
        scores: Dict[str, Dict] = {}

        for category, kw_groups in KEYWORD_MAP.items():
            primary_hits   = [kw for kw in kw_groups.get("primary",   []) if kw in desc]
            secondary_hits = [kw for kw in kw_groups.get("secondary", []) if kw in desc]
            weighted       = len(primary_hits) * 2 + len(secondary_hits)

            cat_objects = _CATEGORY_OBJECTS.get(category, [])
            obj_bonus   = 3 if any(o in obj_set for o in cat_objects) else 0
            total       = weighted + obj_bonus

            if total > 0:
                scores[category] = {
                    "total":    total,
                    "evidence": primary_hits[:4] + secondary_hits[:2],
                    "hits":     len(primary_hits) + len(secondary_hits),
                }

        if not scores:
            return None

        winner = max(scores, key=lambda c: scores[c]["total"])
        if scores[winner]["total"] < 2:
            return None

        d          = scores[winner]
        hits       = d["hits"]
        confidence = "high" if hits >= 4 else ("medium" if hits >= 2 else "low")
        activity   = (
            self._find_activity(winner, obj_set, desc)
            or primary_activity
            or winner
        )
        return {
            "primary_activity": activity,
            "category":         winner,
            "confidence":       confidence,
            "evidence":         d["evidence"],
            "matched_objects":  list(obj_set),
            "detection_method": "keyword_score",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 3 — Rule-based fusion (original ACTIVITY_RULES logic)
    # ─────────────────────────────────────────────────────────────────────────

    def _phase3_rules(
        self,
        desc: str,
        obj_set: set,
        primary_activity: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Scores ACTIVITY_RULES by object + description hit combination.
        Music no longer hard-gated on obj_hits (>=2 desc hits sufficient).
        """
        best_match    = None
        best_score    = 999.0
        best_evidence: List[str] = []

        for priority, category, activity, rules in ACTIVITY_RULES:
            obj_hits  = [o for o in rules["objects"] if o in obj_set]
            desc_hits = [kw for kw in rules["desc"] if kw in desc]

            if category in ("Music Performance", "Podcast / Interview"):
                # Both require obj evidence OR >=2 strong description hits
                if obj_hits:
                    score = priority - 0.5
                elif len(desc_hits) >= 2:
                    score = priority
                elif desc_hits:
                    score = priority + 0.5
                else:
                    continue
            elif category == "Sports":
                if obj_hits:
                    score = priority - 0.5
                elif len(desc_hits) >= 2:
                    score = priority + 0.1
                elif desc_hits:
                    score = priority + 0.3
                else:
                    continue
            else:
                if obj_hits and desc_hits:
                    score = priority - 0.5
                elif obj_hits:
                    score = priority + 0.2
                elif len(desc_hits) >= 2:
                    score = priority + 0.1
                elif desc_hits:
                    score = priority + 0.3
                else:
                    continue

            if score < best_score:
                best_score    = score
                best_match    = (category, activity)
                best_evidence = obj_hits + desc_hits[:3]

        if not best_match:
            return None

        confidence = "high" if best_score < 3 else ("medium" if best_score < 6 else "low")
        return {
            "primary_activity": best_match[1],
            "category":         best_match[0],
            "confidence":       confidence,
            "evidence":         list(set(best_evidence)),
            "matched_objects":  list(obj_set),
            "detection_method": "rule_fusion",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _find_activity(self, category: str, obj_set: set, desc: str) -> str:
        """Find the most specific activity label for a category from ACTIVITY_RULES."""
        for _, cat, activity, rules in ACTIVITY_RULES:
            if cat != category:
                continue
            obj_hit  = any(o in obj_set for o in rules["objects"])
            desc_hit = any(kw in desc   for kw in rules["desc"])
            if obj_hit or desc_hit:
                return activity
        return ""