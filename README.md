# Drone Security Analyst Agent

An intelligent AI-powered security monitoring system that analyzes drone video feeds in real-time to detect threats, identify objects, and generate actionable security alerts.

## 🎯 System Overview

```
Drone Video Stream
    ↓
Frame Extraction (Video → Still Images)
    ↓
Vision Language Model (BLIP-2) Analysis
    ↓
Object Detection & Semantic Description
    ↓
Hybrid Alert System (Rules + LLM)
    ↓
SQLite + ChromaDB Indexing
    ↓
LangChain Agent Q&A
    ↓
Streamlit Dashboard & Reporting
```

---

## 🚀 Quick Start (GPU Recommended)

### 1. Setup Environment (2 min)

```bash
cd /home/neel/Desktop/flytbaseAI
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q
```

### 2. Test GPU Access

```bash
python -c "import torch; print(f'✓ GPU: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

### 3. Process Video (Sample)

```bash
python src/live_pipeline.py \
  --video sample_data/09172008flight1tape1_5.mpg \
  --fps 10 \
  --export results.json
```

### 4. View Results

```bash
python -c "
import json
data = json.load(open('results.json'))
print(f'Frames: {len(data[\"frames\"])}')
print(f'Alerts: {len(data[\"alerts\"])}')
print('\nTop Alerts:')
for alert in data['alerts'][:5]:
    print(f'  [{alert[\"severity\"]}] {alert[\"message\"][:60]}...')
"
```

### 5. Launch Dashboard

```bash
streamlit run src/dashboard.py
```

Opens at `http://localhost:8501` with live UI for:
- Real-time metrics
- Alert filtering
- Frame search
- Natural language Q&A
- Report generation

---

## 📋 Project Structure

```
flytbaseAI/
├── main.py                           # Main entry point
├── README.md                         # This file
├── README_GPU.md                     # GPU-focused quick start
├── QUICK_START.md                    # Executable commands reference
├── requirements.txt                  # Dependencies
├── .gitignore                        # Git exclusions
├── design/
│   ├── FEATURE_SPEC.md              # Feature specification
│   ├── ARCHITECTURE.md              # System design & rationale
│   └── CONFIGURATION.md             # Config & customization guide
├── src/
│   ├── __init__.py
│   ├── data_simulator.py            # Generate test frames
│   ├── vlm_processor.py             # BLIP-2 model integration
│   ├── frame_indexer.py             # SQLite + ChromaDB storage
│   ├── alert_engine.py              # Rule + LLM alerting
│   ├── agent.py                     # LangChain orchestration
│   ├── config.py                    # Central runtime configuration
│   ├── video_stream.py              # Video/RTSP processing
│   ├── frame_description.py         # Frame analysis
│   ├── live_pipeline.py             # End-to-end streaming pipeline
│   └── dashboard.py                 # Streamlit UI
├── tests/
│   ├── test_indexing.py
│   ├── test_alerts.py
│   └── test_agent.py
├── data/
│   ├── frames.db                    # SQLite database
│   └── simulated_frames.json        # Test data
└── sample_data/
    └── 09172008flight1tape1_5.mpg   # Test video (720x480, 30fps)
```

---

## �� Usage Patterns

### Pattern 1: One-Shot Video Analysis

```bash
# Process entire video file
python src/live_pipeline.py --video path/to/video.mp4 --fps 10 --export results.json

# Use configured defaults from src/config.py
python src/live_pipeline.py --export

# Loop a file continuously until Ctrl+C
python src/live_pipeline.py --video path/to/video.mp4 --loop --export loop_results.json

# View results
python -c "import json; d=json.load(open('results.json')); [print(f'{a[\"severity\"]}: {a[\"message\"]}') for a in d['alerts']]"
```

### Pattern 2: Live Streaming from Drone

```bash
# Stream from RTSP (e.g., DJI Mavic 3)
python src/live_pipeline.py --video rtsp://192.168.1.100:554/live --fps 5 --loop --export live_results.json

# In another terminal, monitor dashboard
streamlit run src/dashboard.py
```

### Pattern 3: Query Indexed Results

