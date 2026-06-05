"""
Live Video Processing Pipeline: End-to-end real-time security analysis
Integrates video stream → frame analysis → agent processing → alerts
"""
import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import threading
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from video_stream import VideoStreamProcessor, LocalVideoProcessor
from frame_description import RealTimeFrameAnalyzer, FrameDescriptionGenerator
from agent import SecurityAnalystAgent
from frame_indexer import FrameIndexer
from dataclasses import asdict


class LiveSecurityAnalysisPipeline:
    """
    Complete end-to-end pipeline for live drone security analysis.
    
    Pipeline Flow:
    Video Input → Frame Extraction → Description Generation → 
    Agent Analysis → Alert Generation → Output/Dashboard
    """

    def __init__(
        self,
        video_source: str,
        db_path: str = "/home/neel/Desktop/flytbaseAI/data/frames.db",
        vlm_processor=None,
        fps_limit: int = 10
    ):
        """
        Initialize live analysis pipeline
        
        Args:
            video_source: Path to video file or RTSP URL
            db_path: Database path for storing frames and alerts
            vlm_processor: VLM processor for frame analysis
            fps_limit: Frame rate limit for processing
        """
        self.video_source = video_source
        self.fps_limit = fps_limit
        self.is_running = False
        
        # Initialize components
        self.stream_processor = LocalVideoProcessor(video_source, fps_limit=fps_limit)
        self.frame_generator = FrameDescriptionGenerator(vlm_processor=vlm_processor)
        self.agent = SecurityAnalystAgent(db_path=db_path)
        self.indexer = FrameIndexer(db_path=db_path)
        
        # Results storage
        self.frames_processed = 0
        self.alerts_generated = []
        self.frame_descriptions = []
        
        # Processing thread
        self.process_thread = None

    def start(self):
        """Start the live analysis pipeline"""
        if self.is_running:
            return
        
        self.is_running = True
        self.stream_processor.start()
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()
        
        print("=" * 70)
        print("🚁 LIVE DRONE SECURITY ANALYSIS PIPELINE STARTED")
        print("=" * 70)
        print(f"Video Source: {self.video_source}")
        print(f"FPS Limit: {self.fps_limit}")
        print(f"Database: {self.indexer.db_path}")
        print("=" * 70)

    def stop(self):
        """Stop the pipeline"""
        self.is_running = False
        if self.process_thread:
            self.process_thread.join(timeout=10)
        self.stream_processor.stop()
        self.agent.close()
        self.indexer.close()
        
        print("\n" + "=" * 70)
        print("✓ PIPELINE STOPPED")
        print("=" * 70)

    def _process_loop(self):
        """Main processing loop"""
        previous_frames = []
        
        for stream_frame in self.stream_processor.frame_generator():
            if not self.is_running:
                break
            
            try:
                # 1. Generate frame description
                frame_desc = self.frame_generator.describe_frame(
                    stream_frame.frame_data,
                    stream_frame.frame_id,
                    stream_frame.timestamp
                )
                
                self.frame_descriptions.append(frame_desc)
                
                # 2. Create frame data dict
                frame_data = {
                    "frame_id": frame_desc.frame_id,
                    "timestamp": frame_desc.timestamp,
                    "location": "Drone-Aerial",  # Default location
                    "description": frame_desc.description,
                    "objects": frame_desc.objects,
                    "activity_type": frame_desc.activity_type,
                    "telemetry": stream_frame.metadata
                }
                
                # 3. Store in indexer
                self.indexer.store_frame(
                    frame_id=frame_data['frame_id'],
                    timestamp=frame_data['timestamp'],
                    location=frame_data['location'],
                    description=frame_data['description'],
                    objects=frame_data['objects'],
                    activity_type=frame_data['activity_type'],
                    threat_score=0,
                    telemetry=frame_data.get('telemetry')
                )
                
                # 4. Analyze with agent (with context)
                frame_alerts = self.agent.alert_engine.analyze_frame(frame_data, previous_frames)
                
                # 5. Store alerts
                for alert in frame_alerts:
                    self.indexer.store_alert(
                        frame_id=alert.frame_id,
                        alert_type=alert.alert_type,
                        severity=alert.severity,
                        threat_score=alert.threat_score,
                        message=alert.message
                    )
                    self.alerts_generated.append(alert)
                
                # 6. Update context
                previous_frames.append(frame_data)
                if len(previous_frames) > 50:  # Keep last 50 frames for context
                    previous_frames.pop(0)
                
                # 7. Print progress
                self.frames_processed += 1
                
                if self.frames_processed % 10 == 0:
                    self._print_progress_update()
                
                # High-risk alerts printed immediately
                high_risk = [a for a in frame_alerts if a.severity in ["HIGH", "CRITICAL"]]
                for alert in high_risk:
                    self._print_alert(alert)
                
            except Exception as e:
                print(f"✗ Error processing frame: {e}")
                import traceback
                traceback.print_exc()

    def _print_progress_update(self):
        """Print progress update"""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Progress: {self.frames_processed} frames processed")
        
        if self.alerts_generated:
            severity_counts = {}
            for alert in self.alerts_generated:
                severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1
            
            alert_str = ", ".join([f"{k}:{v}" for k, v in severity_counts.items()])
            print(f"  Alerts: {alert_str}")

    def _print_alert(self, alert):
        """Print alert with formatting"""
        severity_emoji = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }
        
        emoji = severity_emoji.get(alert.severity, "⚪")
        print(f"\n{emoji} ALERT [{alert.severity}] Threat:{alert.threat_score}/10")
        print(f"   Time: {alert.timestamp}")
        print(f"   Type: {alert.alert_type}")
        print(f"   Message: {alert.message}")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of analysis"""
        return {
            "frames_processed": self.frames_processed,
            "total_alerts": len(self.alerts_generated),
            "high_alerts": len([a for a in self.alerts_generated if a.severity in ["HIGH", "CRITICAL"]]),
            "medium_alerts": len([a for a in self.alerts_generated if a.severity == "MEDIUM"]),
            "low_alerts": len([a for a in self.alerts_generated if a.severity == "LOW"]),
            "avg_processing_time_ms": sum([d.processing_time_ms for d in self.frame_descriptions]) / len(self.frame_descriptions) if self.frame_descriptions else 0
        }

    def print_final_report(self):
        """Print final analysis report"""
        summary = self.get_summary()
        
        print("\n" + "=" * 70)
        print("📊 FINAL ANALYSIS REPORT")
        print("=" * 70)
        print(f"Frames Processed: {summary['frames_processed']}")
        print(f"Processing Rate: ~{self.fps_limit} FPS")
        print(f"Avg Frame Processing Time: {summary['avg_processing_time_ms']:.2f}ms")
        print(f"\nAlerts Generated: {summary['total_alerts']}")
        print(f"  🔴 Critical/High: {summary['high_alerts']}")
        print(f"  🟡 Medium: {summary['medium_alerts']}")
        print(f"  🟢 Low: {summary['low_alerts']}")
        print("=" * 70)
        
        # Print high-risk alerts
        if summary['high_alerts'] > 0:
            print("\n⚠️  HIGH-RISK INCIDENTS:")
            for alert in self.alerts_generated:
                if alert.severity in ["HIGH", "CRITICAL"]:
                    print(f"  [{alert.timestamp}] {alert.severity}: {alert.message}")
        
        print("\n" + "=" * 70)

    def export_results(self, output_file: str = "live_analysis_results.json"):
        """Export results to JSON"""
        import json
        
        results = {
            "summary": self.get_summary(),
            "frames": [asdict(d) for d in self.frame_descriptions],
            "alerts": [
                {
                    "type": a.alert_type,
                    "severity": a.severity,
                    "threat_score": a.threat_score,
                    "timestamp": a.timestamp,
                    "location": a.location,
                    "message": a.message
                }
                for a in self.alerts_generated
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Results exported to {output_file}")


def main():
    """Main entry point for live analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Live Drone Security Analysis Pipeline")
    parser.add_argument(
        "--video",
        type=str,
        default="/home/neel/Desktop/flytbaseAI/sample_data/09172008flight1tape1_5.mpg",
        help="Path to video file or RTSP URL"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="Frame rate limit (default: 10)"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="/home/neel/Desktop/flytbaseAI/data/frames_live.db",
        help="Database path (default: frames_live.db)"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export results to JSON file"
    )
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = LiveSecurityAnalysisPipeline(
        video_source=args.video,
        db_path=args.db,
        fps_limit=args.fps
    )
    
    try:
        pipeline.start()
        
        # Wait for processing to complete
        while pipeline.is_running and pipeline.stream_processor.is_running:
            import time
            time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    finally:
        pipeline.stop()
        pipeline.print_final_report()
        
        if args.export:
            pipeline.export_results(args.export)


if __name__ == "__main__":
    main()
