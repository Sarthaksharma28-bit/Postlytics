"""
Postlytics - Main FastAPI Application
"""
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from modules.video_processor import VideoProcessor
from modules.vision_analyzer import VisionAnalyzer
from modules.audio_analyzer import AudioAnalyzer
from modules.content_understanding import ContentUnderstandingModule
from modules.creator_coach import CreatorCoachModule
from modules.caption_generator import CaptionGenerator
from modules.hashtag_generator import HashtagGenerator
from modules.thumbnail_selector import ThumbnailSelector
from api.schemas import AnalysisResult
from utils.file_manager import FileManager

app = FastAPI(
    title="Postlytics",
    description="Analyze short-form videos and get professional creator feedback",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for thumbnails
Path("static/thumbnails").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

file_manager = FileManager()


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...)
):
    """
    Main endpoint: Upload a reel and receive full creator analysis.
    """
    # Validate file type
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
    if video.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported video format: {video.content_type}")

    session_id = str(uuid.uuid4())
    session_dir = file_manager.create_session(session_id)

    try:
        # ─── STEP 1: Save uploaded video ───────────────────────────────────────
        video_path = session_dir / f"original{Path(video.filename).suffix}"
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)

        # ─── STEP 2: Video Processing — extract frames + audio ─────────────────
        processor = VideoProcessor(session_dir)
        video_meta = processor.process(video_path)
        frames = video_meta["frames"]          # list of frame paths
        audio_path = video_meta["audio_path"]  # extracted audio file
        fps = video_meta["fps"]
        duration = video_meta["duration"]

        # ─── STEP 3: Vision Analysis — describe each frame via LLaVA ──────────
        vision = VisionAnalyzer()
        frame_descriptions = vision.analyze_frames(frames)

        # ─── STEP 4: Visual Quality Analysis ──────────────────────────────────
        visual_metrics = processor.analyze_visual_quality(frames)
        hook_analysis = processor.analyze_hook(frames[:min(3, len(frames))])

        # ─── STEP 5: Audio Analysis ────────────────────────────────────────────
        audio_analyzer = AudioAnalyzer()
        audio_metrics = audio_analyzer.analyze(audio_path)

        # ─── STEP 6: Content Understanding — what is happening ─────────────────
        content_module = ContentUnderstandingModule()
        video_description = content_module.understand(frame_descriptions, audio_metrics)
        content_category = content_module.detect_category(video_description)

        # ─── STEP 7: Postlytics Feedback ────────────────────────────────
        coach = CreatorCoachModule()
        coaching_feedback = coach.generate_feedback(
            content_category=content_category,
            video_description=video_description,
            visual_metrics=visual_metrics,
            hook_analysis=hook_analysis,
            audio_metrics=audio_metrics,
        )

        # ─── STEP 8: Caption Generation ───────────────────────────────────────
        caption_gen = CaptionGenerator()
        captions = caption_gen.generate(video_description, content_category)

        # ─── STEP 9: Hashtag Generation ───────────────────────────────────────
        hashtag_gen = HashtagGenerator()
        hashtags = hashtag_gen.generate(video_description, content_category)

        # ─── STEP 10: Thumbnail Selection ─────────────────────────────────────
        thumbnail_selector = ThumbnailSelector()
        thumbnail_result = thumbnail_selector.select_best(frames, visual_metrics, session_id)

        # ─── Cleanup session files in background ──────────────────────────────
        background_tasks.add_task(file_manager.cleanup_session, session_id, keep_thumbnail=True)

        return AnalysisResult(
            session_id=session_id,
            video_description=video_description,
            content_category=content_category,
            duration_seconds=duration,
            visual_analysis=visual_metrics,
            hook_analysis=hook_analysis,
            audio_analysis=audio_metrics,
            coaching_feedback=coaching_feedback,
            captions=captions,
            hashtags=hashtags,
            thumbnail=thumbnail_result,
        )

    except Exception as e:
        file_manager.cleanup_session(session_id)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Postlytics"}