```bash
# Search frames by object type
python -c "
from src.frame_indexer import FrameIndexer
db = FrameIndexer('data/frames.db')
vehicles = db.query_by_object('vehicle')
print(f'Found {len(vehicles)} vehicle events')
"

# Search by time range
python -c "
from src.frame_indexer import FrameIndexer
from datetime import datetime
db = FrameIndexer('data/frames.db')
start = datetime(2024, 6, 13, 22, 0)  # 10 PM
end = datetime(2024, 6, 13, 23, 59)
night_frames = db.query_by_timestamp_range(start, end)
print(f'Night shift: {len(night_frames)} frames')
"
```

### Pattern 4: Ask Questions (Q&A)

```bash
python -c "
from src.agent import SecurityAnalystAgent
agent = SecurityAnalystAgent()

# Ask natural language questions
queries = [
    'What security threats were detected?',
    'How many repeat visitors?',
    'Show all loitering incidents',
    'What vehicles were present?'
]

for q in queries:
    result = agent.run_query(q)
    print(f'Q: {q}')
    print(f'A: {result}\n')
"
```

### Pattern 5: Dashboard Monitoring

```bash
# Just run dashboard to explore all features
streamlit run src/dashboard.py

# Features:
# - Dashboard tab: Key metrics, alert summary
# - Frames tab: Browse all detected frames
# - Alerts tab: Filter by severity level
# - Query tab: Search by object, location, time
# - Q&A tab: Ask natural language questions
# - Report tab: Generate and export reports
```

---

## 🔧 Configuration

All common runtime settings live in `src/config.py`. Change defaults there when you want project-wide behavior, or use CLI flags when you only want to override one run.

```python
STREAM_CONFIG = StreamConfig(
    fps_limit=10,
    loop=False,
    queue_size=10,
)

PIPELINE_CONFIG = PipelineConfig(
    video_source="sample_data/09172008flight1tape1_5.mpg",
    db_path="data/frames_live.db",
    export_path="results.json",
    default_location="Drone-Aerial",
    context_frame_limit=50,
    progress_interval_frames=10,
)
```

### CLI Overrides

`src/config.py` provides defaults. These flags override them for a single command:

| Setting | Config field | CLI override |
|---------|--------------|--------------|
| Video/RTSP source | `PIPELINE_CONFIG.video_source` | `--video path_or_url` |
| Processing FPS | `STREAM_CONFIG.fps_limit` | `--fps 10` |
| SQLite database | `PIPELINE_CONFIG.db_path` | `--db data/run.db` |
| JSON export path | `PIPELINE_CONFIG.export_path` | `--export results.json` |
| Looping mode | `STREAM_CONFIG.loop` | `--loop` / `--no-loop` |

```bash
# Configured one-shot run. Stops at EOF.
python src/live_pipeline.py --export

# Override only this run.
python src/live_pipeline.py --video file.mp4 --fps 5 --db data/custom.db --export custom.json

# Continuous replay/live-style mode.
python src/live_pipeline.py --video file.mp4 --loop --export loop_results.json
```

### Alert Rules

Edit `ALERT_RULE_CONFIG` in `src/config.py`:

```python
ALERT_RULE_CONFIG = AlertRuleConfig(
    loitering_hours=(23, 0, 1, 2),
    night_vehicle_hours=(23, 0, 1, 2, 3, 4, 5, 6),
    loitering_severity="HIGH",
    loitering_threat_score=8,
    perimeter_severity="MEDIUM",
    perimeter_threat_score=6,
    night_vehicle_severity="LOW",
    night_vehicle_threat_score=3,
    repeat_visit_severity="MEDIUM",
    repeat_visit_threat_score=5,
)
```

### Object Detection Categories

Edit `DETECTION_CONFIG` in `src/config.py` to change the labels the VLM is allowed to choose. The VLM prompt is built from these values and asks the model to return JSON with `description`, `objects`, and `activity_type`.

```python
DETECTION_CONFIG = DetectionConfig(
    object_categories=(
        "vehicle",
        "person",
        "drone",
        "fire",
    ),
    activity_categories=(
        "vehicle+person",
        "vehicle",
        "person",
        "drone",
        "fire",
        "empty",
    ),
    fallback_object="scene",
    fallback_activity="empty",
)
```

`cv_fallback_keywords` and `cv_fallback_activity_rules` in the same config are only used when the real VLM is unavailable and the system has to use the OpenCV fallback.

### VLM, Database, and Simulator Defaults

