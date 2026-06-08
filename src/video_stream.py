"""Live Video Stream Processor: Real-time drone video analysis."""
import os

os.environ.setdefault("OPENCV_FFMPEG_LOGLEVEL", "error")

import cv2
import threading
import queue
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import time


@dataclass
class StreamFrame:
    """Represents a single frame from the video stream"""
    frame_id: int
    timestamp: str
    frame_data: Any
    fps: float
    resolution: tuple
    metadata: Dict[str, Any] = None


class VideoStreamProcessor:
    """Processes live video streams from files or RTSP sources."""

    def __init__(self, source: str, callback: Optional[Callable] = None, fps_limit: int = 30):
        """Initialize video stream processor"""
        self.source = source
        self.callback = callback
        self.fps_limit = fps_limit
        self.frame_queue = queue.Queue(maxsize=10)
        self.is_running = False
        self.frame_count = 0
        self.cap = None
        self.thread = None
        
        self.fps = 30
        self.width = 720
        self.height = 480
        self.total_frames = 0
        
        self._open_stream()

    def _open_stream(self):
        """Open video stream from source"""
        try:
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)

            if hasattr(cv2, "setLogLevel"):
                try:
                    cv2.setLogLevel(3)
                except Exception:
                    pass
            
            if not self.cap.isOpened():
                raise RuntimeError(f"Failed to open stream: {self.source}")
            
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            print(f"✓ Opened video stream: {self.source}")
            print(f"  Resolution: {self.width}x{self.height}")
            print(f"  FPS: {self.fps}")
            print(f"  Total Frames: {self.total_frames}")
            
        except Exception as e:
            print(f"✗ Failed to open stream: {e}")
            raise

    def start(self):
        """Start processing video stream in background thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._process_stream, daemon=True)
        self.thread.start()
        print("✓ Video stream processing started")

    def stop(self):
        """Stop processing video stream"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.cap:
            self.cap.release()
        print("✓ Video stream processing stopped")

    def _process_stream(self):
        """Process video stream frames"""
        frame_delay = 1.0 / self.fps_limit if self.fps_limit > 0 else 0
        
        while self.is_running:
            ret, frame = self.cap.read()
            
            if not ret:
                if self.total_frames > 0:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break
            
            self.frame_count += 1
            
            stream_frame = StreamFrame(
                frame_id=self.frame_count,
                timestamp=datetime.now().isoformat(),
                frame_data=frame,
                fps=self.fps,
                resolution=(self.width, self.height),
                metadata={
                    "source": self.source,
                    "total_frames": self.total_frames,
                    "current_frame": int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                }
            )
            
            try:
                self.frame_queue.put(stream_frame, block=False)
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put(stream_frame)
                except:
                    pass
            
            if self.callback:
                try:
                    self.callback(stream_frame)
                except Exception as e:
                    print(f"✗ Callback error: {e}")
            
            if frame_delay > 0:
                time.sleep(frame_delay)

    def get_frame(self, timeout: float = 1.0) -> Optional[StreamFrame]:
        """Get next frame from queue"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_latest_frame(self) -> Optional[StreamFrame]:
        """Get most recent frame without blocking"""
        latest_frame = None
        while True:
            try:
                latest_frame = self.frame_queue.get_nowait()
            except queue.Empty:
                break
        return latest_frame

    def frame_generator(self):
        """Generator that yields frames as they're available"""
        while self.is_running:
            frame = self.get_frame(timeout=5.0)
            if frame:
                yield frame
            else:
                break


class LocalVideoProcessor(VideoStreamProcessor):
    """Specialized processor for local video files"""
    pass


class RTSPStreamProcessor(VideoStreamProcessor):
    """Specialized processor for RTSP drone streams"""
    pass
