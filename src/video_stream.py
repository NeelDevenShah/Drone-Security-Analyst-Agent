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
            # Do NOT force cv2.CAP_FFMPEG for MPEG-1/2 files – it causes the
            # decoder to return raw YUV bytes without colorspace conversion,
            # producing rainbow static.  Let OpenCV auto-select the backend.
            self.cap = cv2.VideoCapture(self.source)

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

    def _is_mpeg_source(self) -> bool:
        """Return True if the source is an MPEG-1/2 file that requires full decode of every frame."""
        src = str(self.source).lower()
        return any(src.endswith(ext) for ext in (".mpg", ".mpeg", ".m2v", ".vob", ".ts"))

    @staticmethod
    def _is_valid_frame(frame) -> bool:
        """
        Reject garbage frames before they reach the VLM.

        Two failure modes we guard against:
          • All-black  (ret=True but frame is zeros) – mean < 3
          • Static / noise (YUV misread) – std-dev across all pixels > 80
            because real-world footage is spatially correlated; pure noise is not.
        """
        import numpy as np
        if frame is None:
            return False
        mean = float(frame.mean())
        std  = float(frame.std())
        if mean < 3:
            return False   # all-black frame
        if std > 80 and mean > 100:
            return False   # rainbow static / decoder garbage
        return True

    def _process_stream(self):
        """
        Read frames from the video, sampling at fps_limit rate.

        Strategy depends on the codec:

        • MPEG-1/2 (.mpg/.mpeg): fully decode EVERY frame via cap.read() and
          discard frames we don't need by counting.  grab()-without-retrieve()
          skipping corrupts the MPEG inter-frame decoder state (P/B frames
          depend on previously decoded reference frames) and produces solid
          black frames even when ret=True.

        • All other formats (H.264, VP9, MJPEG …): use the faster grab()-skip
          approach – advance N-1 positions with grab() (no decode) then
          cap.read() for the Nth frame.  A failed grab() during the skip phase
          signals EOS; we never call read() afterwards to avoid the zero-frame
          black-image bug.
        """
        source_fps = self.fps if self.fps > 0 else 30.0
        frames_per_step = max(1, int(round(source_fps / self.fps_limit))) if self.fps_limit > 0 else 1
        use_full_decode = self._is_mpeg_source()

        if use_full_decode:
            print(f"  ℹ MPEG source detected – using full-decode frame sampling (every {frames_per_step} frames)")

        raw_frame_counter = 0  # counts every decoded frame from the source

        while self.is_running:
            if use_full_decode:
                # MPEG path: decode every frame, keep only every Nth
                ret, frame = self.cap.read()
                if not ret:
                    if self.loop and self.total_frames > 0:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        raw_frame_counter = 0
                        continue
                    self.is_running = False
                    break

                raw_frame_counter += 1
                if raw_frame_counter % frames_per_step != 0:
                    continue  # discard this frame, keep decoding

                if not self._is_valid_frame(frame):
                    print(f"  ⚠ Skipping garbage frame at source position {raw_frame_counter} (black/static)")
                    continue

            else:
                # Non-MPEG path: grab()-skip then read()
                skip_count = frames_per_step - 1
                eos_during_skip = False
                for _ in range(skip_count):
                    if not self.cap.grab():
                        eos_during_skip = True
                        break

                if eos_during_skip:
                    ret, frame = False, None
                else:
                    ret, frame = self.cap.read()

                if not ret:
                    if self.loop and self.total_frames > 0:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        raw_frame_counter = 0
                        continue
                    self.is_running = False
                    break

                if not self._is_valid_frame(frame):
                    print(f"  ⚠ Skipping garbage frame #{self.frame_count + 1} (black/static)")
                    continue

            self.frame_count += 1
            current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))


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
