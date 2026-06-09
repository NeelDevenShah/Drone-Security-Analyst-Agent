#!/usr/bin/env python
"""
Main Entry Point: Drone Security Analyst Agent
Orchestrates the full pipeline from data generation to analysis
"""

import sys
import os
from pathlib import Path
from dataclasses import asdict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_simulator import DataSimulator
from agent import SecurityAnalystAgent
from config import SIMULATOR_CONFIG


def main():
    """Main execution pipeline"""
    
    print("=" * 70)
    print("🚁  DRONE SECURITY ANALYST AGENT - Main Pipeline")
    print("=" * 70)
    
    # Step 1: Generate simulated data
    print("\n[1/4] Generating simulated frame data...")
    simulator = DataSimulator()
    frames = simulator.generate_realistic_scenario()
    simulator.save_to_file(SIMULATOR_CONFIG.output_path)
    print(f"✓ Generated {len(frames)} frames")
    
    # Step 2: Initialize agent
    print("\n[2/4] Initializing Security Analyst Agent...")
    agent = SecurityAnalystAgent()
    print("✓ Agent initialized with all tools")
    
    # Step 3: Process frames
    print("\n[3/4] Processing frames through pipeline...")
    frames_dict = [asdict(f) for f in frames]
    results = agent.process_frames(frames_dict)
    print(f"✓ Processed {results['frames_processed']} frames")
    print(f"✓ Generated {len(results['alerts_generated'])} alerts")
    
    # Step 4: Display results
    print("\n[4/4] Generating reports and summary...")
    print("\n" + "=" * 70)
    print("SHIFT SUMMARY REPORT")
    print("=" * 70)
    print(results['summary'])
    
    # Display sample alerts
    if results['alerts_generated']:
        print("\n" + "=" * 70)
        print(f"ALERTS GENERATED ({len(results['alerts_generated'])} total)")
        print("=" * 70)
        for i, alert in enumerate(results['alerts_generated'][:5], 1):
            severity_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(alert['severity'], '⚪')
            
            print(f"\n{i}. {severity_emoji} {alert['severity']}")
            print(f"   Location: {alert['location']}")
            print(f"   Message: {alert['message']}")
    
    # Display Q&A examples
    print("\n" + "=" * 70)
    print("Q&A EXAMPLES")
    print("=" * 70)
    
    questions = [
        "How many vehicles detected?",
        "What about the blue truck?",
        "What objects were in the video?",
        "How many people detected?"
    ]
    
    for q in questions:
        answer = agent.answer_question(q)
        print(f"\nQ: {q}")
        print(f"A: {answer}")
    
    # Database statistics
    print("\n" + "=" * 70)
    print("DATABASE STATISTICS")
    print("=" * 70)
    indexer = agent.indexer
    print(f"Total Frames Indexed: {indexer.get_frame_count()}")
    print(f"Total Alerts Stored: {indexer.get_alert_count()}")
    
    # Display database location
    print(f"Database Location: {indexer.db_path}")
    print(f"Simulated Frames: {SIMULATOR_CONFIG.output_path}")
    
    # Cleanup
    agent.close()
    
    print("\n" + "=" * 70)
    print("✓ Pipeline Complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Run dashboard: streamlit run src/dashboard.py")
    print("  2. Run tests: pytest tests/ -v")
    print("  3. Review frame data: less data/simulated_frames.json")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
