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

try:
    from .config import STREAM_CONFIG
except ImportError:
    from config import STREAM_CONFIG


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

    def __init__(
        self,
        source: str,
        callback: Optional[Callable] = None,
        fps_limit: int = STREAM_CONFIG.fps_limit,
        loop: bool = STREAM_CONFIG.loop
    ):
        """Initialize video stream processor"""
        self.source = source
        self.callback = callback
        self.fps_limit: float = float(fps_limit)
        self.loop = loop
        self.frame_queue = queue.Queue(maxsize=STREAM_CONFIG.queue_size)
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
            self.thread.join(timeout=STREAM_CONFIG.stop_join_timeout_seconds)
        if self.cap:
            self.cap.release()
        print("✓ Video stream processing stopped")

    def _process_stream(self):
        """
        Read frames from the video by seeking, not by decoding every frame.
        Calculates how many source frames to skip per step so that the
        effective analysis rate matches fps_limit exactly.
        """
        # How many source frames to advance per analysis step
        source_fps = self.fps if self.fps > 0 else 30.0
        frames_per_step = max(1, int(round(source_fps / self.fps_limit))) if self.fps_limit > 0 else 1
        current_pos = 0  # current position in source frames

        while self.is_running:
            # Seek to the desired position (skips decoding intermediate frames)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
            ret, frame = self.cap.read()

            if not ret:
                if self.loop and self.total_frames > 0:
                    current_pos = 0
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                self.is_running = False
                break

            self.frame_count += 1
            current_pos += frames_per_step

            stream_frame = StreamFrame(
                frame_id=self.frame_count,
                timestamp=datetime.now().isoformat(),
                frame_data=frame,
                fps=self.fps_limit,
                resolution=(self.width, self.height),
                metadata={
                    "source": self.source,
                    "total_frames": self.total_frames,
                    "source_frame_pos": current_pos,
                    "frames_per_step": frames_per_step,
                }
            )

            if self.loop:
                try:
                    self.frame_queue.put(stream_frame, block=False)
                except queue.Full:
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(stream_frame)
                    except queue.Empty:
                        pass
            else:
                while self.is_running:
                    try:
                        self.frame_queue.put(stream_frame, timeout=0.5)
                        break
                    except queue.Full:
                        continue

            if self.callback:
                try:
                    self.callback(stream_frame)
                except Exception as e:
                    print(f"✗ Callback error: {e}")


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
        while self.is_running or not self.frame_queue.empty():
            frame = self.get_frame(timeout=STREAM_CONFIG.frame_timeout_seconds)
            if frame:
                yield frame
            elif not self.is_running:
                break


class LocalVideoProcessor(VideoStreamProcessor):
    """Specialized processor for local video files"""
    pass


class RTSPStreamProcessor(VideoStreamProcessor):
    """Specialized processor for RTSP drone streams"""
    pass
