"""Central runtime configuration for the drone security pipeline."""
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class StreamConfig:
    """Video reader defaults."""
    fps_limit: int = 10
    loop: bool = False
    queue_size: int = 10
    frame_timeout_seconds: float = 1.0
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


@dataclass(frozen=True)
class DatabaseConfig:
    """Database defaults."""
    db_path: str = str(PROJECT_ROOT / "data" / "frames.db")


@dataclass(frozen=True)
class SimulatorConfig:
    """Synthetic data generation defaults."""
    output_path: str = str(PROJECT_ROOT / "data" / "simulated_frames.json")
    base_time: datetime = datetime(2026, 6, 13, 0, 0, 0)
    default_coordinates: Dict[str, float] = field(default_factory=lambda: {
        "lat": 40.7128,
        "lon": -74.0060,
        "altitude": 50,
    })
    location_coordinates: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "Main Gate": {"lat": 40.7128, "lon": -74.0060, "altitude": 50},
        "Garage": {"lat": 40.7135, "lon": -74.0065, "altitude": 45},
        "Perimeter Fence": {"lat": 40.7130, "lon": -74.0070, "altitude": 55},
        "Parking Lot": {"lat": 40.7140, "lon": -74.0055, "altitude": 50},
    })


@dataclass(frozen=True)
class VLMConfig:
    """Vision language model defaults."""
    model_name: str = "blip2"
    model_repo: str = "Salesforce/blip2-opt-2.7b"
    use_cv_fallback: bool = True
    fallback_on_load_error: bool = True
    simulated_confidence: float = 0.95
    cv_fallback_confidence: float = 0.65
    vlm_confidence: float = 0.85


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
SIMULATOR_CONFIG = SimulatorConfig()
VLM_CONFIG = VLMConfig()
ALERT_RULE_CONFIG = AlertRuleConfig()
