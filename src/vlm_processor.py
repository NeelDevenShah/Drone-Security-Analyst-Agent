"""
VLM Processor: Analyzes frames using Vision Language Models.
Currently uses Qwen2-VL from HuggingFace for frame description generation.
"""
import json
import cv2
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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

    Currently configured for Qwen2-VL (accessible via HuggingFace).
    Can be extended to support GPT-4o, LLaVA, and other multimodal models.
    """

    def __init__(self, model_name: str = VLM_CONFIG.model_name):
        """
        Initialize VLM processor
        
        Args:
            model_name: Which VLM to use ("qwen2-vl", "llava", "gpt4o")
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
        Load the specified VLM model (Qwen2-VL).
        """
        print(f"Initializing {self.model_name} VLM...")
        
        try:
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
            import torch
            
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {self.device}")
            
            # Limit resolution to optimize dynamic patch visual tokens and prevent OOM
            min_pixels = 256 * 28 * 28
            max_pixels = 512 * 28 * 28
            
            self.processor = AutoProcessor.from_pretrained(
                VLM_CONFIG.model_repo,
                min_pixels=min_pixels,
                max_pixels=max_pixels
            )
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                VLM_CONFIG.model_repo,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None
            )
            self.model.eval()
            print("✓ Qwen2-VL model loaded successfully")
        except ImportError as e:
            raise RuntimeError(
                "Failed to initialize qwen2-vl VLM: transformers is not installed"
            ) from e
        except Exception as e:
            print(f"⚠ Failed to load {self.model_name} model: {e}")
            raise

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
        """
        Processes actual image using Qwen2-VL.
        Requests structured JSON directly from the model.
        """
        frame = frame_data.get("frame_data")
        if frame is None:
            frame = frame_data.get("image")

        if frame is None:
            raise ValueError("VLM frame analysis requires 'frame_data' or 'image'")

        image = self._prepare_image(frame)

        description = ""
        objects = []
        activity_type = "empty"

        try:
            import torch
            
            conversation = [
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": "You are a precise drone security camera assistant. You must analyze images carefully, even under dark, shadowed, or low-light conditions, to detect objects of interest. Output ONLY a valid JSON object. Do not repeat items. Be concise."}
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": self._build_prompt()},
                    ],
                }
            ]
            text_prompt = self.processor.apply_chat_template(conversation, add_generation_prompt=True)
            inputs = self.processor(
                text=[text_prompt],
                images=[image],
                padding=True,
                return_tensors="pt"
            )
            inputs = {key: value.to(self.device) for key, value in inputs.items()}
            
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=VLM_CONFIG.max_new_tokens,
                    do_sample=False,
                    repetition_penalty=1.2,
                )
            
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
            ]
            raw_output = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0].strip()
            
            # Robust JSON parsing and stripping of markdown JSON tags
            clean_output = raw_output
            for marker in ["```json", "```"]:
                if clean_output.startswith(marker):
                    clean_output = clean_output[len(marker):].strip()
                if clean_output.endswith(marker):
                    clean_output = clean_output[:-len(marker)].strip()
            
            parsed = self._loads_json_object(clean_output)
            if parsed and isinstance(parsed, dict):
                # Use normalizer to get allowed objects and activity type
                normalized = self._parse_model_output(clean_output)
                description = normalized["description"]
                objects = normalized["objects"]
                activity_type = normalized["activity_type"]
            else:
                # If full JSON parsing still fails, parse whatever text we got
                description = clean_output
                activity_type = self._infer_activity_type(description)
                objects = [cat for cat in DETECTION_CONFIG.object_categories if cat in description.lower()]

        except Exception as e:
            print(f"⚠ Real VLM analysis failed: {e}")
            raise

        return VLMAnalysis(
            frame_id=frame_data.get("frame_id"),
            timestamp=frame_data.get("timestamp"),
            location=frame_data.get("location"),
            description=description,
            objects=objects,
            activity_type=activity_type,
            confidence=VLM_CONFIG.vlm_confidence,
            vlm_model=self.model_name
        )

    def _infer_activity_type(self, caption: str) -> str:
        """
        Lightweight keyword-based activity_type inference from a VLM caption.
        Needed only to satisfy alert rule conditions (e.g. night_vehicle requires
        activity_type == 'vehicle'). The description itself is the primary signal.
        """
        c = caption.lower()
        has_vehicle = any(kw in c for kw in ("vehicle", "car", "truck", "van", "sedan", "pickup"))
        has_person  = any(kw in c for kw in ("person", "people", "human", "man", "woman", "pedestrian"))

        if has_vehicle and has_person:
            return "vehicle+person"
        if has_vehicle:
            return "vehicle"
        if has_person:
            return "person"
        return "empty"

    def _prepare_image(self, frame):
        """Convert an OpenCV/PIL frame into an RGB PIL image for the VLM, with brightness/contrast enhancement."""
        from PIL import Image
        import numpy as np
        if isinstance(frame, Image.Image):
            frame_np = np.array(frame.convert("RGB"))
        elif isinstance(frame, np.ndarray):
            if frame.ndim == 2:
                frame_np = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            else:
                # Assuming OpenCV BGR if ndarray
                frame_np = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            raise TypeError(f"Unsupported frame type for VLM analysis: {type(frame)!r}")

        # Image enhancement for low-light or low-contrast drone security footage
        if cv2 is not None:
            try:
                # Convert to LAB space to analyze and enhance lightness channel
                lab = cv2.cvtColor(frame_np, cv2.COLOR_RGB2LAB)
                l, a, b = cv2.split(lab)
                
                # Check average brightness of the L channel (0-255 range)
                avg_l = np.mean(l)
                
                # If the image is dark or has low contrast, apply CLAHE to boost details
                if avg_l < 130:
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    cl = clahe.apply(l)
                    # Merge enhanced L channel back
                    enhanced_lab = cv2.merge((cl, a, b))
                    frame_np = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
                    print(f"✓ Applied low-light CLAHE enhancement (avg lightness: {avg_l:.1f})")
            except Exception as e:
                print(f"⚠ Image enhancement failed: {e}")

        return Image.fromarray(frame_np)

    def _build_prompt(self) -> str:
        """Return the VQA prompt for the VLM."""
        return VLM_CONFIG.prompt

    def _parse_model_output(self, raw_output: str) -> Dict[str, Any]:
        """Parse and validate structured VLM output."""
        parsed = self._loads_json_object(raw_output)

        if not parsed:
            return {
                "description": raw_output or "Frame analyzed by VLM, no caption generated",
                "objects": ["scene"],
                "activity_type": "empty",
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
            normalized_objects = ["scene"]

        activity_type = parsed.get("activity_type", "empty")
        allowed_activities = {
            activity.lower(): activity
            for activity in DETECTION_CONFIG.activity_categories
        }
        if isinstance(activity_type, str) and activity_type.strip().lower() in allowed_activities:
            activity_type = allowed_activities[activity_type.strip().lower()]
        else:
            activity_type = "empty"

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
    def create(model_name: str = "qwen2-vl") -> VLMProcessor:
        """Create a VLM processor for the specified model"""
        return VLMProcessor(model_name=model_name)


if __name__ == "__main__":
    # Test VLM processor with simulated data
    processor = VLMProcessor(model_name="qwen2-vl")
    
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
