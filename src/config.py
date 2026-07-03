"""Central runtime configuration for the drone security pipeline."""
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    fallback_object: str = "scene"
    fallback_activity: str = "empty"
    cv_fallback_keywords: Dict[str, Tuple[str, ...]] = field(default_factory=lambda: {
        "vehicle": (
            "truck", "trucks", "car", "cars", "sedan", "sedans",
            "vehicle", "vehicles", "automobile", "automobiles", "van", "vans",
            "bus", "buses", "pickup", "pickups"
        ),
        "person": (
            "person", "people", "human", "humans", "man", "men",
            "woman", "women", "pedestrian", "pedestrians", "individual"
        ),
        "building": ("building", "buildings", "structure", "house", "garage", "warehouse"),
        "gate": ("gate", "fence", "barrier", "entrance", "door"),
        "road": ("road", "street", "path", "pavement", "asphalt", "driveway"),
        "nature": ("grass", "vegetation", "tree", "trees", "outdoor", "field"),
    })
    cv_fallback_activity_rules: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
        ("vehicle+person", ("vehicle", "person")),
        ("vehicle", ("vehicle",)),
        ("person", ("person",)),
    )


@dataclass(frozen=True)
class VLMConfig:
    """Vision language model defaults."""
    enabled: bool = True
    model_name: str = "qwen2-vl"
    model_repo: str = "Qwen/Qwen2-VL-2B-Instruct"
    # Prompt for Qwen2-VL requesting structured JSON output
    prompt: str = (
        "Analyze this drone security camera image. Even if the image contains dark regions, low light, or shadows, "
        "examine it carefully to identify any visible elements. Provide a JSON object with the following keys:\n"
        "1. \"description\": A clear, concise natural language description of the scene from a security perspective (focusing on people, vehicles, perimeter areas, and their activities).\n"
        "2. \"objects\": A list containing any of these specific categories that are present: \"vehicle\", \"person\", \"building\", \"gate\", \"road\", \"nature\".\n"
        "3. \"activity_type\": A single category representing the main activity: \"vehicle+person\" (if both are interacting), \"vehicle\" (if only vehicles), \"person\" (if only people), or \"empty\".\n"
        "Return ONLY the raw JSON object, no Markdown blocks or extra text."
    )
    max_new_tokens: int = 256
    use_cv_fallback: bool = True
    simulated_confidence: float = 0.95
    cv_fallback_confidence: float = 0.65
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
SIMULATOR_CONFIG = SimulatorConfig()
DETECTION_CONFIG = DetectionConfig()
VLM_CONFIG = VLMConfig()
LLM_CONFIG = LLMConfig()
ALERT_RULE_CONFIG = AlertRuleConfig()
