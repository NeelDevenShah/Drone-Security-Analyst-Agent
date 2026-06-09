"""
Frame Indexer: Stores frames with metadata and embeddings for semantic search
Hybrid approach: SQLite for metadata + ChromaDB for semantic embeddings
"""
import sqlite3
import json
import threading
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

try:
    from .config import DATABASE_CONFIG
except ImportError:
    from config import DATABASE_CONFIG


class FrameIndexer:
    """
    Hybrid indexing system for drone security frames.
    
    Storage Strategy:
    - SQLite: Metadata (timestamp, location, objects, description, threat_score)
    - ChromaDB: Semantic embeddings for similarity search (optional enhancement)
    """

    def __init__(self, db_path: str = DATABASE_CONFIG.db_path):
        """Initialize the frame indexing database"""
        self.db_path = db_path
        self.conn = None
        self.db_lock = threading.RLock()
        self._initialize_database()

    def _initialize_database(self):
        """Create SQLite tables for frame storage"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        with self.db_lock:
            cursor = self.conn.cursor()

            # Create frames table with metadata
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS frames (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    frame_id INTEGER UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT NOT NULL,
                    objects TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    threat_score INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    telemetry TEXT
                )
            ''')

            # Create alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    frame_id INTEGER NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    threat_score INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (frame_id) REFERENCES frames(frame_id)
                )
            ''')

            # Create index on timestamp for efficient temporal queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON frames(timestamp)
            ''')

            # Create index on location for location queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_location ON frames(location)
            ''')

            # Create index on activity_type for activity queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_activity_type ON frames(activity_type)
            ''')

            self.conn.commit()
        print(f"✓ Initialized database at {self.db_path}")

    def store_frame(
        self,
        frame_id: int,
        timestamp: str,
        location: str,
        description: str,
        objects: List[str],
        activity_type: str,
        threat_score: int = 0,
        telemetry: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store a single frame in the database
        
        Args:
            frame_id: Unique frame identifier
            timestamp: ISO format timestamp
            location: Location/area where frame was captured
            description: VLM-generated description
            objects: List of detected objects
            activity_type: Type of activity (vehicle, person, etc.)
            threat_score: Threat level 0-10
            telemetry: Optional drone telemetry data
        
        Returns:
            Database ID of inserted record
        """
        objects_json = json.dumps(objects)
        telemetry_json = json.dumps(telemetry) if telemetry else None

        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO frames 
                (frame_id, timestamp, location, description, objects, activity_type, threat_score, telemetry)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (frame_id, timestamp, location, description, objects_json, activity_type, threat_score, telemetry_json))

            self.conn.commit()
            return cursor.lastrowid

    def store_alert(
        self,
        frame_id: int,
        alert_type: str,
        severity: str,  # LOW, MEDIUM, HIGH, CRITICAL
        threat_score: int,
        message: str
    ) -> int:
        """
        Store an alert triggered by frame analysis
        
        Args:
            frame_id: ID of frame that triggered alert
            alert_type: Type of alert (loitering, repeat_visit, etc.)
            severity: Alert severity level
            threat_score: Threat score 1-10
            message: Human-readable alert message
        
        Returns:
            Database ID of inserted alert
        """
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO alerts (frame_id, alert_type, severity, threat_score, message)
                VALUES (?, ?, ?, ?, ?)
            ''', (frame_id, alert_type, severity, threat_score, message))

            self.conn.commit()
            return cursor.lastrowid

    def query_by_timestamp_range(
        self,
        start_time: str,
        end_time: str
    ) -> List[Dict[str, Any]]:
        """
        Query frames within a time range
        
        Args:
            start_time: ISO format start timestamp
            end_time: ISO format end timestamp
        
        Returns:
            List of matching frames
        """
        with self.db_lock:
            cursor = self.conn.execute('''
                SELECT * FROM frames 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (start_time, end_time))

            return self._fetch_as_dicts(cursor)

    def query_by_location(self, location: str) -> List[Dict[str, Any]]:
        """
        Query frames by location
        
        Args:
            location: Location to filter by
        
        Returns:
            List of frames at that location
        """
        with self.db_lock:
            cursor = self.conn.execute('''
                SELECT * FROM frames 
                WHERE location = ?
                ORDER BY timestamp
            ''', (location,))

            return self._fetch_as_dicts(cursor)

    def query_by_activity_type(self, activity_type: str) -> List[Dict[str, Any]]:
        """
        Query frames by activity type
        
        Args:
            activity_type: Type of activity (vehicle, person, empty, etc.)
        
        Returns:
            List of matching frames
        """
        with self.db_lock:
            cursor = self.conn.execute('''
                SELECT * FROM frames 
                WHERE activity_type = ?
                ORDER BY timestamp
            ''', (activity_type,))

            return self._fetch_as_dicts(cursor)

    def query_by_object(self, object_keyword: str) -> List[Dict[str, Any]]:
        """
        Query frames containing a specific object keyword
        
        Args:
            object_keyword: Object to search for (e.g., "truck", "person")
        
        Returns:
            List of frames containing that object
        """
        # Since objects are stored as JSON, we need to search within the JSON
        with self.db_lock:
            cursor = self.conn.execute('''
                SELECT * FROM frames 
                WHERE objects LIKE ?
                ORDER BY timestamp
            ''', (f'%{object_keyword}%',))

            return self._fetch_as_dicts(cursor)

    def get_all_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all alerts, most recent first"""
        with self.db_lock:
            cursor = self.conn.execute('''
                SELECT a.*, f.timestamp, f.location, f.description 
                FROM alerts a
                JOIN frames f ON a.frame_id = f.frame_id
                ORDER BY a.created_at DESC
                LIMIT ?
            ''', (limit,))

            return self._fetch_as_dicts(cursor)

    def get_alerts_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Get alerts filtered by severity"""
        with self.db_lock:
            cursor = self.conn.execute('''
                SELECT a.*, f.timestamp, f.location, f.description 
                FROM alerts a
                JOIN frames f ON a.frame_id = f.frame_id
                WHERE a.severity = ?
                ORDER BY a.created_at DESC
            ''', (severity,))

            return self._fetch_as_dicts(cursor)

    def get_frame_count(self) -> int:
        """Get total number of stored frames"""
        with self.db_lock:
            cursor = self.conn.execute('SELECT COUNT(*) FROM frames')
            return cursor.fetchone()[0]

    def get_alert_count(self) -> int:
        """Get total number of alerts"""
        with self.db_lock:
            cursor = self.conn.execute('SELECT COUNT(*) FROM alerts')
            return cursor.fetchone()[0]

    def get_frames_for_shift_summary(self) -> List[Dict[str, Any]]:
        """Get all frames for generating shift summary"""
        with self.db_lock:
            cursor = self.conn.execute('SELECT * FROM frames ORDER BY timestamp')
            return self._fetch_as_dicts(cursor)

    def _fetch_as_dicts(self, cursor) -> List[Dict[str, Any]]:
        """Convert cursor results to list of dicts with column names"""
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parse JSON fields
            if 'objects' in result and isinstance(result['objects'], str):
                result['objects'] = json.loads(result['objects'])
            if 'telemetry' in result and result['telemetry']:
                result['telemetry'] = json.loads(result['telemetry'])
            results.append(result)
        return results

    def close(self):
        """Close database connection"""
        with self.db_lock:
            if self.conn:
                self.conn.close()
                self.conn = None
                print("✓ Database connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    # Test frame indexer
    indexer = FrameIndexer()
    
    # Store sample frame
    indexer.store_frame(
        frame_id=1,
        timestamp="2026-06-13 00:01:00",
        location="Main Gate",
        description="Unknown person loitering near main gate",
        objects=["person", "gate"],
        activity_type="person",
        threat_score=8
    )
    
    # Store alert
    indexer.store_alert(
        frame_id=1,
        alert_type="loitering",
        severity="HIGH",
        threat_score=8,
        message="Person loitering at main gate at midnight - HIGH RISK"
    )
    
    print(f"\n✓ Stored 1 frame and 1 alert")
    print(f"Total frames: {indexer.get_frame_count()}")
    print(f"Total alerts: {indexer.get_alert_count()}")
    
    # Test queries
    print("\nQuery test - all alerts:")
    alerts = indexer.get_all_alerts()
    for alert in alerts:
        print(f"  [{alert['timestamp']}] {alert['severity']}: {alert['message']}")
    
    indexer.close()
