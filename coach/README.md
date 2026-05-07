# 🎬 Postlytics

**Professional AI-powered reel analysis for Instagram Reels, TikTok, and YouTube Shorts.**

Upload your video before posting. Get niche-specific feedback from an AI that thinks like a top creator in your space.

---

## Architecture Overview

```
ai-creator-coach/
├── backend/
│   ├── main.py                         # FastAPI app + analysis pipeline orchestration
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── api/
│   │   └── schemas.py                  # Pydantic response models
│   ├── modules/
│   │   ├── video_processor.py          # Frame extraction + visual quality analysis
│   │   ├── vision_analyzer.py          # LLaVA frame descriptions
│   │   ├── audio_analyzer.py           # Librosa audio feature extraction
│   │   ├── content_understanding.py    # Gemini: video description + category detection
│   │   ├── creator_coach.py            # Gemini: niche-aware coaching feedback
│   │   ├── caption_generator.py        # Gemini: 4 caption styles
│   │   ├── hashtag_generator.py        # Gemini: 25 optimized hashtags
│   │   └── thumbnail_selector.py       # OpenCV: best frame selection
│   └── utils/
│       └── file_manager.py             # Session directory management
└── frontend/
    └── index.html                      # Complete single-file UI
```

---

## Analysis Pipeline

```
Video Upload
     │
     ▼
┌─────────────────────────────────────────────┐
│  VideoProcessor                             │
│  • Extract 1 frame/sec (OpenCV)             │
│  • Extract audio (FFmpeg → WAV)             │
│  • Analyze visual quality metrics           │
│  • Analyze hook (first 3 frames)            │
└────────────────┬────────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌───────────────┐  ┌──────────────────────────┐
│ VisionAnalyzer│  │ AudioAnalyzer            │
│ LLaVA: frame  │  │ Librosa: RMS, tempo,     │
│ descriptions  │  │ spectral, noise, clipping│
└───────┬───────┘  └────────────┬─────────────┘
        │                       │
        ▼                       │
┌───────────────────────────────▼─────────────┐
│  ContentUnderstandingModule (Gemini)         │
│  • Synthesize frame descriptions             │
│  • Detect content category / niche           │
└────────────────────┬────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
┌─────────────┐ ┌──────────┐ ┌──────────────┐
│CreatorCoach │ │ Caption  │ │  Hashtag     │
│(Gemini)     │ │Generator │ │  Generator   │
│Niche-aware  │ │(Gemini)  │ │  (Gemini)    │
│feedback     │ │4 styles  │ │  25 tags     │
└─────────────┘ └──────────┘ └──────────────┘
        │
        ▼
┌───────────────────────────┐
│  ThumbnailSelector         │
│  OpenCV: score each frame  │
│  (sharpness, brightness,   │
│   contrast, subject)       │
└───────────────────────────┘
        │
        ▼
   JSON Response → Frontend
```

---

## Quick Start

### 1. Prerequisites

- Python 3.10+
- FFmpeg installed (`brew install ffmpeg` / `apt install ffmpeg`)
- Gemini API key (required)
- One of: Ollama + LLaVA (local) OR Replicate API token (cloud)

### 2. Backend Setup

```bash
cd backend

# Copy and configure env
cp .env.example .env
# Edit .env: add GEMINI_API_KEY

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Vision Backend — Choose One

**Option A: Ollama (local, free)**
```bash
# Install Ollama: https://ollama.ai
ollama run llava
# Set in .env: VISION_BACKEND=ollama
```

**Option B: Replicate (cloud)**
```bash
# Set in .env:
# VISION_BACKEND=replicate
# REPLICATE_API_TOKEN=your_token
```

**Option C: OpenAI GPT-4V**
```bash
# Set in .env:
# VISION_BACKEND=openai
# OPENAI_API_KEY=your_key
```

### 4. Frontend

Open `frontend/index.html` in a browser, or serve it:
```bash
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

### 5. Docker

```bash
cd backend
docker build -t creator-coach .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -e VISION_BACKEND=ollama \
  creator-coach
```

---

## API Reference

### `POST /api/analyze`

**Request:** `multipart/form-data` with `video` field (MP4, MOV, WebM, AVI)

**Response:**
```json
{
  "session_id": "uuid",
  "video_description": "A person sitting indoors playing an acoustic guitar...",
  "content_category": "Music Performance",
  "duration_seconds": 15.0,
  "visual_analysis": {
    "brightness_score": 62.3,
    "brightness_label": "good",
    "contrast_score": 45.1,
    "contrast_label": "good",
    "noise_level": 18.2,
    "noise_label": "clean",
    "stability_score": 88.5,
    "stability_label": "stable",
    "framing_label": "good",
    "motion_energy": 12.4
  },
  "hook_analysis": {
    "has_strong_hook": false,
    "motion_intensity": 8.2,
    "scene_change_detected": false,
    "subject_visible": true,
    "hook_score": 5.5,
    "hook_assessment": "Weak hook — the opening 3 seconds lack visual variety..."
  },
  "audio_analysis": {
    "audio_type": "music",
    "rms_loudness": -18.3,
    "volume_label": "good",
    "tempo_bpm": 92.0,
    "spectral_centroid": 2340.5,
    "noise_level": 12.1,
    "noise_label": "clean",
    "silence_percentage": 3.2,
    "clipping_detected": false,
    "issues": []
  },
  "coaching_feedback": {
    "creator_persona": "professional music creator...",
    "what_works_well": ["..."],
    "what_needs_improvement": [
      {
        "category": "Hook",
        "issue": "Weak hook — score 5.5/10",
        "feedback": "Your opening 3 seconds don't have a scene change...",
        "priority": "high"
      }
    ],
    "overall_score": 7.2,
    "overall_summary": "..."
  },
  "captions": {
    "engaging": "...",
    "question_based": "...",
    "viral_short": "...",
    "story_style": "..."
  },
  "hashtags": ["#music", "#guitarist", ...],
  "thumbnail": {
    "frame_index": 7,
    "timestamp_seconds": 7.0,
    "url": "/static/thumbnails/session-id_thumbnail.jpg",
    "reason": "Selected for: sharp and in focus, well-exposed lighting",
    "overlay_text_suggestion": "Add your name/handle in the top-left corner"
  }
}
```

---

## Content Categories

| Category | Creator Persona | Focus Areas |
|---|---|---|
| Music Performance | Music creator 2M+ | Instrument visibility, audio clarity, performance framing |
| Tech Review | Tech reviewer | Product visibility, feature demo, text overlays |
| Fitness | Elite fitness creator | Exercise form, camera angle, body framing |
| Gaming | Top gaming creator | Screen visibility, facecam, commentary |
| Comedy | Viral comedy creator | Timing, facial expressions, punchline framing |
| Tutorial | Educational creator | Step visibility, overlays, pacing |
| Travel | Full-time travel creator | Scenery framing, color grading, movement |
| Dance | Dance choreographer | Full body visibility, music sync, angles |
| Education | Viral educator | Concept clarity, visual aids, hook strength |
| Food & Cooking | Food creator | Close-ups, process visibility, lighting |
| Beauty & Fashion | Beauty creator | Face lighting, product visibility, color accuracy |
| Lifestyle | Lifestyle creator | Aesthetic, story arc, visual variety |
| Sports | Sports creator | Action clarity, slow-motion, athlete focus |

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Required. Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model to use |
| `VISION_BACKEND` | `ollama` | `ollama` / `replicate` / `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `REPLICATE_API_TOKEN` | — | Replicate API token (if using replicate) |
| `OPENAI_API_KEY` | — | OpenAI key (if using openai backend) |
