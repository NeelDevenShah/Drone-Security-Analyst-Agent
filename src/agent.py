"""
LangChain Agent: Orchestrates security analysis, pattern detection, and Q&A
"""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from frame_indexer import FrameIndexer
from alert_engine import AlertEngine, Alert
from vlm_processor import VLMProcessor


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

    def __init__(self, db_path: str = "/home/neel/Desktop/flytbaseAI/data/frames.db"):
        """Initialize the agent with indexer and alert engine"""
        self.indexer = FrameIndexer(db_path)
        self.alert_engine = AlertEngine()
        self.vlm_processor = VLMProcessor()
        self.context = AgentContext()
        self.tools = self._register_tools()

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
            # Analyze frame with VLM
            vlm_analysis = self.vlm_processor.analyze_frame(frame)
            
            # Store frame in indexer
            self.indexer.store_frame(
                frame_id=frame['frame_id'],
                timestamp=frame['timestamp'],
                location=frame['location'],
                description=vlm_analysis.description,
                objects=vlm_analysis.objects,
                activity_type=vlm_analysis.activity_type,
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
        # VLM analysis
        vlm_analysis = self.vlm_processor.analyze_frame(frame)
        
        # Check alerts
        alerts = self.alert_engine.analyze_frame(frame)
        
        return {
            "frame_id": frame['frame_id'],
            "timestamp": frame['timestamp'],
            "location": frame['location'],
            "vlm_description": vlm_analysis.description,
            "objects": vlm_analysis.objects,
            "activity_type": vlm_analysis.activity_type,
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

    def query_frame_index(self, query: str) -> List[Dict[str, Any]]:
        """
        Query the frame index with natural language.
        
        Args:
            query: Natural language query
                Examples:
                - "Show all truck events"
                - "What happened at gate at midnight?"
                - "All people detected"
        
        Returns:
            Matching frames with metadata
        """
        query_lower = query.lower()
        
        # Parse query intent
        if "truck" in query_lower or "vehicle" in query_lower:
            return self.indexer.query_by_activity_type("vehicle")
        elif "person" in query_lower or "people" in query_lower:
            return self.indexer.query_by_activity_type("person")
        elif "gate" in query_lower:
            return self.indexer.query_by_location("Main Gate")
        elif "garage" in query_lower:
            return self.indexer.query_by_location("Garage")
        elif "midnight" in query_lower or "night" in query_lower:
            # Query specific time range
            return self.indexer.query_by_timestamp_range("2026-06-13 23:00:00", "2026-06-14 06:00:00")
        else:
            # Return all frames sorted by timestamp
            return self.indexer.get_frames_for_shift_summary()

    def answer_question(self, question: str) -> str:
        """
        Answer user questions about the shift.
        
        Args:
            question: User question
        
        Returns:
            Answer based on processed data
        """
        q_lower = question.lower()
        
        if "how many" in q_lower and "vehicle" in q_lower:
            vehicles = self.indexer.query_by_activity_type("vehicle")
            return f"Detected {len(vehicles)} vehicle events."
        
        elif "how many" in q_lower and "person" in q_lower:
            people = self.indexer.query_by_activity_type("person")
            return f"Detected {len(people)} person events."
        
        elif "what objects" in q_lower or "what was" in q_lower:
            all_frames = self.indexer.get_frames_for_shift_summary()
            objects_set = set()
            for frame in all_frames:
                objects_set.update(frame['objects'])
            return f"Objects detected: {', '.join(sorted(objects_set))}"
        
        elif "alert" in q_lower or "incident" in q_lower:
            alerts = self.indexer.get_all_alerts()
            if not alerts:
                return "No alerts generated during this period."
            return f"Generated {len(alerts)} alerts. High severity: {len([a for a in alerts if a['severity'] in ['HIGH', 'CRITICAL']])}"
        
        elif "blue" in q_lower and "truck" in q_lower:
            truck_frames = self.indexer.query_by_object("F150")
            count = len(truck_frames)
            times = [f['timestamp'] for f in truck_frames]
            return f"Blue Ford F150 appeared {count} times at: {', '.join(times)}"
        
        else:
            return "I can answer questions about: vehicles detected, people detected, objects, alerts, and specific events."

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
