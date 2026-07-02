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


def load_simulated_data():
    """Load simulated frames from JSON, generating them if they don't exist"""
    frames_file = Path("/home/neel/Desktop/flytbaseAI/data/simulated_frames.json")
    if not frames_file.exists():
        try:
            from data_simulator import DataSimulator
            simulator = DataSimulator()
            simulator.generate_realistic_scenario()
            frames_file.parent.mkdir(parents=True, exist_ok=True)
            simulator.save_to_file(str(frames_file))
        except Exception as e:
            st.error(f"Failed to generate simulated frames: {e}")
            
    if frames_file.exists():
        with open(frames_file) as f:
            return json.load(f)
    return []


def initialize_session_state():
    """Initialize Streamlit session state and auto-process frames if not done yet"""
    if 'agent' not in st.session_state:
        st.session_state.agent = SecurityAnalystAgent()
        
    if 'frames_processed' not in st.session_state or not st.session_state.frames_processed:
        frames = load_simulated_data()
        if frames:
            db_frames_count = st.session_state.agent.indexer.get_frame_count()
            if db_frames_count > 0:
                # Database already has data; load directly from indexer
                st.session_state.results = {
                    "frames_processed": db_frames_count,
                    "alerts_generated": [
                        {
                            "timestamp": a["timestamp"],
                            "location": a["location"],
                            "severity": a["severity"],
                            "message": a["message"]
                        }
                        for a in st.session_state.agent.indexer.get_all_alerts()
                    ],
                    "patterns_detected": [],
                    "summary": st.session_state.agent.get_shift_summary()
                }
                st.session_state.frames_processed = True
            else:
                # Ingest and process simulated frames
                results = st.session_state.agent.process_frames(frames)
                st.session_state.results = results
                st.session_state.frames_processed = True


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
        
        if st.button("🔄 Load & Process Frames", key="process_btn"):
            with st.spinner("Processing frames..."):
                frames = load_simulated_data()
                if frames:
                    results = st.session_state.agent.process_frames(frames)
                    st.session_state.frames_processed = True
                    st.session_state.results = results
                    st.success(f"✓ Processed {results['frames_processed']} frames")
                else:
                    st.error("No simulated frames found")
        
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
    """Display all processed frames"""
    st.header("📹 Frame Index")
    
    indexer = FrameIndexer()
    frames = indexer.get_frames_for_shift_summary()
    indexer.close()
    
    if frames:
        # Convert to dataframe
        df_frames = pd.DataFrame([
            {
                'ID': f['frame_id'],
                'Time': f['timestamp'],
                'Location': f['location'],
                'Activity': f['activity_type'],
                'Description': f['description'][:50] + "..." if len(f['description']) > 50 else f['description'],
                'Objects': ', '.join(f['objects'])
            }
            for f in frames
        ])
        
        st.dataframe(df_frames, use_container_width=True, hide_index=True)
    else:
        st.info("No frames indexed yet")


def show_alerts():
    """Display all alerts"""
    st.header("🚨 All Alerts")
    
    indexer = FrameIndexer()
    all_alerts = indexer.get_all_alerts()
    indexer.close()
    
    if all_alerts:
        # Filter by severity
        col1, col2 = st.columns([3, 1])
        
        with col2:
            filter_severity = st.multiselect(
                "Filter by Severity",
                ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                default=["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            )
        
        with col1:
            st.write("")
        
        # Display alerts
        filtered_alerts = [a for a in all_alerts if a['severity'] in filter_severity]
        
        for alert in filtered_alerts:
            severity_color = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }
            
            with st.expander(f"{severity_color[alert['severity']]} {alert['severity']} - {alert['timestamp']}"):
                st.write(f"**Location**: {alert['location']}")
                st.write(f"**Type**: {alert['alert_type']}")
                st.write(f"**Threat Score**: {alert['threat_score']}/10")
                st.write(f"**Message**: {alert['message']}")
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
    """Q&A interface for user questions"""
    st.header("❓ Ask Questions About the Shift")
    
    agent = st.session_state.agent
    
    st.write("Examples:")
    st.write("- How many vehicles detected?")
    st.write("- What about the blue truck?")
    st.write("- What objects were in the video?")
    st.write("- How many people detected?")
    
    question = st.text_input("Ask a question:")
    
    if question:
        answer = agent.answer_question(question)
        
        st.markdown("---")
        st.subheader("Answer")
        st.write(answer)


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
