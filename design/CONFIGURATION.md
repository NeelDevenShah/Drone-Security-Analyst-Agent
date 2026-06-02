# Configuration & Customization Guide

## Alert Rules Configuration

### Modifying Alert Thresholds

Edit `src/alert_engine.py` in the `_check_rules()` method:

```python
# Example: Change midnight loitering threshold
def _check_rules(self, frame):
    hour = int(frame['timestamp'].split()[1].split(':')[0])
    
    # OLD: if hour >= 23 or hour <= 2:
    # NEW: if hour >= 22 or hour <= 3:  # Expanded window
    if hour >= 22 or hour <= 3:
        if activity_type == "person":
            alert = Alert(
                # ... parameters ...
                threat_score=9  # Increased from 8
            )
```

### Available Alert Types

| Alert Type | Trigger | Severity | Threat | Configurable |
|------------|---------|----------|--------|--------------|
| `loitering_midnight` | Person at midnight | HIGH | 8 | Time window |
| `perimeter_breach` | Person at perimeter | MEDIUM | 6 | Locations |
| `night_vehicle` | Vehicle at night | LOW | 3 | Time window |
| `repeat_visit` | Same vehicle 2+ times | MEDIUM | 5 | Visit count |
| `long_dwell` | Object stationary 4hrs+ | LOW | 4 | Dwell time |

### Adding Custom Alert Rules

1. **Edit `src/alert_engine.py`**:

```python
def _check_rules(self, frame):
    # ... existing rules ...
    
    # NEW RULE: Delivery truck after hours
    if "delivery" in frame['description'].lower():
        hour = int(frame['timestamp'].split()[1].split(':')[0])
        if hour >= 20 or hour <= 6:
            alerts.append(Alert(
                frame_id=frame['frame_id'],
                alert_type="after_hours_delivery",
                severity="LOW",
                threat_score=2,
                message=f"Delivery truck at {location} after hours",
                timestamp=frame['timestamp'],
                location=frame['location']
            ))
    
    return alerts
```

2. **Test the rule**:

```bash
python -m pytest tests/test_alerts.py -v -k "delivery"
```

## VLM Configuration

### Switching VLM Models

Edit `src/agent.py` in `__init__()`:

```python
# Current: BLIP-2 (7GB, local)
self.vlm_processor = VLMProcessor(model_name="blip2")

# Alternative options:
# self.vlm_processor = VLMProcessor(model_name="llava")       # ~12GB
# self.vlm_processor = VLMProcessor(model_name="qwen-vl")     # ~15GB
# self.vlm_processor = VLMProcessor(model_name="gpt4o")       # API-based
```

### Model Comparison

| Model | Size | Speed | Accuracy | Cost | Notes |
|-------|------|-------|----------|------|-------|
| BLIP-2 | 7GB | Fast | Good | Free | Recommended for drones |
| LLaVA | 12GB | Slower | Better | Free | More detailed captions |
| Qwen-VL | 15GB | Slower | Excellent | Free | Chinese-optimized |
| GPT-4o | API | Medium | Best | $$ | Most reliable |

### Adding New VLM

1. **Edit `src/vlm_processor.py`**:

```python
def _initialize_model(self):
    if self.model_name == "my_model":
        from transformers import MyModelProcessor, MyModel
        self.processor = MyModelProcessor.from_pretrained("model_id")
        self.model = MyModel.from_pretrained("model_id")
        print("✓ My Model loaded")
```

2. **Implement analysis method**:

```python
def _analyze_real_frame(self, frame_data):
    # Your custom implementation
    pass
```

## Database Configuration

### Using Different Databases

#### Option 1: SQLite (Current, Default)
```python
# In src/frame_indexer.py
indexer = FrameIndexer(db_path="/custom/path/frames.db")
```

#### Option 2: PostgreSQL (Recommended for Scale)

1. **Install PostgreSQL adapter**:
```bash
pip install psycopg2-binary
```

2. **Modify `src/frame_indexer.py`**:
```python
import psycopg2

class FrameIndexer:
    def __init__(self, db_url="postgresql://user:pass@localhost/frames"):
        self.conn = psycopg2.connect(db_url)
        self.cursor = self.conn.cursor()
        self._initialize_database()
```

3. **Create database**:
```sql
CREATE DATABASE frames;
CREATE USER security_analyst WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE frames TO security_analyst;
```

#### Option 3: TimescaleDB (Time-Series Optimized)

```python
# Automatic with PostgreSQL + TimescaleDB extension
# Provides better performance for temporal queries

# Create hypertable:
SELECT create_hypertable('frames', 'timestamp', if_not_exists => TRUE);

# Benefits:
# - 10-100x faster time-series queries
# - Automatic data compression
# - Built-in retention policies
```

### Database Connection Pooling

For production use, add connection pooling:

```python
from sqlalchemy import create_engine, pool

engine = create_engine(
    'postgresql://user:pass@localhost/frames',
    poolclass=pool.QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

## Dashboard Configuration

### Customizing Dashboard Appearance

Edit `src/dashboard.py`:

```python
st.set_page_config(
    page_title="Drone Security Analyst",
    page_icon="🚁",
    layout="wide",  # or "centered"
    initial_sidebar_state="expanded"  # or "collapsed"
)

