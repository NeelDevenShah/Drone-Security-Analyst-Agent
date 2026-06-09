"""
VLM Processor: Analyzes frames using Vision Language Models
Currently uses BLIP-2 from HuggingFace for frame description generation
"""
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    from .config import VLM_CONFIG
except ImportError:
    from config import VLM_CONFIG


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
        self._initialize_model()

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
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                print(f"Using device: {device}")
                
                self.processor = Blip2Processor.from_pretrained(VLM_CONFIG.model_repo)
                self.model = Blip2ForConditionalGeneration.from_pretrained(
                    VLM_CONFIG.model_repo,
                    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                    device_map=device
                )
                print("✓ BLIP-2 model loaded successfully")
            except ImportError:
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
        
        if self.model is None:
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
        # This would be implemented when processing real images
        raise NotImplementedError("Real image processing not yet implemented")

    def extract_objects(self, description: str) -> List[str]:
        """
        Extract objects from a description.
        Uses simple pattern matching or LLM in production.
        """
        objects = description.lower().split()
        # Filter to likely objects
        common_objects = {
            "truck", "car", "sedan", "person", "people", "gate", "garage",
            "fence", "parking", "vehicle", "blue", "ford", "f150", "silver"
        }
        extracted = [obj for obj in objects if obj in common_objects]
        return extracted if extracted else ["unknown"]

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
