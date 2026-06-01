"""
Unit tests for Alert Engine
"""
import pytest
import sys

# Add src to path
sys.path.insert(0, '/home/neel/Desktop/flytbaseAI')

from src.alert_engine import AlertEngine


@pytest.fixture
def alert_engine():
    """Create alert engine instance"""
    return AlertEngine()


def test_loitering_midnight_alert(alert_engine):
    """Test midnight loitering alert"""
    frame = {
        'frame_id': 1,
        'timestamp': '2026-06-13 00:01:00',
        'location': 'Main Gate',
        'description': 'Person loitering',
        'objects': ['person'],
        'activity_type': 'person'
    }
    
    alerts = alert_engine.analyze_frame(frame)
    
    assert len(alerts) > 0
    loitering_alert = [a for a in alerts if 'loitering' in a.alert_type.lower()]
    assert len(loitering_alert) > 0
    assert loitering_alert[0].severity == "HIGH"


def test_perimeter_breach_alert(alert_engine):
    """Test perimeter breach alert"""
    frame = {
        'frame_id': 1,
        'timestamp': '2026-06-13 10:00:00',
        'location': 'Perimeter Fence',
        'description': 'Person at fence',
        'objects': ['person'],
        'activity_type': 'person'
    }
    
    alerts = alert_engine.analyze_frame(frame)
    
    perimeter_alert = [a for a in alerts if 'perimeter' in a.alert_type.lower()]
    assert len(perimeter_alert) > 0
    assert perimeter_alert[0].severity == "MEDIUM"


def test_night_vehicle_alert(alert_engine):
    """Test night vehicle activity alert"""
    frame = {
        'frame_id': 1,
        'timestamp': '2026-06-13 02:00:00',
        'location': 'Gate',
        'description': 'Vehicle at gate',
        'objects': ['truck'],
        'activity_type': 'vehicle'
    }
    
    alerts = alert_engine.analyze_frame(frame)
    
    night_alerts = [a for a in alerts if 'night' in a.alert_type.lower()]
    assert len(night_alerts) > 0


def test_repeat_visit_detection(alert_engine):
    """Test repeat vehicle visit detection"""
    frame1 = {
        'frame_id': 1,
        'timestamp': '2026-06-13 08:00:00',
        'location': 'Main Gate',
        'description': 'Blue Ford F150 entering',
        'objects': ['blue', 'Ford', 'F150'],
        'activity_type': 'vehicle'
    }
    
    frame2 = {
        'frame_id': 2,
        'timestamp': '2026-06-13 23:45:00',
        'location': 'Main Gate',
        'description': 'Blue Ford F150 entering again',
        'objects': ['blue', 'Ford', 'F150'],
        'activity_type': 'vehicle'
    }
    
    # Analyze first frame
    alert_engine.analyze_frame(frame1)
    
    # Analyze second frame with history
    alerts = alert_engine.analyze_frame(frame2, [frame1])
    
    # Should detect repeat visit
    repeat_alerts = [a for a in alerts if 'repeat' in a.alert_type.lower()]
    assert len(repeat_alerts) > 0


def test_no_alert_for_daytime_vehicle(alert_engine):
    """Test that daytime vehicle activity doesn't trigger alerts"""
    frame = {
        'frame_id': 1,
        'timestamp': '2026-06-13 12:00:00',
        'location': 'Gate',
        'description': 'Vehicle at gate',
        'objects': ['truck'],
        'activity_type': 'vehicle'
    }
    
    alerts = alert_engine.analyze_frame(frame)
    
    # Should have 0 alerts for normal daytime vehicle activity
    assert len(alerts) == 0


def test_alert_summary_report(alert_engine):
    """Test alert summary report generation"""
    frame = {
        'frame_id': 1,
        'timestamp': '2026-06-13 00:01:00',
        'location': 'Main Gate',
        'description': 'Person loitering',
        'objects': ['person'],
        'activity_type': 'person'
    }
    
    alert_engine.analyze_frame(frame)
    summary = alert_engine.get_summary_report()
    
    assert 'Alert Summary' in summary
    assert 'HIGH' in summary or 'high' in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