# Change color theme
st.markdown("""
<style>
    .reportview-container { background-color: #1a1a1a; }
    .sidebar .sidebar-content { background-color: #0d0d0d; }
</style>
""", unsafe_allow_html=True)
```

### Adding Custom Dashboard Views

1. **Create view function**:

```python
def show_custom_view():
    st.header("📊 Custom Analysis")
    
    # Your custom visualization
    st.write("Custom content here")
```

2. **Register in `main()` view selector**:

```python
view_mode = st.radio(
    "Select View",
    ["Dashboard", "Frames", "Alerts", "Query", "Q&A", "Summary Report", "Custom View"]
)

if view_mode == "Custom View":
    show_custom_view()
```

## Frame Indexing Configuration

### Query Performance Tuning

```python
# Add more indexes for frequently queried fields
self.cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_threat_score ON frames(threat_score)
''')

# Index combinations for complex queries
self.cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_location_time 
    ON frames(location, timestamp)
''')
```

### Data Retention Policies

```python
# Delete frames older than 30 days
def cleanup_old_frames(self, days=30):
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    self.cursor.execute('DELETE FROM frames WHERE timestamp < ?', (cutoff,))
    self.cursor.execute('DELETE FROM alerts WHERE created_at < ?', (cutoff,))
    self.conn.commit()
```

## Agent Configuration

### Adjusting Pattern Detection Sensitivity

Edit `src/alert_engine.py`:

```python
# Repeat visit threshold
MIN_REPEAT_VISITS = 2  # Default
# Change to 1 for more sensitive detection

# Dwell time threshold (minutes)
MAX_DWELL_TIME = 240  # 4 hours
# Change to 120 for 2 hours

# Pattern similarity threshold
PATTERN_SIMILARITY = 0.8  # 80% match required
# Change to 0.7 for more lenient matching
```

### Context Window Size

Edit `src/agent.py`:

```python
# How many frames to keep for pattern detection
CONTEXT_WINDOW = 100  # frames
# Larger = better patterns, more memory
# Smaller = faster processing, less memory

# In process_frames():
if len(previous_frames) > CONTEXT_WINDOW:
    previous_frames = previous_frames[-CONTEXT_WINDOW:]
```

## Logging Configuration

### Enable Debug Logging

Create `src/logging_config.py`:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/drone_agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### Use in components:

```python
import logging
logger = logging.getLogger(__name__)

logger.debug(f"Processing frame {frame_id}")
logger.info(f"Generated {len(alerts)} alerts")
logger.warning(f"Low battery: {battery_level}%")
logger.error(f"Failed to process frame: {error}")
```

## Performance Optimization

### Batch Processing

```python
# Process multiple frames together (faster)
def process_batch(frames, batch_size=10):
    for i in range(0, len(frames), batch_size):
        batch = frames[i:i+batch_size]
        results = agent.process_frames(batch)
        yield results
```

### Query Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_query(query_type, param):
    return indexer.query_by_type(query_type, param)
```

### Model Optimization

```python
# Quantization for faster inference
from transformers import AutoModelForCausalLM
import torch

model = AutoModelForCausalLM.from_pretrained(
    "model_id",
    load_in_8bit=True,  # 8-bit quantization
    device_map="auto"
)
```

## Environment Variables

Create `.env` file:

```bash
# Database
DATABASE_URL=sqlite:///data/frames.db
# DATABASE_URL=postgresql://user:pass@localhost/frames

# VLM Model
VLM_MODEL=blip2
# VLM_MODEL=gpt4o
# VLM_API_KEY=sk-...  # If using API-based model

# Alert Thresholds
THREAT_THRESHOLD=5
HIGH_ALERT_THRESHOLD=7

# Logging
LOG_LEVEL=INFO
LOG_FILE=/tmp/drone_agent.log

# Dashboard
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Performance
MAX_FRAMES_PER_BATCH=50
QUERY_CACHE_SIZE=128
```

Load in Python:

```python
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
VLM_MODEL = os.getenv('VLM_MODEL', 'blip2')
THREAT_THRESHOLD = int(os.getenv('THREAT_THRESHOLD', 5))
```

## Example: Custom Configuration for High-Security Facility

```python
# File: config_high_security.py

ALERT_CONFIG = {
    "loitering_midnight": {
        "enabled": True,
        "time_window": (22, 6),  # 10pm-6am
        "severity": "CRITICAL",
        "threat_score": 10
    },
    "perimeter_breach": {
        "enabled": True,
        "locations": ["perimeter", "fence", "boundary"],
        "severity": "HIGH",
        "threat_score": 8
    },
    "unknown_vehicle": {
        "enabled": True,
        "severity": "MEDIUM",
        "threat_score": 6
    }
}

VLM_CONFIG = {
    "model": "gpt4o",  # Best accuracy
    "confidence_threshold": 0.95,
    "cache_descriptions": True
}

DATABASE_CONFIG = {
    "type": "postgresql",
    "url": "postgresql://user:pass@localhost/high_security_frames",
    "pool_size": 10,
    "retention_days": 90
}

# Use in agent:
from config_high_security import ALERT_CONFIG, VLM_CONFIG
```

---

**Last Updated:** June 13, 2026  
**Version:** 1.0.0