Edit these config blocks in `src/config.py`:

```python
VLM_CONFIG = VLMConfig(
    model_name="blip2",
    model_repo="Salesforce/blip2-opt-2.7b",
    prompt="Analyze this drone security frame. Choose object labels only from {object_categories}. Choose one activity_type only from {activity_categories}. Return only JSON with keys: description, objects, activity_type.",
    use_cv_fallback=True,
    fallback_on_load_error=False,
)

DATABASE_CONFIG = DatabaseConfig(
    db_path="data/frames.db",
)

SIMULATOR_CONFIG = SimulatorConfig(
    output_path="data/simulated_frames.json",
)
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Test Specific Component

```bash
# Test frame indexing
pytest tests/test_indexing.py -v

# Test alert engine
pytest tests/test_alerts.py -v

# Test agent orchestration
pytest tests/test_agent.py -v
```

### Manual Verification

```bash
# 1. Test data generation
python src/data_simulator.py
# Expected: Creates data/simulated_frames.json with 10 test frames

# 2. Test frame indexing
python -c "from src.frame_indexer import FrameIndexer; db = FrameIndexer('data/test.db'); print('✓ Database OK')"

# 3. Test alert engine
python -c "from src.alert_engine import AlertEngine; engine = AlertEngine(); print('✓ Alerts OK')"

# 4. Test VLM processor
python -c "from src.vlm_processor import VLMProcessor; v = VLMProcessor(); print('✓ VLM OK')"

# 5. Test agent
python -c "from src.agent import SecurityAnalystAgent; a = SecurityAnalystAgent(); print('✓ Agent OK')"

# 6. Full pipeline
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 20 --export test.json
# Expected: Generates test.json with frames and alerts
```

---

## 📊 Example Scenarios

### Scenario 1: Repeat Vehicle Detection

**Input:** Blue Ford F150 appears at 08:00, 12:00, and 23:45
**Output:**
```json
{
  "alert_type": "repeat_visitor",
  "message": "Repeat visit: blue ford f150 detected at multiple times",
  "severity": "MEDIUM",
  "threat_score": 5
}
```

### Scenario 2: Midnight Loitering

**Input:** Person detected near perimeter at 00:15 (off-hours)
**Output:**
```json
{
  "alert_type": "loitering_midnight",
  "message": "Person loitering at perimeter during off-hours (00:15)",
  "severity": "HIGH",
  "threat_score": 8
}
```

### Scenario 3: Dashboard Q&A

**User Question:** "What happened during night shift?"
**Agent Response:**
```
During the night shift (22:00-06:00), we detected:
- 2 loitering incidents
- 1 unauthorized vehicle at midnight
- 3 repeat visitors
- Overall threat level: MEDIUM
Recommended action: Increase patrols
```

---

## 🏗️ Architecture Details

### Data Pipeline Components

| Component | Purpose | Input | Output |
|-----------|---------|-------|--------|
| **Video Stream** | Load video/RTSP | MP4, RTSP URL | Frame stream |
| **Frame Extractor** | Extract still images | Video stream | Individual frames |
| **VLM Processor** | Semantic analysis | Frame (image) | Text description |
| **Alert Engine** | Generate alerts | Frame + description | Alert objects |
| **Frame Indexer** | Store & retrieve | Alert, metadata | Database records |
| **LangChain Agent** | Orchestration | Query text | Natural language result |
| **Dashboard** | Visualization | Database | Interactive UI |

### Hybrid Alert System

**Rule Layer (Deterministic):**
- Loitering midnight trigger
- Perimeter breach trigger
- Night vehicle activity trigger

**LLM Layer (Contextual):**
- Repeat visitor detection
- Pattern analysis
- Threat scoring
- Context-aware insights

---

## 🚨 Alert Types & Severity

| Alert Type | Trigger | Severity | Threat Score |
|------------|---------|----------|--------------|
| Loitering Midnight | Person 23:00-06:00 | HIGH | 8 |
| Perimeter Breach | Object at fence line | MEDIUM | 6 |
| Night Vehicle | Vehicle 23:00-06:00 | LOW | 3 |
| Repeat Visit | Same object 2+ times | MEDIUM | 5 |
| Unusual Activity | Uncommon pattern | MEDIUM | 4 |

---

## 💡 Key Features

✅ **Real-Time Processing**
- GPU-accelerated frame analysis
- Sub-second alert generation
- Live streaming support

✅ **Intelligent Detection**
- BLIP-2 Vision Language Model
- Object identification
- Activity classification

✅ **Hybrid Alerting**
- Rule-based triggers (deterministic)
- LLM-enhanced analysis (contextual)
- Threat scoring (1-10 scale)

✅ **Semantic Search**
- SQLite metadata indexing
- ChromaDB embedding search
- Natural language queries

✅ **Interactive Dashboard**
- Real-time metrics
- Alert filtering
- Frame browsing
- Q&A interface
- Report generation

✅ **Extensible Design**
- Modular component architecture
- Tool-based LangChain integration
- Easy to add new alert rules
- Support for multiple VLM models

---

## 🐛 Troubleshooting

### GPU Not Detected
```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
# If False, check: nvidia-smi, CUDA drivers, PyTorch installation
```

### Out of Memory
```bash
# Reduce processing rate
python src/live_pipeline.py --video file.mp4 --fps 5

