"""
Unit tests for Agent functionality
"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent import SecurityAnalystAgent
from data_simulator import DataSimulator
from dataclasses import asdict


@pytest.fixture
def agent():
    """Create agent instance"""
    agent = SecurityAnalystAgent(db_path="/tmp/test_agent.db", enable_vlm=False)
    yield agent
    agent.close()


@pytest.fixture
def test_frames():
    """Generate test frames"""
    simulator = DataSimulator()
    return [asdict(f) for f in simulator.generate_realistic_scenario()]


def test_agent_initialization(agent):
    """Test agent initializes correctly"""
    assert agent.context.frames_processed == 0
    assert agent.context.total_alerts == 0
    assert agent.indexer is not None
    assert agent.alert_engine is not None


def test_process_frames(agent, test_frames):
    """Test processing frames through agent"""
    results = agent.process_frames(test_frames)
    
    assert results['frames_processed'] == len(test_frames)
    assert len(results['alerts_generated']) > 0
    assert 'summary' in results


def test_query_frame_index(agent, test_frames):
    """Test frame index queries"""
    agent.process_frames(test_frames)
    
    # Query vehicles
    vehicles = agent.query_frame_index("Show all truck events")
    assert len(vehicles) > 0
    
    # Query people
    people = agent.query_frame_index("Show all people events")
    assert len(people) > 0


def test_answer_question(agent, test_frames):
    """Test Q&A functionality"""
    agent.process_frames(test_frames)
    
    # Test various questions
    answer1 = agent.answer_question("How many vehicles detected?")
    assert "vehicle" in answer1.lower()
    
    answer2 = agent.answer_question("What objects were in the video?")
    assert "truck" in answer2.lower() or "vehicle" in answer2.lower()
    
    answer3 = agent.answer_question("How many alerts were generated?")
    assert "alert" in answer3.lower()


def test_shift_summary(agent, test_frames):
    """Test shift summary generation"""
    agent.process_frames(test_frames)
    summary = agent.get_shift_summary()
    
    assert "SHIFT SUMMARY REPORT" in summary
    assert "Frames Processed" in summary
    assert "Total Alerts" in summary


def test_pattern_detection(agent, test_frames):
    """Test pattern detection"""
    agent.process_frames(test_frames)
    patterns = agent._detect_patterns()
    
    assert patterns['total_frames'] > 0
    assert patterns['total_alerts'] > 0
    assert isinstance(patterns['vehicles'], list)


def test_context_persistence(agent, test_frames):
    """Test that context persists across operations"""
    agent.process_frames(test_frames)
    
    assert agent.context.frames_processed == len(test_frames)
    assert agent.context.total_alerts > 0
    assert len(agent.context.vehicles_detected) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
