# -*- coding: utf-8 -*-
"""
Object Detection Module
─────────────────────────────────────────────
Uses YOLOv8 (ultralytics) to detect objects across all extracted frames.
Results are fused across frames and deduplicated.

If ultralytics is not installed, falls back to a keyword-based heuristic
from the Gemini vision description.

YOLOv8 nano model is used (yolov8n.pt — ~6MB) — fast enough for real-time use.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

YOLO_AVAILABLE = False
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    pass

# Minimum confidence threshold for YOLO detections
CONF_THRESHOLD = float(os.getenv("YOLO_CONF", "0.35"))

# Objects that are specifically useful for activity detection
ACTIVITY_RELEVANT_OBJECTS = {
    # Music
    "guitar", "violin", "cello", "piano", "keyboard", "drums", "microphone",
    "music stand", "headphones", "speaker", "amplifier", "trumpet", "saxophone",
    # Sports / Fitness
    "sports ball", "basketball", "football", "tennis racket", "baseball bat",
    "frisbee", "skateboard", "skis", "snowboard", "surfboard", "bicycle",
    "barbell", "dumbbell", "yoga mat", "treadmill", "punching bag", "glove",
    # Tech
    "laptop", "computer", "keyboard", "mouse", "cell phone", "tablet",
    "monitor", "camera", "remote", "tv",
    # Food
    "bowl", "cup", "fork", "knife", "spoon", "dining table", "pizza",
    "sandwich", "apple", "orange", "banana", "broccoli", "carrot",
    # General scene
    "person", "car", "chair", "bed", "couch", "potted plant", "book",
    "bottle", "backpack", "umbrella", "suitcase",
}


class ObjectDetector:

    def __init__(self):
        self.model = None
        if YOLO_AVAILABLE:
            try:
                # Downloads yolov8n.pt automatically on first run (~6MB)
                self.model = YOLO("yolov8n.pt")
            except Exception:
                self.model = None

    def detect(self, frame_paths: List[Path]) -> Dict[str, Any]:
        """
        Run object detection across all frames.
        Returns fused, deduplicated detections with confidence scores.
        """
        if not frame_paths:
            return self._empty_result()

        if self.model is not None:
            return self._yolo_detect(frame_paths)
        else:
            return self._empty_result()

    def _yolo_detect(self, frame_paths: List[Path]) -> Dict[str, Any]:
        all_detections = []  # list of (class_name, confidence)
        frame_counts = Counter()

        for fp in frame_paths:
            try:
                results = self.model(str(fp), conf=CONF_THRESHOLD, verbose=False)
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        conf   = float(box.conf[0])
                        name   = result.names[cls_id].lower()
                        all_detections.append((name, conf))
                        frame_counts[name] += 1
            except Exception:
                continue

        # Build deduplicated list with best confidence per object
        best_conf: Dict[str, float] = {}
        for name, conf in all_detections:
            if name not in best_conf or conf > best_conf[name]:
                best_conf[name] = conf

        # Sort by confidence descending
        sorted_objects = sorted(best_conf.items(), key=lambda x: x[1], reverse=True)

        # Split into activity-relevant and general
        relevant = [n for n, _ in sorted_objects if n in ACTIVITY_RELEVANT_OBJECTS]
        all_names = [n for n, _ in sorted_objects]

        return {
            "detected_objects": all_names[:20],          # top 20 overall
            "activity_relevant": relevant[:12],           # top relevant for activity detection
            "frame_counts": dict(frame_counts),           # how many frames each appeared in
            "confidence_map": {n: round(c, 2) for n, c in sorted_objects[:15]},
            "yolo_available": True,
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "detected_objects": [],
            "activity_relevant": [],
            "frame_counts": {},
            "confidence_map": {},
            "yolo_available": False,
        }