# Or use CPU
export CUDA_VISIBLE_DEVICES=""
python src/live_pipeline.py --video file.mp4
```

### Model Download Fails
```bash
# Use smaller model
export HF_HOME=/path/to/cache  # Set model cache location
python src/vlm_processor.py    # Try downloading again
```

### Database Locked
```bash
# Remove old database
rm data/frames.db
# Re-run pipeline
python src/live_pipeline.py --video file.mp4 --export results.json
```

---

## 📚 File Reference

### Core Modules

**`src/live_pipeline.py`** - Main entry point
- Processes video files or RTSP streams
- Extracts frames and generates descriptions
- Runs alert analysis and stores results
- Command-line interface with options

**`src/agent.py`** - LangChain orchestration
- Frame processing pipeline
- Natural language Q&A
- Pattern detection
- Shift summary generation

**`src/dashboard.py`** - Streamlit UI
- Real-time metrics display
- Alert filtering interface
- Frame search capabilities
- Report generation

**`src/frame_indexer.py`** - Database layer
- SQLite metadata storage
- ChromaDB semantic search
- Query methods for filtering
- Result pagination

**`src/alert_engine.py`** - Alert generation
- Rule-based trigger system
- LLM contextual analysis
- Threat scoring
- Alert persistence

**`src/vlm_processor.py`** - Vision model
- BLIP-2 integration
- Fallback to simulation
- Object extraction
- Activity classification

### Additional Files

**`src/video_stream.py`** - Video processing
**`src/frame_description.py`** - Frame analysis
**`tests/*.py`** - Unit tests
**`design/*.md`** - Architecture documentation

---

## 📈 Performance Metrics

- Frame processing: 100-200ms (GPU)
- Alert generation: 50-100ms per frame
- Query response: <1 second
- Dashboard load: 2-3 seconds
- Full video analysis: ~2-5 minutes (depends on video length/FPS)

---

## 🤝 Extension Points

### Add Custom Alert Rule

Edit `src/alert_engine.py` `_check_rules()`:
```python
if custom_condition:
    alerts.append(Alert(
        alert_type="custom_alert",
        severity="MEDIUM",
        threat_score=5,
        message="Custom alert message"
    ))
```

### Add New VLM Model

Edit `src/vlm_processor.py` `_initialize_model()`:
```python
elif self.model_name == "custom":
    # Load your model here
    self.model = load_custom_model()
```

### Add Dashboard Widget

Edit `src/dashboard.py` `main()`:
```python
elif page == "Custom":
    st.header("My Custom Analysis")
    # Add your visualization
```

---

## 📞 Support & Documentation

- **Feature Specification**: `design/FEATURE_SPEC.md`
- **Architecture Document**: `design/ARCHITECTURE.md`
- **Configuration Guide**: `design/CONFIGURATION.md`
- **Quick Start Commands**: `QUICK_START.md`
- **GPU-Focused Setup**: `README_GPU.md`

---

## 📦 Dependencies

Core: Python 3.9+, PyTorch, OpenCV, Transformers, LangChain, Streamlit, SQLite3, ChromaDB

See `requirements.txt` for complete list with versions.

---

**Version:** 1.0.0 | **Status:** Production Ready | **Last Updated:** June 13, 2026
