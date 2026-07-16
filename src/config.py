"""Central runtime configuration for the drone security pipeline."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple


import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from prompts import VLM_ANALYSIS_PROMPT


@dataclass(frozen=True)
class StreamConfig:
    """Video reader defaults."""
    fps_limit: float = 0.5          # frames per second to process (0.5 = 1 frame every 2s)
    loop: bool = False
    queue_size: int = 4
    frame_timeout_seconds: float = 3.0
    stop_join_timeout_seconds: float = 5.0


@dataclass(frozen=True)
class PipelineConfig:
    """End-to-end pipeline defaults."""
    video_source: str = str(PROJECT_ROOT / "sample_data" / "09172008flight1tape1_5.mpg")
    db_path: str = str(PROJECT_ROOT / "data" / "frames_live.db")
    export_path: str = "results.json"
    default_location: str = "Drone-Aerial"
    context_frame_limit: int = 50
    progress_interval_frames: int = 10
    stop_join_timeout_seconds: float = 10.0
    # Frame image storage
    frames_dir: str = str(PROJECT_ROOT / "data" / "frames")
    frame_save_interval: int = 1    # at 0.5 FPS every frame is already sparse; save all


@dataclass(frozen=True)
class DatabaseConfig:
    """Database defaults."""
    db_path: str = str(PROJECT_ROOT / "data" / "frames.db")



@dataclass(frozen=True)
class DetectionConfig:
    """Configurable object and activity labels used by the VLM prompt."""
    object_categories: Tuple[str, ...] = (
        "vehicle",
        "person",
        "building",
        "gate",
        "road",
        "nature",
    )
    activity_categories: Tuple[str, ...] = (
        "vehicle+person",
        "vehicle",
        "person",
        "empty",
    )


@dataclass(frozen=True)
class VLMConfig:
    """Vision language model defaults."""
    enabled: bool = True
    model_name: str = "qwen2-vl"
    model_repo: str = "Qwen/Qwen2-VL-2B-Instruct"
    # Prompt for Qwen2-VL requesting structured JSON output loaded from prompts/
    prompt: str = VLM_ANALYSIS_PROMPT
    max_new_tokens: int = 256
    simulated_confidence: float = 0.95
    vlm_confidence: float = 0.85


@dataclass(frozen=True)
class LLMConfig:
    """Language model defaults for Q&A."""
    enabled: bool = True
    model_name: str = "transformers"
    model_repo: str = "Qwen/Qwen2.5-1.5B-Instruct"
    device: str = "cuda"  # Default to CUDA/GPU for model acceleration

    max_new_tokens: int = 256
    temperature: float = 0.1


@dataclass(frozen=True)
class AlertRuleConfig:
    """Alert rule thresholds and severity values."""
    loitering_hours: Tuple[int, ...] = (23, 0, 1, 2)
    night_vehicle_hours: Tuple[int, ...] = (23, 0, 1, 2, 3, 4, 5, 6)
    loitering_severity: str = "HIGH"
    loitering_threat_score: int = 8
    perimeter_severity: str = "MEDIUM"
    perimeter_threat_score: int = 6
    night_vehicle_severity: str = "LOW"
    night_vehicle_threat_score: int = 3
    repeat_visit_severity: str = "MEDIUM"
    repeat_visit_threat_score: int = 5
    dwell_time_severity: str = "LOW"
    dwell_time_threat_score: int = 4
    dwell_time_min_frames: int = 3
    dwell_time_min_minutes: int = 240
    suspicious_locations: Tuple[str, ...] = ("perimeter", "fence")
    severity_icons: Dict[str, str] = field(default_factory=lambda: {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MEDIUM": "🟡",
        "LOW": "🟢",
    })


STREAM_CONFIG = StreamConfig()
PIPELINE_CONFIG = PipelineConfig()
DATABASE_CONFIG = DatabaseConfig()
DETECTION_CONFIG = DetectionConfig()
VLM_CONFIG = VLMConfig()
LLM_CONFIG = LLMConfig()
ALERT_RULE_CONFIG = AlertRuleConfig()
