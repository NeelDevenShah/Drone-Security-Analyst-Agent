"""
LangChain Agent: Orchestrates security analysis, pattern detection, and Q&A
"""
import sys
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frame_indexer import FrameIndexer
from alert_engine import AlertEngine, Alert
from vlm_processor import VLMProcessor
from config import DATABASE_CONFIG, VLM_CONFIG, LLM_CONFIG
from bm25 import BM25
from prompts import AGENT_QA_PROMPT


@dataclass
class AgentContext:
    """Context maintained by the agent across multiple frames"""
    frames_processed: int = 0
    total_alerts: int = 0
    high_risk_alerts: int = 0
    vehicles_detected: set = None
    people_detected: set = None
    
    def __post_init__(self):
        if self.vehicles_detected is None:
            self.vehicles_detected = set()
        if self.people_detected is None:
            self.people_detected = set()


class SecurityAnalystAgent:
    """
    LangChain-style agent for drone security analysis.
    
    Maintains context across frames, can answer questions, and generates reports.
    """

    def __init__(
        self,
        db_path: str = DATABASE_CONFIG.db_path,
        vlm_model: str = VLM_CONFIG.model_name,
        vlm_processor=None
    ):
        """Initialize the agent with indexer and alert engine"""
        self.indexer = FrameIndexer(db_path)
        self.vlm_processor = vlm_processor or VLMProcessor(model_name=vlm_model)
        self.alert_engine = AlertEngine(vlm_processor=self.vlm_processor, llm_processor=self)
        self.context = AgentContext()
        self.tools = self._register_tools()
        
        # Load 2B LLM for Q&A
        self.llm = None
        self.tokenizer = None
        self.llm_model_name = LLM_CONFIG.model_name
        self.llm_model_repo = LLM_CONFIG.model_repo
        self.llm_attempted = False

    def _initialize_llm(self):
        """Initialize the LLM model for Q&A via HuggingFace Transformers."""
        if self.llm_attempted:
            return
        self.llm_attempted = True

        print(f"Initializing QA LLM (Model: {self.llm_model_repo})...")
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
            
            # Determine target device
            config_device = getattr(LLM_CONFIG, 'device', 'cpu')
            if config_device == 'auto':
                target_device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                target_device = config_device
                
            self.device = target_device
            print(f"Loading QA model on device: {self.device}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.llm_model_repo)
            
            self.llm = AutoModelForCausalLM.from_pretrained(
                self.llm_model_repo,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            self.llm.to(self.device)
            print(f"✓ QA LLM loaded via Transformers successfully on {self.device}")
        except Exception as e:
            print(f"⚠ Failed to load QA model: {e}")
            self.llm = None
            raise e

    def query_llm(self, prompt: str) -> str:
        """Query the Qwen2.5 LLM model directly."""
        if LLM_CONFIG.enabled and self.llm is None:
            self._initialize_llm()
        if self.llm is None:
            return ""
        try:
            import torch
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            prompt_len = inputs.input_ids.shape[1]
            with torch.no_grad():
                outputs = self.llm.generate(
                    **inputs,
                    max_new_tokens=LLM_CONFIG.max_new_tokens,
                    temperature=LLM_CONFIG.temperature,
                    do_sample=LLM_CONFIG.temperature > 0,
                )
            decoded = self.tokenizer.decode(outputs[0][prompt_len:], skip_special_tokens=True)
            return decoded.strip()
        except Exception as e:
            print(f"QA LLM query failed: {e}")
            return ""

    def _register_tools(self) -> Dict[str, Callable]:
        """Register available tools for the agent"""
        return {
            "query_frame_index": self.query_frame_index,
            "analyze_frame": self.analyze_frame,
            "get_shift_summary": self.get_shift_summary,
            "answer_question": self.answer_question,
            "check_alert_rules": self._check_alert_rules,
            "detect_patterns": self._detect_patterns,
        }

    def process_frames(self, frames: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of frames through the full pipeline.
        
        Args:
            frames: List of frame data to process
        
        Returns:
            Processing summary and alerts
        """
        results = {
            "frames_processed": 0,
            "alerts_generated": [],
            "patterns_detected": [],
            "summary": ""
        }
        
        for frame in frames:
            # Only run VLM re-analysis when the frame carries actual pixel data
            # (i.e. live pipeline frames). Simulated / JSON frames have no image
            # and would crash with "requires 'frame_data' or 'image'"
            has_image = frame.get("frame_data") is not None or frame.get("image") is not None
            if self.vlm_processor and has_image:
                vlm_analysis = self.vlm_processor.analyze_frame(frame)
            else:
                vlm_analysis = None

            # Store frame in indexer
            self.indexer.store_frame(
                frame_id=frame['frame_id'],
                timestamp=frame['timestamp'],
                location=frame['location'],
                description=vlm_analysis.description if vlm_analysis else frame.get('description', ''),
                objects=vlm_analysis.objects if vlm_analysis else frame.get('objects', []),
                activity_type=vlm_analysis.activity_type if vlm_analysis else frame.get('activity_type', 'unknown'),
                threat_score=0,
                telemetry=frame.get('telemetry')
            )
            
            # Analyze for alerts
            frame_alerts = self.alert_engine.analyze_frame(frame, frames[:frames.index(frame)])
            
            # Store alerts
            for alert in frame_alerts:
                self.indexer.store_alert(
                    frame_id=alert.frame_id,
                    alert_type=alert.alert_type,
                    severity=alert.severity,
                    threat_score=alert.threat_score,
                    message=alert.message
                )
                results["alerts_generated"].append({
                    "timestamp": alert.timestamp,
                    "location": alert.location,
                    "severity": alert.severity,
                    "message": alert.message
                })
            
            # Update context
            self.context.frames_processed += 1
            self.context.total_alerts += len(frame_alerts)
            self.context.high_risk_alerts += len([a for a in frame_alerts if a.severity in ["HIGH", "CRITICAL"]])
            
            # Track objects
            for obj in frame.get('objects', []):
                if any(v in obj.lower() for v in ['truck', 'car', 'sedan', 'vehicle']):
                    self.context.vehicles_detected.add(obj)
                elif 'person' in obj.lower():
                    self.context.people_detected.add(obj)
        
        results["frames_processed"] = self.context.frames_processed
        results["summary"] = self.get_shift_summary()
        
        return results

    def analyze_frame(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single frame.
        
        Args:
            frame: Frame data to analyze
        
        Returns:
            Analysis result including alerts
        """
        # VLM analysis – only when frame carries actual pixel data
        has_image = frame.get("frame_data") is not None or frame.get("image") is not None
        vlm_analysis = self.vlm_processor.analyze_frame(frame) if (self.vlm_processor and has_image) else None
        
        # Check alerts
        alerts = self.alert_engine.analyze_frame(frame)
        
        return {
            "frame_id": frame['frame_id'],
            "timestamp": frame['timestamp'],
            "location": frame['location'],
            "vlm_description": vlm_analysis.description if vlm_analysis else frame.get('description', ''),
            "objects": vlm_analysis.objects if vlm_analysis else frame.get('objects', []),
            "activity_type": vlm_analysis.activity_type if vlm_analysis else frame.get('activity_type', 'unknown'),
            "alerts": [
                {
                    "type": a.alert_type,
                    "severity": a.severity,
                    "threat_score": a.threat_score,
                    "message": a.message
                }
                for a in alerts
            ]
        }

    def _enrich_frame_with_alert_context(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        """Add alert context to the frame record"""
        frame_id = frame.get('frame_id') or frame.get('id')
        alert_context = []
        if frame_id is not None:
            with self.indexer.db_lock:
                cursor = self.indexer.conn.execute(
                    "SELECT alert_type, severity, threat_score, message FROM alerts WHERE frame_id = ?",
                    (frame_id,)
                )
                rows = cursor.fetchall()
                for r in rows:
                    alert_context.append({
                        "alert_type": r["alert_type"],
                        "severity": r["severity"],
                        "threat_score": r["threat_score"],
                        "message": r["message"]
                    })
        frame["alert_context"] = alert_context
        return frame

    def query_frame_index(self, query: str) -> List[Dict[str, Any]]:
        """
        Query the frame index with natural language using Hybrid Search (BM25 + Embeddings).
        
        Args:
            query: Natural language query
        
        Returns:
            Matching frames with metadata and alert context
        """
        def enrich(frames):
            return [self._enrich_frame_with_alert_context(f) for f in frames]
            
        all_frames = self.indexer.get_frames_for_shift_summary()
        if not all_frames:
            return []
            
        # 1. BM25 Search
        bm25_searcher = BM25(all_frames)
        bm25_scores = bm25_searcher.score(query)
        bm25_sorted = sorted(bm25_scores, key=lambda x: x[0], reverse=True)
        
        # 2. ChromaDB Semantic Search
        semantic_frames = self.indexer.query_by_semantic_similarity(query, limit=len(all_frames))
        
        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        k = 60
        
        # Add BM25 ranks
        for rank, (_, frame) in enumerate(bm25_sorted):
            fid = frame['frame_id']
            rrf_scores[fid] = rrf_scores.get(fid, 0.0) + (1.0 / (k + rank + 1))
            
        # Add ChromaDB ranks
        for rank, frame in enumerate(semantic_frames):
            fid = frame['frame_id']
            rrf_scores[fid] = rrf_scores.get(fid, 0.0) + (1.0 / (k + rank + 1))
            
        # Sort by RRF score descending
        frames_by_id = {f['frame_id']: f for f in all_frames}
        sorted_fids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # Return top 10 matching frames enriched with alert context
        matching_frames = [frames_by_id[fid] for fid in sorted_fids[:10] if fid in frames_by_id]
        return enrich(matching_frames)

    def answer_question(self, question: str) -> str:
        """
        Answer user questions about the shift using dynamic Hybrid Search.
        
        Args:
            question: User question
        
        Returns:
            Answer based on processed data
        """
        q_lower = question.lower()
        
        # Query frame index using dynamic Hybrid Search (Embedding + BM25)
        frames = self.query_frame_index(question)
        if not frames:
            return "Based on the security logs, no relevant events were found matching your query."
            
        # If the 2B QA LLM is loaded, use it to answer the question using the retrieved context!
        if LLM_CONFIG.enabled and self.llm is None:
            self._initialize_llm()

        if self.llm is not None:
            context = "Security logs from current shift:\n"
            for idx, f in enumerate(frames):
                alerts_str = ", ".join([f"{a['severity']}: {a['message']}" for a in f['alert_context']]) if f['alert_context'] else "None"
                context += f"Event {idx+1}: [{f['timestamp']}] Location: {f['location']}, Description: {f['description']}, Objects: {', '.join(f['objects'])}, Activity: {f['activity_type']}, Alerts: {alerts_str}\n"
            
            prompt = AGENT_QA_PROMPT.format(context=context, question=question)
            
            try:
                return self.query_llm(prompt)
            except Exception as e:
                print(f"⚠ QA LLM generation failed: {e}. Falling back to dynamic summary.")

        # Case: The question asks about repeated visits / items appearing more than once
        if "more than once" in q_lower or "repeated" in q_lower or "frequency" in q_lower:
            all_frames = self.indexer.get_frames_for_shift_summary()
            object_counts = {}
            for f in all_frames:
                for obj in f.get('objects', []):
                    obj_clean = obj.strip()
                    object_counts[obj_clean] = object_counts.get(obj_clean, 0) + 1
            
            repeating_objects = {obj for obj, count in object_counts.items() if count > 1}
            
            if not repeating_objects:
                return "Based on the shift log, no objects appeared more than once."
                
            response = f"I detected the following objects appearing more than once: {', '.join(sorted(repeating_objects))}.\nHere are the corresponding frames:\n"
            for f in frames:
                has_repeating = any(obj.strip() in repeating_objects for obj in f.get('objects', []))
                if has_repeating:
                    alerts_str = ", ".join([f"{a['severity']}: {a['message']}" for a in f['alert_context']]) if f['alert_context'] else "None"
                    response += f"- [{f['timestamp']}] Location: {f['location']}, Activity: {f['activity_type']}, Objects: {', '.join(f['objects'])}, Alerts: {alerts_str}\n"
            return response
            
        # Case: Counting query
        if "how many" in q_lower or "count" in q_lower:
            count = len(frames)
            category = "event"
            if "vehicle" in q_lower or "truck" in q_lower or "car" in q_lower:
                category = "vehicle event"
            elif "person" in q_lower or "people" in q_lower:
                category = "person event"
            elif "alert" in q_lower or "incident" in q_lower:
                category = "alert/incident"
                
            response = f"I found {count} relevant {category}(s) matching your query:\n"
            for f in frames:
                alerts_str = ", ".join([f"{a['severity']}: {a['message']}" for a in f['alert_context']]) if f['alert_context'] else "None"
                response += f"- [{f['timestamp']}] Location: {f['location']}, Description: {f['description']} (Alerts: {alerts_str})\n"
            return response
            
        # Case: Asking what objects or what was seen
        if "what objects" in q_lower or "what was" in q_lower or "what appeared" in q_lower:
            objects_seen = set()
            for f in frames:
                objects_seen.update(f.get('objects', []))
            if objects_seen:
                return f"The following objects were detected in the matching logs: {', '.join(sorted(objects_seen))}."
            return "No specific objects were identified in the matching records."
            
        # General response synthesis from matching frames
        response = f"Here are the relevant security events found matching your query:\n"
        for f in frames:
            alerts_str = ", ".join([f"{a['severity']}: {a['message']}" for a in f['alert_context']]) if f['alert_context'] else "None"
            response += f"- [{f['timestamp']}] Location: {f['location']}, Activity: {f['activity_type']}, Objects: {', '.join(f['objects'])}, Alerts: {alerts_str}\n"
        return response

    def get_shift_summary(self) -> str:
        """
        Generate a comprehensive shift summary.
        
        Returns:
            Human-readable shift report
        """
        frames = self.indexer.get_frames_for_shift_summary()
        alerts = self.indexer.get_all_alerts()
        
        # Count by type
        vehicle_count = len(self.indexer.query_by_activity_type("vehicle"))
        person_count = len(self.indexer.query_by_activity_type("person"))
        
        # Count by severity
        high_alerts = len([a for a in alerts if a['severity'] in ['HIGH', 'CRITICAL']])
        medium_alerts = len([a for a in alerts if a['severity'] == 'MEDIUM'])
        
        # Build summary
        summary = f"""
=== SHIFT SUMMARY REPORT ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DETECTION SUMMARY:
- Total Frames Processed: {len(frames)}
- Vehicle Events: {vehicle_count}
- Person Events: {person_count}
- Total Alerts: {len(alerts)}

ALERT BREAKDOWN:
- High/Critical: {high_alerts}
- Medium: {medium_alerts}
- Low: {len(alerts) - high_alerts - medium_alerts}

KEY INCIDENTS:
"""
        
        # Add high-risk alerts
        for alert in alerts:
            if alert['severity'] in ['HIGH', 'CRITICAL']:
                summary += f"  • [{alert['timestamp']}] {alert['severity']}: {alert['message']}\n"
        
        # Pattern detection
        summary += "\nPATTERNS DETECTED:\n"
        vehicle_list = list(self.context.vehicles_detected)
        if vehicle_list:
            summary += f"  • Vehicles: {', '.join(vehicle_list)}\n"
        if self.context.people_detected:
            summary += f"  • People detected during shift\n"
        
        # Repeat visit detection
        truck_frames = self.indexer.query_by_object("F150")
        if len(truck_frames) > 1:
            summary += f"  • Blue Ford F150 made {len(truck_frames)} visits (potential repeat visitor)\n"
        
        summary += "\nRECOMMENDATIONS:\n"
        if high_alerts > 0:
            summary += "  • URGENT: Review high-severity incidents immediately\n"
        if person_count > 0:
            summary += "  • Review person detection events for validation\n"
        summary += "  • Archive frame metadata for audit trail\n"
        
        return summary

    def _check_alert_rules(self, frame: Dict[str, Any]) -> List[Alert]:
        """Tool: Check alert rules for a frame"""
        return self.alert_engine._check_rules(frame)

    def _detect_patterns(self) -> Dict[str, Any]:
        """Tool: Detect patterns in processed frames"""
        return {
            "vehicles": list(self.context.vehicles_detected),
            "people": list(self.context.people_detected),
            "total_frames": self.context.frames_processed,
            "total_alerts": self.context.total_alerts,
            "high_risk_alerts": self.context.high_risk_alerts
        }

    def close(self):
        """Clean up resources"""
        self.indexer.close()


if __name__ == "__main__":
    # Test the agent
    from dataclasses import asdict
    from data_simulator import DataSimulator
    
    # Generate test data
    simulator = DataSimulator()
    frames = simulator.generate_realistic_scenario()
    
    # Create and run agent
    agent = SecurityAnalystAgent()
    
    print("Processing frames through agent...\n")
    results = agent.process_frames([asdict(f) for f in frames])
    
    print(f"✓ Processed {results['frames_processed']} frames")
    print(f"✓ Generated {len(results['alerts_generated'])} alerts")
    
    print(results['summary'])
    
    # Test Q&A
    print("\n=== Q&A Examples ===")
    print(f"Q: How many vehicles detected?")
    print(f"A: {agent.answer_question('How many vehicles detected?')}\n")
    
    print(f"Q: What about the blue truck?")
    print(f"A: {agent.answer_question('What about the blue truck?')}\n")
    
    agent.close()
