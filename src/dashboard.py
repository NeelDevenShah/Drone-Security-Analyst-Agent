"""
Streamlit Dashboard: Interactive UI for security monitoring
Displays frame analysis, alerts, and allows querying the frame index
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# Import our components
from frame_indexer import FrameIndexer
from alert_engine import AlertEngine
from agent import SecurityAnalystAgent


def load_from_results_json(path: str):
    """
    Load pipeline output from a results.json (or simulated_frames.json) file.

    Handles two formats:
      - New pipeline format: {"summary": {...}, "frames": [...], "all_alerts": [...]}
      - Old flat-list format: [{"frame_id": ..., ...}, ...]
    
    Returns a normalised dict {"frames": [...], "all_alerts": [...], "summary": {...}}
    or None if the file does not exist.
    """
    results_file = Path(path)
    if not results_file.exists():
        return None
    with open(results_file) as f:
        data = json.load(f)
    if isinstance(data, list):
        # Old simulated_frames.json – flat list of frame dicts
        return {"frames": data, "all_alerts": [], "summary": {}}
    # New results.json from live_pipeline.export_results()
    return {
        "frames":     data.get("frames", []),
        "all_alerts": data.get("all_alerts", []),
        "summary":    data.get("summary", {}),
    }


def import_results_into_agent(agent, results: dict) -> dict:
    """
    Import frames and alerts from a pre-computed results dict into the agent's
    indexer WITHOUT re-running VLM or alert analysis (the JSON already has them).
    Returns a session-compatible results dict.
    """
    from config import PIPELINE_CONFIG
    indexer = agent.indexer
    frames = results["frames"]

    # ── CRITICAL: wipe stale data from previous runs first ───────────────────
    indexer.clear_all()

    imported_frames = 0
    imported_alerts = 0
    frame_image_paths = {}  # frame_id → image file path

    for frame in frames:
        fid = frame.get("frame_id")
        if fid is None:
            continue

        # Track saved image path (None if the frame wasn't sampled/saved)
        img_path = frame.get("image_path")
        if img_path:
            frame_image_paths[fid] = img_path

        indexer.store_frame(
            frame_id=fid,
            timestamp=frame.get("timestamp", ""),
            location=frame.get("location", PIPELINE_CONFIG.default_location),
            description=frame.get("description", ""),
            objects=frame.get("objects", []),
            activity_type=frame.get("activity_type", "empty"),
            threat_score=0,
            telemetry=frame.get("telemetry"),
        )
        imported_frames += 1

        # Import per-frame alerts (embedded in the frame record)
        for alert in frame.get("alerts", []):
            try:
                indexer.store_alert(
                    frame_id=fid,
                    alert_type=alert.get("alert_type", "unknown"),
                    severity=alert.get("severity", "LOW"),
                    threat_score=alert.get("threat_score", 0),
                    message=alert.get("message", ""),
                )
                imported_alerts += 1
            except Exception:
                pass

    # Persist image path map in session state for the UI to use
    import streamlit as st
    st.session_state.frame_image_paths = frame_image_paths

    # Build session results compatible with the rest of the dashboard
    loaded_alerts = [
        {
            "timestamp":    a.get("timestamp", ""),
            "location":     a.get("location", ""),
            "severity":     a.get("severity", "LOW"),
            "message":      a.get("message", ""),
            "alert_type":   a.get("alert_type", ""),
            "threat_score": a.get("threat_score", 0),
            "frame_id":     frame.get("frame_id"),
            "frame_image":  a.get("frame_image"),
        }
        for frame in frames for a in frame.get("alerts", [])
    ]

    summary_obj = results.get("summary", {})
    return {
        "frames_processed": imported_frames,
        "alerts_generated": loaded_alerts,
        "patterns_detected": [],
        "summary": (
            summary_obj.get("summary", str(summary_obj))
            if isinstance(summary_obj, dict) else str(summary_obj)
        ),
    }




def initialize_session_state():
    """Initialize Streamlit session state"""
    if 'agent' not in st.session_state:
        st.session_state.agent = SecurityAnalystAgent()
    if 'frames_processed' not in st.session_state:
        st.session_state.frames_processed = False
    if 'results_json_path' not in st.session_state:
        st.session_state.results_json_path = "results.json"


def main():
    """Main dashboard application"""
    st.set_page_config(
        page_title="Drone Security Analyst",
        page_icon="🚁",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("🚁 Drone Security Analyst Agent")
    st.markdown("Real-time security monitoring and threat detection for property surveillance")
    
    # Sidebar controls
    with st.sidebar:
        st.header("Controls")

        # ── results.json loader ──────────────────────────────────────────────
        st.subheader("Load Pipeline Results")
        results_path = st.text_input(
            "results.json path",
            value=st.session_state.results_json_path,
            key="results_path_input",
            help="Path to the results.json exported by the pipeline"
        )
        st.session_state.results_json_path = results_path

        if st.button("📂 Load from results.json", key="load_results_btn"):
            with st.spinner("Loading results.json …"):
                data = load_from_results_json(results_path)
                if data is None:
                    st.error(f"File not found: {results_path}")
                elif not data["frames"]:
                    st.error("results.json contains no frames.")
                else:
                    results = import_results_into_agent(st.session_state.agent, data)
                    st.session_state.results = results
                    st.session_state.frames_processed = True
                    st.success(
                        f"✓ Loaded {results['frames_processed']} frames "
                        f"and {len(results['alerts_generated'])} alerts from {results_path}"
                    )

        st.markdown("---")

        # ── simulated data fallback ──────────────────────────────────────────
        if st.button("🔄 Load Simulated Frames", key="process_btn"):
            with st.spinner("Processing simulated frames..."):
                sim_file = Path("/home/neel/Desktop/flytbaseAI/data/simulated_frames.json")
                data = load_from_results_json(str(sim_file))
                if data is None:
                    # Generate synthetic data on the fly
                    try:
                        from data_simulator import DataSimulator
                        simulator = DataSimulator()
                        raw_frames = simulator.generate_realistic_scenario()
                        from dataclasses import asdict
                        data = {"frames": [asdict(f) for f in raw_frames], "all_alerts": [], "summary": {}}
                    except Exception as e:
                        st.error(f"Could not generate simulated data: {e}")
                        data = None
                if data and data["frames"]:
                    results = import_results_into_agent(st.session_state.agent, data)
                    st.session_state.results = results
                    st.session_state.frames_processed = True
                    st.success(f"✓ Processed {results['frames_processed']} frames")
                else:
                    st.error("No frames to process")
        
        st.markdown("---")
        
        # View options
        view_mode = st.radio(
            "Select View",
            ["Dashboard", "Frames", "Alerts", "Query", "Q&A", "Summary Report"]
        )
    
    # Main content area
    if not st.session_state.frames_processed:
        st.info("👈 Click 'Load & Process Frames' in the sidebar to start")
        return
    
    results = st.session_state.results
    
    if view_mode == "Dashboard":
        show_dashboard(results)
    elif view_mode == "Frames":
        show_frames()
    elif view_mode == "Alerts":
        show_alerts()
    elif view_mode == "Query":
        show_query_interface()
    elif view_mode == "Q&A":
        show_qa_interface()
    elif view_mode == "Summary Report":
        show_summary_report(results)


def show_dashboard(results):
    """Display main dashboard with key metrics"""
    st.header("📊 Dashboard")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Frames Processed", results['frames_processed'])
    
    with col2:
        st.metric("Total Alerts", len(results['alerts_generated']))
    
    with col3:
        high_risk = len([a for a in results['alerts_generated'] if a['severity'] in ['HIGH', 'CRITICAL']])
        st.metric("🔴 High Risk", high_risk)
    
    with col4:
        indexer = FrameIndexer()
        frame_count = indexer.get_frame_count()
        indexer.close()
        st.metric("Indexed Frames", frame_count)
    
    st.markdown("---")
    
    # Alerts by severity
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Alerts by Severity")
        
        severity_counts = {
            "CRITICAL": len([a for a in results['alerts_generated'] if a['severity'] == 'CRITICAL']),
            "HIGH": len([a for a in results['alerts_generated'] if a['severity'] == 'HIGH']),
            "MEDIUM": len([a for a in results['alerts_generated'] if a['severity'] == 'MEDIUM']),
            "LOW": len([a for a in results['alerts_generated'] if a['severity'] == 'LOW']),
        }
        
        df_severity = pd.DataFrame({
            'Severity': list(severity_counts.keys()),
            'Count': list(severity_counts.values()),
            'Color': ['#FF0000', '#FF6B6B', '#FFA500', '#FFFF00']
        })
        
        st.bar_chart(
            df_severity.set_index('Severity')['Count'],
            use_container_width=True
        )
    
    with col2:
        st.subheader("Recent Alerts")
        
        if results['alerts_generated']:
            for alert in results['alerts_generated'][:5]:
                severity = alert['severity']
                color = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟠',
                    'MEDIUM': '🟡',
                    'LOW': '🟢'
                }.get(severity, '⚪')
                
                st.write(f"{color} **{alert['severity']}** - {alert['message']}")
        else:
            st.info("No alerts generated")
    
    st.markdown("---")
    
    # Timeline view
    st.subheader("Alert Timeline")
    
    if results['alerts_generated']:
        timeline_data = []
        for alert in results['alerts_generated']:
            timeline_data.append({
                'Time': alert['timestamp'],
                'Severity': alert['severity'],
                'Message': alert['message']
            })
        
        df_timeline = pd.DataFrame(timeline_data)
        st.dataframe(df_timeline, use_container_width=True, hide_index=True)
    else:
        st.info("No alerts to display")


def show_frames():
    """Display all processed frames with thumbnails"""
    st.header("📹 Frame Index")

    indexer = FrameIndexer()
    frames = indexer.get_frames_for_shift_summary()
    indexer.close()

    frame_image_paths = getattr(st.session_state, "frame_image_paths", {})

    if frames:
        # Summary table
        df_frames = pd.DataFrame([
            {
                'ID': f['frame_id'],
                'Time': f['timestamp'],
                'Location': f['location'],
                'Activity': f['activity_type'],
                'Description': f['description'][:60] + "..." if len(f['description']) > 60 else f['description'],
                'Objects': ', '.join(f['objects']),
                'Has Image': '✅' if frame_image_paths.get(f['frame_id']) else '—',
            }
            for f in frames
        ])
        st.dataframe(df_frames, use_container_width=True, hide_index=True)

        # Thumbnail gallery for frames that have saved images
        saved = [(f, frame_image_paths[f['frame_id']]) for f in frames if frame_image_paths.get(f['frame_id'])]
        if saved:
            st.markdown("---")
            st.subheader(f"📸 Saved Frame Images ({len(saved)} frames)")
            cols = st.columns(3)
            for idx, (frame, img_path) in enumerate(saved):
                from pathlib import Path as _Path
                with cols[idx % 3]:
                    if _Path(img_path).exists():
                        st.image(
                            img_path,
                            caption=f"#{frame['frame_id']} · {frame['timestamp'][:19]}\n{frame['location']} · {frame['activity_type']}",
                            use_container_width=True
                        )
                    else:
                        st.caption(f"Frame #{frame['frame_id']}: image missing")
        else:
            st.info("No frame images were saved during this pipeline run (only alert frames and sampled frames are saved).")
    else:
        st.info("No frames indexed yet")




def show_alerts():
    """Display all alerts with frame image proof"""
    st.header("🚨 All Alerts")

    indexer = FrameIndexer()
    all_alerts = indexer.get_all_alerts()
    indexer.close()

    # Image path lookup from session state (populated when results.json is loaded)
    frame_image_paths = getattr(st.session_state, "frame_image_paths", {})

    if all_alerts:
        col1, col2 = st.columns([3, 1])
        with col2:
            filter_severity = st.multiselect(
                "Filter by Severity",
                ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                default=["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            )
        with col1:
            st.write("")

        filtered_alerts = [a for a in all_alerts if a['severity'] in filter_severity]

        severity_icon = {
            'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢'
        }

        for alert in filtered_alerts:
            icon = severity_icon.get(alert['severity'], '⚪')
            with st.expander(f"{icon} {alert['severity']} — {alert['timestamp']}"):
                col_info, col_img = st.columns([2, 1])
                with col_info:
                    st.write(f"**Location**: {alert.get('location', 'N/A')}")
                    st.write(f"**Type**: {alert.get('alert_type', 'N/A')}")
                    st.write(f"**Threat Score**: {alert.get('threat_score', '?')}/10")
                    st.write(f"**Message**: {alert['message']}")
                    if alert.get('description'):
                        st.caption(f"Frame: {alert['description'][:120]}")
                with col_img:
                    fid = alert.get('frame_id')
                    img_path = frame_image_paths.get(fid) if fid else None
                    if img_path:
                        from pathlib import Path as _Path
                        if _Path(img_path).exists():
                            st.image(img_path, caption=f"Frame #{fid}", use_container_width=True)
                        else:
                            st.caption(f"📷 Image not found:\n{img_path}")
                    else:
                        st.caption("📷 No frame image saved for this alert")
    else:
        st.info("No alerts generated")



def show_query_interface():
    """Interactive query interface"""
    st.header("🔍 Query Frames")
    
    query_type = st.selectbox(
        "Query Type",
        ["By Activity Type", "By Location", "By Time Range", "By Object Keyword"]
    )
    
    indexer = FrameIndexer()
    
    if query_type == "By Activity Type":
        activity = st.selectbox("Select Activity", ["vehicle", "person", "vehicle+person", "empty"])
        results = indexer.query_by_activity_type(activity)
        st.write(f"Found {len(results)} frames with activity: {activity}")
    
    elif query_type == "By Location":
        location = st.selectbox(
            "Select Location",
            ["Main Gate", "Garage", "Perimeter Fence", "Parking Lot"]
        )
        results = indexer.query_by_location(location)
        st.write(f"Found {len(results)} frames at location: {location}")
    
    elif query_type == "By Time Range":
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.text_input("Start Time (YYYY-MM-DD HH:MM:SS)", "2026-06-13 00:00:00")
        with col2:
            end_time = st.text_input("End Time (YYYY-MM-DD HH:MM:SS)", "2026-06-13 23:59:59")
        
        if st.button("Query"):
            results = indexer.query_by_timestamp_range(start_time, end_time)
            st.write(f"Found {len(results)} frames in time range")
    
    elif query_type == "By Object Keyword":
        keyword = st.text_input("Enter object keyword (e.g., 'truck', 'person')")
        if st.button("Search"):
            results = indexer.query_by_object(keyword)
            st.write(f"Found {len(results)} frames containing '{keyword}'")
    
    # Display results
    if 'results' in locals() and results:
        enriched_results = [st.session_state.agent._enrich_frame_with_alert_context(r) for r in results]
        st.subheader("Query Results")
        df_results = pd.DataFrame([
            {
                'Time': r['timestamp'],
                'Location': r['location'],
                'Activity': r['activity_type'],
                'Description': r['description'][:40] + "...",
                'Objects': ', '.join(r['objects']),
                'Alerts': ', '.join([f"{a['severity']}: {a['message']}" for a in r.get('alert_context', [])]) if r.get('alert_context') else "None"
            }
            for r in enriched_results
        ])
        st.dataframe(df_results, use_container_width=True, hide_index=True)
    elif 'results' in locals():
        st.info("No results found")
    
    indexer.close()


def show_qa_interface():
    """Q&A interface with cited source frames and images"""
    st.header("❓ Ask Questions About the Shift")

    agent = st.session_state.agent
    frame_image_paths = getattr(st.session_state, "frame_image_paths", {})

    st.write("Examples:")
    st.write("- How many vehicles detected?")
    st.write("- What about the blue truck?")
    st.write("- What objects were in the video?")
    st.write("- How many people detected?")

    question = st.text_input("Ask a question:")

    if question:
        with st.spinner("Searching security logs…"):
            cited_frames = agent.query_frame_index(question)
            answer = agent.answer_question(question)

        st.markdown("---")

        # ── Answer ──────────────────────────────────────────────────────────
        st.subheader("Answer")
        st.write(answer)

        # ── Citations with frame images ──────────────────────────────────────
        if cited_frames:
            st.markdown("---")
            st.subheader(f"📎 Source Frames ({len(cited_frames)} citations)")
            st.caption("These are the frames the answer was derived from.")

            for idx, frame in enumerate(cited_frames):
                fid = frame.get("frame_id")
                img_path = frame_image_paths.get(fid)
                alerts = frame.get("alert_context", [])

                with st.expander(
                    f"Citation {idx + 1} — Frame #{fid} · {frame.get('timestamp', '')[:19]} · {frame.get('location', '')}",
                    expanded=(idx == 0)
                ):
                    col_img, col_meta = st.columns([1, 2])

                    with col_img:
                        if img_path:
                            from pathlib import Path as _Path
                            if _Path(img_path).exists():
                                st.image(img_path, caption=f"Frame #{fid}", use_container_width=True)
                            else:
                                st.caption(f"📷 Image file missing:\n`{img_path}`")
                        else:
                            st.info("📷 No image saved for this frame")

                    with col_meta:
                        st.markdown(f"**📍 Location:** {frame.get('location', 'N/A')}")
                        st.markdown(f"**🏃 Activity:** {frame.get('activity_type', 'N/A')}")
                        st.markdown(f"**🔍 Objects:** {', '.join(frame.get('objects', [])) or 'none'}")
                        st.markdown("**📝 Description:**")
                        st.write(frame.get('description', ''))

                        if alerts:
                            st.markdown("**🚨 Alerts on this frame:**")
                            for a in alerts:
                                sev_icon = {
                                    'CRITICAL': '🔴', 'HIGH': '🟠',
                                    'MEDIUM': '🟡', 'LOW': '🟢'
                                }.get(a.get('severity', ''), '⚪')
                                st.markdown(
                                    f"{sev_icon} **{a.get('severity')}** — "
                                    f"{a.get('message', '')} "
                                    f"*(threat: {a.get('threat_score', '?')}/10)*"
                                )
        else:
            st.info("No matching frames found for this query.")



def show_summary_report(results):
    """Display comprehensive summary report"""
    st.header("📋 Shift Summary Report")
    
    agent = st.session_state.agent
    summary = agent.get_shift_summary()
    
    st.text(summary)
    
    # Export option
    if st.button("📥 Download Summary as Text"):
        st.download_button(
            label="Download",
            data=summary,
            file_name=f"security_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )


if __name__ == "__main__":
    main()
