"""
VLM Processor: Analyzes frames using Vision Language Models
Currently uses BLIP-2 from HuggingFace for frame description generation
"""
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    from .config import DETECTION_CONFIG, VLM_CONFIG
except ImportError:
    from config import DETECTION_CONFIG, VLM_CONFIG


@dataclass
class VLMAnalysis:
    """Result of VLM frame analysis"""
    frame_id: int
    timestamp: str
    location: str
    description: str
    objects: List[str]
    activity_type: str
    confidence: float
    vlm_model: str


class VLMProcessor:
    """
    Processes frames with Vision Language Models to extract semantic information.
    
    Currently configured for BLIP-2 (accessible via HuggingFace).
    Can be extended to support GPT-4o, LLaVA, Qwen-VL, etc.
    """

    def __init__(self, model_name: str = VLM_CONFIG.model_name):
        """
        Initialize VLM processor
        
        Args:
            model_name: Which VLM to use ("blip2", "llava", "qwen-vl", "gpt4o")
        """
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.device = "cpu"
        self._initialize_model()

    @property
    def is_available(self) -> bool:
        """Whether a real image model is loaded and ready for inference."""
        return self.model is not None and self.processor is not None

    def _initialize_model(self):
        """
        Load the specified VLM model.
        For production, would download from HuggingFace or use API.
        """
        print(f"Initializing {self.model_name} VLM...")
        
        if self.model_name == "blip2":
            try:
                from transformers import Blip2Processor, Blip2ForConditionalGeneration
                import torch
                
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                print(f"Using device: {self.device}")
                
                self.processor = Blip2Processor.from_pretrained(VLM_CONFIG.model_repo)
                self.model = Blip2ForConditionalGeneration.from_pretrained(
                    VLM_CONFIG.model_repo,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
                )
                self.model.to(self.device)
                self.model.eval()
                print("✓ BLIP-2 model loaded successfully")
            except ImportError:
                if not VLM_CONFIG.fallback_on_load_error:
                    raise RuntimeError(
                        "Failed to initialize blip2 VLM: transformers is not installed"
                    )

                print("⚠ Transformers not installed. Using mock VLM processor.")
                self.processor = None
                self.model = None
            except Exception as e:
                if not VLM_CONFIG.fallback_on_load_error:
                    raise

                print(f"⚠ Failed to load {self.model_name} model: {e}")
                print("⚠ Using mock VLM processor.")
                self.processor = None
                self.model = None
        else:
            if not VLM_CONFIG.fallback_on_load_error:
                raise ValueError(f"VLM model {self.model_name!r} is not configured")

            print(f"⚠ Model {self.model_name} not yet configured. Using mock processor.")

    def analyze_frame(self, frame_data: Dict[str, Any]) -> VLMAnalysis:
        """
        Analyze a frame and extract semantic information.
        
        If real VLM is not available, uses the provided description
        (in simulation, description is pre-generated).
        
        Args:
            frame_data: Dict with 'description', 'timestamp', 'location', 'objects', etc.
        
        Returns:
            VLMAnalysis with extracted information
        """
        # In simulation mode, we use pre-generated descriptions
        # In production, we would analyze actual images
        
        if not self.is_available:
            # Simulation mode: use provided description
            return self._analyze_simulated_frame(frame_data)
        else:
            # Real mode: would process actual image
            return self._analyze_real_frame(frame_data)

    def _analyze_simulated_frame(self, frame_data: Dict[str, Any]) -> VLMAnalysis:
        """Use pre-generated description (simulation mode)"""
        return VLMAnalysis(
            frame_id=frame_data.get("frame_id"),
            timestamp=frame_data.get("timestamp"),
            location=frame_data.get("location"),
            description=frame_data.get("description"),
            objects=frame_data.get("objects", []),
            activity_type=frame_data.get("activity_type", "unknown"),
            confidence=VLM_CONFIG.simulated_confidence,
            vlm_model=f"{self.model_name}_simulated"
        )

    def _analyze_real_frame(self, frame_data: Dict[str, Any]) -> VLMAnalysis:
        """Analyze actual image with VLM (production mode)"""
        frame = frame_data.get("frame_data")
        if frame is None:
            frame = frame_data.get("image")

        if frame is None:
            raise ValueError("VLM frame analysis requires 'frame_data' or 'image'")

        image = self._prepare_image(frame)

        try:
            import torch

            inputs = self.processor(
                images=image,
                text=self._build_prompt(),
                return_tensors="pt"
            )
            inputs = {key: value.to(self.device) for key, value in inputs.items()}

            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=VLM_CONFIG.max_new_tokens
                )

            description = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0].strip()
        except Exception:
            if not VLM_CONFIG.fallback_on_load_error:
                raise
            raise

        parsed_result = self._parse_model_output(description)

        return VLMAnalysis(
            frame_id=frame_data.get("frame_id"),
            timestamp=frame_data.get("timestamp"),
            location=frame_data.get("location"),
            description=parsed_result["description"],
            objects=parsed_result["objects"],
            activity_type=parsed_result["activity_type"],
            confidence=VLM_CONFIG.vlm_confidence,
            vlm_model=self.model_name
        )

    def _prepare_image(self, frame):
        """Convert an OpenCV/PIL frame into an RGB PIL image for the VLM."""
        from PIL import Image

        if isinstance(frame, Image.Image):
            return frame.convert("RGB")

        try:
            import cv2
            import numpy as np

            if isinstance(frame, np.ndarray):
                if frame.ndim == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                else:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return Image.fromarray(frame).convert("RGB")
        except ImportError:
            pass

        raise TypeError(f"Unsupported frame type for VLM analysis: {type(frame)!r}")

    def _build_prompt(self) -> str:
        """Build the VLM prompt from configured labels."""
        return VLM_CONFIG.prompt.format(
            object_categories=", ".join(DETECTION_CONFIG.object_categories),
            activity_categories=", ".join(DETECTION_CONFIG.activity_categories),
        )

    def _parse_model_output(self, raw_output: str) -> Dict[str, Any]:
        """Parse and validate structured VLM output."""
        parsed = self._loads_json_object(raw_output)

        if not parsed:
            return {
                "description": raw_output or "Frame analyzed by VLM, no caption generated",
                "objects": [DETECTION_CONFIG.fallback_object],
                "activity_type": DETECTION_CONFIG.fallback_activity,
            }

        objects = parsed.get("objects", [])
        if isinstance(objects, str):
            objects = [objects]
        allowed_objects = {
            category.lower(): category
            for category in DETECTION_CONFIG.object_categories
        }
        normalized_objects = [
            allowed_objects[obj.strip().lower()]
            for obj in objects
            if isinstance(obj, str) and obj.strip().lower() in allowed_objects
        ]
        if not normalized_objects:
            normalized_objects = [DETECTION_CONFIG.fallback_object]

        activity_type = parsed.get("activity_type", DETECTION_CONFIG.fallback_activity)
        allowed_activities = {
            activity.lower(): activity
            for activity in DETECTION_CONFIG.activity_categories
        }
        if isinstance(activity_type, str) and activity_type.strip().lower() in allowed_activities:
            activity_type = allowed_activities[activity_type.strip().lower()]
        else:
            activity_type = DETECTION_CONFIG.fallback_activity

        description = parsed.get("description") or raw_output or "Frame analyzed by VLM"

        return {
            "description": description,
            "objects": normalized_objects,
            "activity_type": activity_type,
        }

    def _loads_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """Load the first JSON object from a model response."""
        if not text:
            return None

        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            parsed = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

        return parsed if isinstance(parsed, dict) else None

    def assess_security_threat(self, frame_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze frame image with VLM directly to detect security threats.
        """
        if self.is_available:
            try:
                frame_img = frame_data.get("frame_data") or frame_data.get("image")
                if frame_img is not None:
                    image = self._prepare_image(frame_img)
                    prompt = (
                        "Question: Analyze this drone security frame. Is there a security threat (like loitering, perimeter breach, or off-hours vehicle) in this image? "
                        "Answer in JSON format: {\"threat_detected\": true, \"alert_type\": \"perimeter_breach\", \"severity\": \"HIGH\", \"threat_score\": 8, \"message\": \"Detailed description of threat\"}"
                    )

                    import torch
                    inputs = self.processor(images=image, text=prompt, return_tensors="pt")
                    inputs = {key: value.to(self.device) for key, value in inputs.items()}

                    with torch.no_grad():
                        generated_ids = self.model.generate(**inputs, max_new_tokens=150)

                    output_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

                    
                    parsed = self._loads_json_object(output_text)
                    if parsed and isinstance(parsed, dict) and parsed.get("threat_detected"):
                        return parsed
            except Exception as e:
                print(f"⚠ Direct VLM threat assessment failed: {e}")
                
        # If model is not loaded (mock mode) or failed, fall back to simulation/metadata rule heuristics
        return self._assess_threat_from_text(frame_data)

    def _assess_threat_from_text(self, frame_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Simulate VLM threat analysis of the frame metadata"""
        description = frame_data.get("description", "").lower()
        location = frame_data.get("location", "").lower()
        timestamp = frame_data.get("timestamp", "")
        
        # Parse hour
        hour = 0
        try:
            if " " in timestamp:
                hour = int(timestamp.split(" ")[1].split(":")[0])
            elif "T" in timestamp:
                hour = int(timestamp.split("T")[1].split(":")[0])
        except Exception:
            pass
            
        # Loitering threat
        if "loitering" in description or "hanging around" in description or ("person" in description and (hour >= 23 or hour <= 2)):
            return {
                "threat_detected": True,
                "alert_type": "loitering_midnight",
                "severity": "HIGH",
                "threat_score": 8,
                "message": f"VLM Alert: Detected person loitering near {frame_data.get('location')} during off-hours."
            }
        
        # Perimeter breach
        if any(k in location for k in ["perimeter", "fence", "gate"]) and ("person" in description or "vehicle" in description):
            return {
                "threat_detected": True,
                "alert_type": "perimeter_breach",
                "severity": "MEDIUM",
                "threat_score": 6,
                "message": f"VLM Alert: Detected activity near restricted zone: {frame_data.get('location')}."
            }
            
        # Night vehicle
        if "vehicle" in description or "truck" in description or "car" in description:
            if hour >= 23 or hour <= 6:
                return {
                    "threat_detected": True,
                    "alert_type": "night_vehicle",
                    "severity": "LOW",
                    "threat_score": 3,
                    "message": f"VLM Alert: Detected vehicle activity near {frame_data.get('location')} during night hours."
                }
                
        return None

    def batch_analyze_frames(self, frames: List[Dict[str, Any]]) -> List[VLMAnalysis]:
        """
        Analyze multiple frames efficiently.
        
        Args:
            frames: List of frame data dicts
        
        Returns:
            List of VLMAnalysis results
        """
        results = []
        for frame in frames:
            analysis = self.analyze_frame(frame)
            results.append(analysis)
        return results


class VLMFactory:
    """Factory to create VLM processors for different models"""

    @staticmethod
    def create(model_name: str = "blip2") -> VLMProcessor:
        """Create a VLM processor for the specified model"""
        return VLMProcessor(model_name=model_name)


if __name__ == "__main__":
    # Test VLM processor with simulated data
    processor = VLMProcessor(model_name="blip2")
    
    test_frame = {
        "frame_id": 1,
        "timestamp": "2026-06-13 00:01:00",
        "location": "Main Gate",
        "description": "Unknown person loitering near main gate entrance at midnight",
        "objects": ["person", "main gate"],
        "activity_type": "person"
    }
    
    analysis = processor.analyze_frame(test_frame)
    print(f"\nAnalysis Result:")
    print(f"  Frame ID: {analysis.frame_id}")
    print(f"  Timestamp: {analysis.timestamp}")
    print(f"  Location: {analysis.location}")
    print(f"  Description: {analysis.description}")
    print(f"  Objects: {analysis.objects}")
    print(f"  Activity: {analysis.activity_type}")
    print(f"  Confidence: {analysis.confidence}")
    print(f"  Model: {analysis.vlm_model}")
