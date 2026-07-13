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
from config import ALERT_RULE_CONFIG, PIPELINE_CONFIG, STREAM_CONFIG, VLM_CONFIG
from vlm_processor import VLMProcessor


class LiveSecurityAnalysisPipeline:
    """
    Complete end-to-end pipeline for live drone security analysis.
    
    Pipeline Flow:
    Video Input → Frame Extraction → Description Generation → 
    Agent Analysis → Alert Generation → Output/Dashboard
    """

    def __init__(
        self,
        video_source: str = PIPELINE_CONFIG.video_source,
        db_path: str = PIPELINE_CONFIG.db_path,
        vlm_processor=None,
        fps_limit: float = STREAM_CONFIG.fps_limit,
        loop: bool = STREAM_CONFIG.loop,
        use_vlm: bool = VLM_CONFIG.enabled
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
        self.loop = loop
        self.use_vlm = use_vlm
        self.is_running = False
        self.completed = False
        self.db_path = db_path
        
        # Initialize components
        if self.use_vlm and vlm_processor is None:
            vlm_processor = VLMProcessor(model_name=VLM_CONFIG.model_name)

        self.vlm_processor = vlm_processor
        self.stream_processor = LocalVideoProcessor(video_source, fps_limit=fps_limit, loop=loop)
        self.frame_generator = FrameDescriptionGenerator(vlm_processor=self.vlm_processor)
        self.agent = SecurityAnalystAgent(
            db_path=db_path,
            vlm_processor=self.vlm_processor,
            enable_vlm=self.use_vlm
        )
        self.indexer = FrameIndexer(db_path=db_path)
        
        # Results storage
        self.frames_processed = 0
        self.alerts_generated = []
        self.frame_descriptions = []
        self.frame_image_paths: Dict[int, str] = {}  # frame_id → saved JPEG path

        # Create frames directory for saved images
        import os
        os.makedirs(PIPELINE_CONFIG.frames_dir, exist_ok=True)

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
        interval_s = round(1.0 / self.fps_limit, 2) if self.fps_limit > 0 else "∞"
        print(f"Analysis Rate: {self.fps_limit} FPS  (1 frame every {interval_s}s)")
        print(f"Loop Video: {'yes' if self.loop else 'no'}")
        print(f"VLM Enabled: {'yes' if self.use_vlm else 'no'}")
        print(f"Database: {self.indexer.db_path}")
        print(f"Frame images: {PIPELINE_CONFIG.frames_dir}")
        print("=" * 70)

    def stop(self):
        """Stop the pipeline"""
        self.is_running = False
        if self.process_thread:
            self.process_thread.join(timeout=PIPELINE_CONFIG.stop_join_timeout_seconds)
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
                    "location": PIPELINE_CONFIG.default_location,
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

                # 5. Save frame image to disk
                #    - Always save if the frame triggered an alert
                #    - Sample clean frames every frame_save_interval processed frames
                should_save = bool(frame_alerts) or (
                    self.frames_processed % PIPELINE_CONFIG.frame_save_interval == 0
                )
                if should_save:
                    try:
                        import cv2
                        import os
                        tag = "alert" if frame_alerts else "sample"
                        img_filename = f"frame_{frame_desc.frame_id:06d}_{tag}.jpg"
                        img_path = os.path.join(PIPELINE_CONFIG.frames_dir, img_filename)
                        cv2.imwrite(img_path, stream_frame.frame_data)
                        self.frame_image_paths[frame_desc.frame_id] = img_path
                    except Exception as e:
                        print(f"⚠ Could not save frame image: {e}")

                # 6. Store alerts
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
                if len(previous_frames) > PIPELINE_CONFIG.context_frame_limit:
                    previous_frames.pop(0)
                
                # 7. Print progress
                self.frames_processed += 1
                
                if self.frames_processed % PIPELINE_CONFIG.progress_interval_frames == 0:
                    self._print_progress_update()
                
                # High-risk alerts printed immediately
                high_risk = [a for a in frame_alerts if a.severity in ["HIGH", "CRITICAL"]]
                for alert in high_risk:
                    self._print_alert(alert)
                
            except Exception as e:
                print(f"✗ Error processing frame: {e}")
                import traceback
                traceback.print_exc()

        if self.is_running and not self.loop and not self.stream_processor.is_running:
            self.completed = True
            self.is_running = False

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
        emoji = ALERT_RULE_CONFIG.severity_icons.get(alert.severity, "⚪")
        print(f"\n{emoji} ALERT [{alert.severity}] Threat:{alert.threat_score}/10")
        print(f"   Time: {alert.timestamp}")
        print(f"   Type: {alert.alert_type}")
        print(f"   Message: {alert.message}")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of analysis"""
        return {
            "video_source": self.video_source,
            "loop": self.loop,
            "completed": self.completed,
            "vlm_enabled": self.use_vlm,
            "vlm_available": bool(self.vlm_processor and self.vlm_processor.is_available),
            "vlm_model": self.vlm_processor.model_name if self.vlm_processor else "cv_fallback",
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
        print(f"Status: {'completed video' if self.completed else 'stopped before completion'}")
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

    def export_results(self, output_file: str = PIPELINE_CONFIG.export_path, append: bool = False):
        """Export full end-to-end results to JSON.

        Args:
            output_file: Path to write results JSON.
            append: If True, merge with existing file instead of overwriting.
                    New frames replace old ones with the same frame_id.
                    Alerts are combined and de-duplicated by message text.

        Each frame record contains:
          - frame_id, timestamp, location
          - description, objects, activity_type, confidence, processing_time_ms
          - telemetry (GPS, altitude, etc.)
          - image_path: path to saved JPEG proof image (None if not saved)
          - alerts: list of every alert triggered on this frame
        """
        import json

        # Build a frame_id → frame_data lookup so we can attach telemetry/location
        frame_data_lookup: Dict[int, Dict[str, Any]] = {}
        for fd in self.frame_descriptions:
            frame_data_lookup[fd.frame_id] = {
                "frame_id": fd.frame_id,
                "timestamp": fd.timestamp,
                "description": fd.description,
                "objects": fd.objects,
                "activity_type": fd.activity_type,
                "confidence": round(fd.confidence, 4),
                "processing_time_ms": round(fd.processing_time_ms, 2),
                "location": PIPELINE_CONFIG.default_location,
                "telemetry": None,
                "image_path": self.frame_image_paths.get(fd.frame_id),
                "alerts": [],
            }

        # Attach telemetry from the DB
        try:
            with self.indexer.db_lock:
                rows = self.indexer.conn.execute(
                    "SELECT frame_id, location, telemetry FROM frames"
                ).fetchall()
            for row in rows:
                fid = row["frame_id"]
                if fid in frame_data_lookup:
                    frame_data_lookup[fid]["location"] = row["location"] or PIPELINE_CONFIG.default_location
                    raw_tel = row["telemetry"]
                    if raw_tel:
                        try:
                            frame_data_lookup[fid]["telemetry"] = json.loads(raw_tel) if isinstance(raw_tel, str) else raw_tel
                        except Exception:
                            frame_data_lookup[fid]["telemetry"] = raw_tel
        except Exception as e:
            print(f"⚠ Could not load telemetry from DB for export: {e}")

        # Attach alerts to their parent frames
        all_alerts_list = []
        for alert in self.alerts_generated:
            alert_record = {
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "threat_score": alert.threat_score,
                "timestamp": alert.timestamp,
                "location": alert.location,
                "message": alert.message,
                "frame_image": self.frame_image_paths.get(alert.frame_id),
            }
            all_alerts_list.append(alert_record)
            fid = alert.frame_id
            if fid in frame_data_lookup:
                frame_data_lookup[fid]["alerts"].append(alert_record)

        # Sort new frames by frame_id
        new_frames = sorted(frame_data_lookup.values(), key=lambda x: x["frame_id"])

        # ── Append mode: merge with existing file ───────────────────────────────
        import os
        if append and os.path.exists(output_file):
            try:
                with open(output_file) as f:
                    existing = json.load(f)

                # Merge frames: existing first, then new frames overwrite by frame_id
                existing_frames_by_id: Dict[int, Dict[str, Any]] = {
                    fr["frame_id"]: fr for fr in existing.get("frames", [])
                }
                for fr in new_frames:
                    existing_frames_by_id[fr["frame_id"]] = fr
                merged_frames = sorted(existing_frames_by_id.values(), key=lambda x: x["frame_id"])

                # Merge alerts: combine and de-duplicate by (frame_id, message)
                seen_alert_keys = set()
                merged_alerts = []
                for a in existing.get("all_alerts", []) + all_alerts_list:
                    key = (a.get("timestamp", ""), a.get("message", ""))
                    if key not in seen_alert_keys:
                        seen_alert_keys.add(key)
                        merged_alerts.append(a)

                # Merge summary counts
                existing_summary = existing.get("summary", {})
                new_summary = self.get_summary()
                merged_summary = dict(existing_summary)
                for k, v in new_summary.items():
                    if isinstance(v, (int, float)) and isinstance(existing_summary.get(k), (int, float)):
                        merged_summary[k] = existing_summary[k] + v
                    else:
                        merged_summary[k] = v  # new value wins for non-numeric fields
                merged_summary["video_source"] = (
                    f"{existing_summary.get('video_source', '')} + {new_summary.get('video_source', '')}"
                )

                frames_list = merged_frames
                all_alerts_list = merged_alerts
                summary = merged_summary
                print(f"  ℹ Append mode: merging with {len(existing.get('frames', []))} existing frames")
            except Exception as e:
                print(f"⚠ Could not read existing file for append – overwriting instead: {e}")
                frames_list = new_frames
                summary = self.get_summary()
        else:
            if append:
                print(f"  ℹ Append mode: {output_file} does not exist yet – creating new file")
            frames_list = new_frames
            summary = self.get_summary()

        results = {
            "summary": summary,
            "frames": frames_list,
            "all_alerts": all_alerts_list,
        }

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n✓ Results {'appended to' if append else 'exported to'} {output_file}")
        print(f"  {len(frames_list)} total frames, {len(all_alerts_list)} total alerts")





def main():
    """Main entry point for live analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Live Drone Security Analysis Pipeline")
    parser.add_argument(
        "--video",
        type=str,
        default=PIPELINE_CONFIG.video_source,
        help=f"Path to video file or RTSP URL (default: {PIPELINE_CONFIG.video_source})"
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=STREAM_CONFIG.fps_limit,
        help=f"Frames per second to analyse (default: {STREAM_CONFIG.fps_limit}, e.g. 0.5 = 1 frame every 2s)"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=PIPELINE_CONFIG.db_path,
        help=f"Database path (default: {PIPELINE_CONFIG.db_path})"
    )
    parser.add_argument(
        "--export",
        type=str,
        nargs="?",
        const=PIPELINE_CONFIG.export_path,
        help=f"Export results to JSON file (default when flag has no value: {PIPELINE_CONFIG.export_path})"
    )
    parser.add_argument(
        "--loop",
        action=argparse.BooleanOptionalAction,
        default=STREAM_CONFIG.loop,
        help=f"Loop the input video continuously until interrupted (default: {STREAM_CONFIG.loop})"
    )
    parser.add_argument(
        "--vlm",
        action=argparse.BooleanOptionalAction,
        default=VLM_CONFIG.enabled,
        help=f"Use configured VLM for semantic frame descriptions (default: {VLM_CONFIG.enabled})"
    )
    parser.add_argument(
        "--append",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Append results to an existing export file instead of overwriting it. "
            "Use this to accumulate results from multiple videos into a single JSON. "
            "New frames replace existing ones with the same frame_id; "
            "alerts are combined and de-duplicated. (default: False = overwrite)"
        )
    )
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = LiveSecurityAnalysisPipeline(
        video_source=args.video,
        db_path=args.db,
        fps_limit=args.fps,
        loop=args.loop,
        use_vlm=args.vlm
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
            pipeline.export_results(args.export, append=args.append)


if __name__ == "__main__":
    main()
