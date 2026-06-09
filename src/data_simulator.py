"""
Data Simulator: Generates realistic simulated drone frames and telemetry
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

try:
    from .config import SIMULATOR_CONFIG
except ImportError:
    from config import SIMULATOR_CONFIG


@dataclass
class TelemetryData:
    """Drone telemetry information"""
    timestamp: str
    location: str
    altitude: float  # meters
    latitude: float
    longitude: float
    battery_level: int  # 0-100


@dataclass
class FrameData:
    """Simulated video frame with context"""
    frame_id: int
    timestamp: str
    location: str
    description: str  # VLM-like description
    objects: List[str]  # ["blue truck", "main gate"]
    telemetry: Dict[str, Any]
    activity_type: str  # "vehicle", "person", "vehicle+person", "empty"


class DataSimulator:
    """Generates realistic simulation scenarios for security monitoring"""

    def __init__(self):
        self.frames: List[FrameData] = []
        self.frame_counter = 0

    def generate_realistic_scenario(self) -> List[FrameData]:
        """
        Generate a realistic daily monitoring scenario with:
        - Vehicle entries/exits
        - Repeat visits
        - Loitering incidents
        - Normal background activity
        """
        frames = [
            # Morning: Delivery truck arrives
            self._create_frame(
                time_offset=0,  # 00:00 baseline
                location="Main Gate",
                description="Blue Ford F150 truck slowly entering the main gate",
                objects=["blue Ford F150", "main gate", "truck"],
                activity_type="vehicle"
            ),
            self._create_frame(
                time_offset=1,
                location="Garage",
                description="Blue Ford F150 parked at garage entrance",
                objects=["blue Ford F150", "garage", "truck"],
                activity_type="vehicle"
            ),
            self._create_frame(
                time_offset=12*60,  # 12:00
                location="Garage",
                description="Blue Ford F150 still parked at garage, delivery person loading items",
                objects=["blue Ford F150", "garage", "person", "truck"],
                activity_type="vehicle+person"
            ),
            # Evening: Unusual late-night activity
            self._create_frame(
                time_offset=23*60 + 45,  # 23:45
                location="Main Gate",
                description="Blue Ford F150 re-entering property for second time today via main gate",
                objects=["blue Ford F150", "main gate", "truck"],
                activity_type="vehicle"
            ),
            # CRITICAL: Loitering incident at midnight
            self._create_frame(
                time_offset=24*60 + 1,  # 00:01 next day
                location="Main Gate",
                description="Unknown person loitering near main gate entrance at midnight, no vehicle present",
                objects=["unknown person", "main gate", "suspicious activity"],
                activity_type="person"
            ),
            self._create_frame(
                time_offset=24*60 + 15,  # 00:15
                location="Perimeter Fence",
                description="Person moving along perimeter fence line, appears to be surveying property",
                objects=["unknown person", "fence", "perimeter"],
                activity_type="person"
            ),
            # Normal activity resumes
            self._create_frame(
                time_offset=24*60 + 30,  # 00:30
                location="Main Gate",
                description="Blue Ford F150 truck exiting property",
                objects=["blue Ford F150", "main gate", "truck"],
                activity_type="vehicle"
            ),
            self._create_frame(
                time_offset=36*60,  # 06:00
                location="Parking Lot",
                description="Empty parking lot, morning clearing",
                objects=["parking lot"],
                activity_type="empty"
            ),
            self._create_frame(
                time_offset=42*60,  # 07:00
                location="Main Gate",
                description="Silver sedan entering property at morning shift start",
                objects=["silver sedan", "main gate"],
                activity_type="vehicle"
            ),
            self._create_frame(
                time_offset=48*60,  # 08:00
                location="Garage",
                description="Silver sedan parked at garage, employee entering building",
                objects=["silver sedan", "garage", "person"],
                activity_type="vehicle+person"
            ),
        ]
        self.frames = frames
        return frames

    def _create_frame(
        self,
        time_offset: int,  # minutes from baseline
        location: str,
        description: str,
        objects: List[str],
        activity_type: str
    ) -> FrameData:
        """Create a single frame with realistic telemetry"""
        self.frame_counter += 1
        
        # Calculate timestamp
        base_time = SIMULATOR_CONFIG.base_time
        frame_time = base_time + timedelta(minutes=time_offset)
        timestamp = frame_time.strftime("%Y-%m-%d %H:%M:%S")
        
        coords = SIMULATOR_CONFIG.location_coordinates.get(
            location,
            SIMULATOR_CONFIG.default_coordinates
        )
        
        # Create telemetry
        telemetry = {
            "timestamp": timestamp,
            "location": location,
            "altitude": coords["altitude"],
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "battery_level": max(10, 100 - (time_offset // 100))  # Decrease over time
        }
        
        return FrameData(
            frame_id=self.frame_counter,
            timestamp=timestamp,
            location=location,
            description=description,
            objects=objects,
            telemetry=telemetry,
            activity_type=activity_type
        )

    def get_frames_as_json(self) -> str:
        """Export frames as JSON"""
        frames_dict = [asdict(frame) for frame in self.frames]
        return json.dumps(frames_dict, indent=2)

    def get_frames_as_list(self) -> List[Dict[str, Any]]:
        """Export frames as list of dicts"""
        return [asdict(frame) for frame in self.frames]

    def save_to_file(self, filepath: str):
        """Save simulated frames to JSON file"""
        with open(filepath, 'w') as f:
            f.write(self.get_frames_as_json())
        print(f"✓ Saved {len(self.frames)} frames to {filepath}")


if __name__ == "__main__":
    # Generate and save sample data
    simulator = DataSimulator()
    frames = simulator.generate_realistic_scenario()
    
    print(f"Generated {len(frames)} simulated frames:")
    for frame in frames:
        print(f"  [{frame.timestamp}] {frame.location}: {frame.description}")
    
    # Save to file
    simulator.save_to_file(SIMULATOR_CONFIG.output_path)
