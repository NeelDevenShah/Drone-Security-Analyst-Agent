"""
Frame Description Generator: Converts raw video frames to descriptions
Integrates with VLM for real-time frame analysis
"""
import cv2
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import threading
import queue

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import VLM_CONFIG


@dataclass
class FrameDescription:
    """Result of frame analysis"""
    frame_id: int
    timestamp: str
    description: str
    objects: List[str]
    activity_type: str
    confidence: float
    processing_time_ms: float


class FrameDescriptionGenerator:
    """
    Generates textual descriptions of video frames using VLM.
    """

    def __init__(self, vlm_processor=None):
        """
        Initialize frame description generator
        
        Args:
            vlm_processor: VLMProcessor instance for VLM analysis
        """
        self.vlm_processor = vlm_processor
        self.frame_cache = {}

    def describe_frame(self, frame: np.ndarray, frame_id: int, timestamp: str) -> FrameDescription:
        """
        Generate description for a frame
        
        Args:
            frame: OpenCV frame (BGR image)
            frame_id: Frame identifier
            timestamp: Frame timestamp
        
        Returns:
            FrameDescription with analysis results
        """
        start_time = datetime.now()
        
        # Rely strictly on VLM
        if self.vlm_processor and getattr(self.vlm_processor, "is_available", False):
            analysis = self._analyze_with_vlm(frame, frame_id, timestamp)
            description = analysis.description
            objects = analysis.objects
            activity = analysis.activity_type
            confidence = analysis.confidence
        else:
            raise RuntimeError("VLM processor is not available. Real-time analysis requires VLM.")
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return FrameDescription(
            frame_id=frame_id,
            timestamp=timestamp,
            description=description,
            objects=objects,
            activity_type=activity,
            confidence=confidence,
            processing_time_ms=processing_time
        )

    def _analyze_with_vlm(self, frame: np.ndarray, frame_id: int, timestamp: str):
        """Use VLM to describe frame"""
        # Prepare frame data
        frame_data = {
            "frame_id": frame_id,
            "timestamp": timestamp,
            "location": "Drone-Aerial",
            "frame_data": frame,
            "description": "",  # Will be filled by VLM
            "objects": [],
        }
        
        return self.vlm_processor.analyze_frame(frame_data)

    def describe_frames_batch(self, frames: List[Dict[str, Any]]) -> List[FrameDescription]:
        """
        Describe multiple frames efficiently
        
        Args:
            frames: List of frame dicts with 'frame_data', 'frame_id', 'timestamp'
        
        Returns:
            List of FrameDescription objects
        """
        results = []
        for frame_dict in frames:
            desc = self.describe_frame(
                frame_dict['frame_data'],
                frame_dict['frame_id'],
                frame_dict['timestamp']
            )
            results.append(desc)
        return results


class RealTimeFrameAnalyzer:
    """
    Performs real-time frame analysis on video stream.
    Bridges VideoStreamProcessor and FrameDescriptionGenerator.
    """

    def __init__(self, stream_processor, vlm_processor=None):
        """
        Initialize real-time analyzer
        
        Args:
            stream_processor: VideoStreamProcessor instance
            vlm_processor: VLMProcessor for VLM analysis
        """
        self.stream = stream_processor
        self.generator = FrameDescriptionGenerator(vlm_processor)
        self.analysis_results = []
        self.analysis_thread = None

    def start_analysis(self):
        """Start analyzing frames in background"""
        self.analysis_thread = threading.Thread(target=self._analyze_stream, daemon=True)
        self.analysis_thread.start()
        print("✓ Real-time frame analysis started")

    def stop_analysis(self):
        """Stop analyzing frames"""
        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)
        print("✓ Real-time frame analysis stopped")

    def _analyze_stream(self):
        """Continuously analyze frames from stream"""
        for stream_frame in self.stream.frame_generator():
            # Generate description
            description = self.generator.describe_frame(
                stream_frame.frame_data,
                stream_frame.frame_id,
                stream_frame.timestamp
            )
            
            # Store result
            self.analysis_results.append(description)
            
            # Print progress
            if stream_frame.frame_id % 30 == 0:
                print(f"✓ Analyzed frame {stream_frame.frame_id}")
                print(f"  Description: {description.description[:80]}...")

    def get_results(self) -> List[FrameDescription]:
        """Get all analysis results"""
        return self.analysis_results

    def get_latest_description(self) -> Optional[FrameDescription]:
        """Get most recent frame description"""
        return self.analysis_results[-1] if self.analysis_results else None


if __name__ == "__main__":
    # Test frame description generator
    print("Testing Frame Description Generator\n")
    
    # Create synthetic test frame
    test_frame = np.random.randint(0, 255, (480, 720, 3), dtype=np.uint8)
    
    # Add some patterns to make it more realistic
    # Add a "vehicle" (rectangle)
    cv2.rectangle(test_frame, (100, 100), (300, 250), (50, 100, 200), -1)
    # Add "person" (circle)
    cv2.circle(test_frame, (500, 200), 50, (100, 150, 50), -1)
    
    # Generate description
    from vlm_processor import VLMProcessor
    vlm = VLMProcessor()
    generator = FrameDescriptionGenerator(vlm_processor=vlm)
    description = generator.describe_frame(test_frame, 1, datetime.now().isoformat())
    
    print(f"Frame ID: {description.frame_id}")
    print(f"Description: {description.description}")
    print(f"Objects: {description.objects}")
    print(f"Activity: {description.activity_type}")
    print(f"Confidence: {description.confidence}")
    print(f"Processing Time: {description.processing_time_ms:.2f}ms")
