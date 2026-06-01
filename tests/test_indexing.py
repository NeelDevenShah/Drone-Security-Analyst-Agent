"""
Unit tests for Frame Indexer
"""
import pytest
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, '/home/neel/Desktop/flytbaseAI')

from src.frame_indexer import FrameIndexer


@pytest.fixture
def test_db():
    """Create a test database"""
    test_path = "/tmp/test_frames.db"
    if os.path.exists(test_path):
        os.remove(test_path)
    
    indexer = FrameIndexer(test_path)
    yield indexer
    
    # Cleanup
    indexer.close()
    if os.path.exists(test_path):
        os.remove(test_path)


def test_store_frame(test_db):
    """Test storing a frame"""
    result = test_db.store_frame(
        frame_id=1,
        timestamp="2026-06-13 12:00:00",
        location="Main Gate",
        description="Blue truck at gate",
        objects=["truck", "blue"],
        activity_type="vehicle",
        threat_score=3
    )
    
    assert result > 0
    assert test_db.get_frame_count() == 1


def test_store_alert(test_db):
    """Test storing an alert"""
    # First store a frame
    test_db.store_frame(
        frame_id=1,
        timestamp="2026-06-13 12:00:00",
        location="Main Gate",
        description="Test",
        objects=["truck"],
        activity_type="vehicle"
    )
    
    # Then store alert
    result = test_db.store_alert(
        frame_id=1,
        alert_type="vehicle_detected",
        severity="LOW",
        threat_score=2,
        message="Vehicle detected at gate"
    )
    
    assert result > 0
    assert test_db.get_alert_count() == 1


def test_query_by_timestamp_range(test_db):
    """Test temporal queries"""
    # Store frames
    test_db.store_frame(1, "2026-06-13 10:00:00", "Gate", "Frame 1", ["truck"], "vehicle")
    test_db.store_frame(2, "2026-06-13 12:00:00", "Gate", "Frame 2", ["car"], "vehicle")
    test_db.store_frame(3, "2026-06-13 15:00:00", "Gate", "Frame 3", ["person"], "person")
    
    # Query range
    results = test_db.query_by_timestamp_range("2026-06-13 10:00:00", "2026-06-13 12:00:00")
    assert len(results) == 2


def test_query_by_location(test_db):
    """Test location queries"""
    test_db.store_frame(1, "2026-06-13 10:00:00", "Gate", "Frame 1", ["truck"], "vehicle")
    test_db.store_frame(2, "2026-06-13 12:00:00", "Garage", "Frame 2", ["car"], "vehicle")
    
    results = test_db.query_by_location("Gate")
    assert len(results) == 1
    assert results[0]['location'] == "Gate"


def test_query_by_activity_type(test_db):
    """Test activity type queries"""
    test_db.store_frame(1, "2026-06-13 10:00:00", "Gate", "F1", ["truck"], "vehicle")
    test_db.store_frame(2, "2026-06-13 12:00:00", "Gate", "F2", ["person"], "person")
    
    results = test_db.query_by_activity_type("vehicle")
    assert len(results) == 1


def test_query_by_object(test_db):
    """Test object keyword queries"""
    test_db.store_frame(1, "2026-06-13 10:00:00", "Gate", "F1", ["blue", "truck"], "vehicle")
    test_db.store_frame(2, "2026-06-13 12:00:00", "Gate", "F2", ["car"], "vehicle")
    
    results = test_db.query_by_object("truck")
    assert len(results) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
