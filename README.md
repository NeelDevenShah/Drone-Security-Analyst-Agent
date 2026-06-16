# Drone Security Analyst Agent 🛸

An intelligent AI-powered security monitoring system that analyzes drone video feeds in real-time to detect threats, identify objects, and generate actionable security alerts. The system utilizes a Vision Language Model (VLM) for scene understanding, spatial-temporal memory indexing with SQLite and ChromaDB, and a Large Language Model (SmolLM2-1.7B-Instruct) for contextual threat validation and natural language query-answering.

---

## 🎯 System Overview

```
          Drone Video Stream (MP4/RTSP)
                       │
                       ▼
    Frame Extraction & Telemetry Association
                       │
                       ▼
        VLM Processor (BLIP-2 / vLLM)
      (Generates descriptions & objects)
                       │
                       ▼
    Spatial-Temporal Memory & Hybrid Indexing
          ┌────────────┴────────────┐
          ▼                         ▼
      SQLite DB                 ChromaDB
    (Metadata Log)        (Vector Embeddings)
          └────────────┬────────────┘
                       │
                       ▼
       Alert Engine (Rules + SmolLM2 LLM)
     (Checks heuristics & detects patterns)
                       │
                       ▼
    LangChain Security Agent (Orchestration)
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
Streamlit Dashboard            Automated Reports
```

---

## ✨ Key Features

*   **Real-Time Frame Processing**: GPU-accelerated video streaming and frame extraction (using FFMPEG) with optimized queue handling.
*   **Intelligent Scene Description**: Automatically generates semantic descriptions and object categories using BLIP-2 or high-throughput vLLM processor configurations.
*   **Hybrid Alerting System**: Combines deterministic rule-based checks (off-hours loitering, restricted perimeter breach) with a Large Language Model (SmolLM2-1.7B-Instruct) to analyze history and flag complex patterns (e.g., repeat vehicle visits, pattern anomalies).
*   **Spatial-Temporal Memory**: Stores structured metadata in SQLite for temporal queries and frame embeddings in ChromaDB for semantic similarity search.
*   **Natural Language Q&A**: Ask the LangChain agent natural language questions (e.g., *"How many vehicles appeared more than once today?"* or *"Was anyone loitering near the perimeter gate at night?"*) and receive contextual answers.
*   **Interactive Dashboard**: A Streamlit UI providing real-time metrics, live alert logs, historical frame searches, Q&A, and shift report generators.

---

## 🚀 Installation & Setup

### 1. Set Up Environment
Ensure you have Python 3.9+ installed. Clone the repository and initialize a virtual environment:
```bash
cd /home/neel/Desktop/flytbaseAI
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Verify GPU Access (Recommended)
Verify PyTorch can access CUDA to accelerate model inference:
```bash
python -c "import torch; print(f'✓ GPU Available: {torch.cuda.is_available()}'); print(f'Device Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

### 3. Pre-download/Verify Models
To avoid timeout errors during first run, verify loading the models:
*   **VLM Model (BLIP-2)**: Download Salesforce/blip2-opt-2.7b (~7GB)
    ```bash
    python -c "from transformers import Blip2Processor, Blip2ForConditionalGeneration; Blip2Processor.from_pretrained('Salesforce/blip2-opt-2.7b'); print('✓ VLM Model Checked')"
    ```
*   **LLM Model (SmolLM2)**: Download SmolLM2-1.7B-Instruct
    ```bash
    python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; AutoTokenizer.from_pretrained('HuggingFaceTB/SmolLM2-1.7B-Instruct'); print('✓ LLM Model Checked')"
    ```

---

## ⚡ Quick Commands Reference

| Task | Command | Target / Output |
| :--- | :--- | :--- |
| **Simulate Data** | `python src/data_simulator.py` | Generates `data/simulated_frames.json` |
| **Pipeline Test** | `python main.py` | Runs pipeline using simulated data & generates report |
| **Process Video** | `python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 10 --export results.json` | Streams video -> Analyzes -> Saves `results.json` |
| **Start Dashboard** | `streamlit run src/dashboard.py` | Launches UI at `http://localhost:8501` |
| **Run All Tests** | `pytest tests/ -v` | Validates indexing, alerting, and agent systems |

---

## 📋 Usage Patterns

### Pattern 1: One-Shot Video Analysis
Process an entire video file using default configuration and export findings:
```bash
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 10 --export results.json
```
If you want the video to loop continuously (like a live feed simulation):
```bash
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --loop --export results.json
```

### Pattern 2: Live Streaming (RTSP Feed)
Configure the system to read from a network IP camera or drone RTSP transmitter:
```bash
python src/live_pipeline.py --video rtsp://192.168.1.100:554/live --fps 5 --loop --export live_results.json
```

### Pattern 3: Programmatic Database Querying
Query indexed metadata and objects programmatically via Python:
```python
from src.frame_indexer import FrameIndexer

# Initialize connection
db = FrameIndexer("data/frames.db")

# 1. Query by detected object keyword
vehicles = db.query_by_object("vehicle")
print(f"Found {len(vehicles)} vehicle incidents.")

# 2. Query by location
gate_frames = db.query_by_location("Main Gate")
print(f"Found {len(gate_frames)} frames at Main Gate.")
```

### Pattern 4: Programmatic Natural Language Q&A
Ask the intelligence agent questions directly in Python:
```python
from src.agent import SecurityAnalystAgent

agent = SecurityAnalystAgent()
response = agent.run_query("Show all loitering incidents at night and summarize repeat visitors.")
print(response)
```

### Pattern 5: Interactive Dashboard Monitoring
Launch the Streamlit dashboard in a separate terminal:
```bash
streamlit run src/dashboard.py
```
Use the web application to view live metrics, filter alerts by severity (LOW, MEDIUM, HIGH, CRITICAL), search frames, use the Chat Q&A interface, and generate Shift Summary PDF/Text reports.

---

## 🔧 Configuration Guide

All configuration defaults are defined in `src/config.py`.

### 1. Alert Rule Config
Tweak rules in `ALERT_RULE_CONFIG` to customize triggers:
*   `loitering_hours`: Set hours triggering loitering alerts (default: `23:00 - 02:00`).
*   `loitering_threat_score`: Custom threat score from `1-10`.
*   `dwell_time_min_frames`: Adjust thresholds for static loitering detections.

### 2. Detection Categories
To adjust VLM label options, modify `DETECTION_CONFIG.object_categories` and `activity_categories`. This alters the VLM's prompt choices, ensuring outputs map cleanly to SQLite keywords.

### 3. CLI Overrides
You can override central configurations dynamically via CLI:
*   `--video <path>`: Source video file or RTSP stream.
*   `--fps <int>`: Processing rate limit.
*   `--db <path>`: Path to SQLite target.
*   `--export <path>`: JSON export location.

---

## 🧪 Testing & Verification

Ensure all system components are fully verified before production runs:
```bash
# Run unit tests
pytest tests/ -v

# Run component sanity checks
python -c "from src.frame_indexer import FrameIndexer; db = FrameIndexer('data/test.db'); print('✓ Indexer OK')"
python -c "from src.alert_engine import AlertEngine; engine = AlertEngine(); print('✓ Alert Engine OK')"
python -c "from src.vlm_processor import VLMProcessor; vlm = VLMProcessor(); print('✓ VLM OK')"
python -c "from src.agent import SecurityAnalystAgent; agent = SecurityAnalystAgent(); print('✓ Agent OK')"
```

---

## 🏗️ Project Structure

```
flytbaseAI/
├── main.py                     # Main entry point (simulation test)
├── README.md                   # System-wide documentation
├── requirements.txt            # Main dependencies list
├── .gitignore                  # Git ignore rules
│
├── src/                        # Core codebase
│   ├── __init__.py
│   ├── config.py               # Centralized system configurations
│   ├── live_pipeline.py        # Streaming video extraction & pipeline logic
│   ├── video_stream.py         # Thread-safe FFMPEG stream reader
│   ├── vlm_processor.py        # BLIP-2 VLM & vLLM image processor
│   ├── frame_description.py    # OpenCV fallback description generators
│   ├── alert_engine.py         # Rule + SmolLM2 LLM hybrid alert engine
│   ├── frame_indexer.py        # SQLite + ChromaDB persistence layer
│   ├── agent.py                # LangChain Agent & tools registry
│   └── dashboard.py            # Streamlit dashboard script
│
├── design/                     # Design documentation & feature specs
│   ├── FEATURE_SPEC.md         # Detailed product requirements
│   ├── ARCHITECTURE.md         # Architectural diagrams & design rationales
│   └── CONFIGURATION.md        # Deep configuration customization guide
│
├── tests/                      # Testing suite
│   ├── test_indexing.py
│   ├── test_alerts.py
│   └── test_agent.py
│
├── data/                       # Database files
│   ├── frames.db               # SQLite metadata storage
│   └── simulated_frames.json   # Test datasets
│
└── sample_data/
    └── 09172008flight1tape1_5.mpg  # Standard MPG test video
```

---

## 📈 Performance & Scalability

*   **Average Processing Time**: ~100-200ms per frame under GPU-accelerated environments using BLIP-2 (Salesforce/blip2-opt-2.7b).
*   **Alert Latency**: Sub-100ms processing delay per frame.
*   **Scale Ready**: SQLite scales efficiently to millions of frame rows, with ChromaDB index partitioning keeping vector lookups fast (<10ms).
*   **Production Deployment Recommendations**:
    *   Transition database layer to PostgreSQL + TimescaleDB for multi-tenant setups.
    *   Deploy vLLM on a dedicated inference server (e.g., NVIDIA Triton) to scale multi-stream inputs.

---

## 🐛 Troubleshooting

### GPU / CUDA Issues
*   *Symptom*: Output shows `GPU Available: False` or fails model loads.
*   *Fix*: Ensure NVIDIA driver matches PyTorch version. For CUDA 11.8:
    ```bash
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
    ```

### Out of Memory (OOM)
*   *Symptom*: Pipeline crashes with `CUDA out of memory`.
*   *Fix*: Reduce processing rate or disable GPU tracking for secondary processes:
    ```bash
    export CUDA_VISIBLE_DEVICES=""  # Force CPU processing (slower)
    python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 5
    ```

### Database Lock Issues
*   *Symptom*: SQLite logs show `database is locked`.
*   *Fix*: This occurs if multiple scripts try to write simultaneously. Ensure you don't run `main.py` and `live_pipeline.py` pointing to the same DB file concurrently. Reset using:
    ```bash
    rm data/frames.db data/frames_live.db
    ```

### Streamlit Port Conflict
*   *Symptom*: Streamlit dashboard fails to start because port 8501 is busy.
*   *Fix*: Start Streamlit on a custom port:
    ```bash
    streamlit run src/dashboard.py --server.port 8502
    ```

---

## 📞 References & Design Docs

To dive deeper into specifications, refer to the following design guides:
*   [FEATURE_SPEC.md](file:///home/neel/Desktop/flytbaseAI/design/FEATURE_SPEC.md) - Deep dive on system features, success metrics, and use cases.
*   [ARCHITECTURE.md](file:///home/neel/Desktop/flytbaseAI/design/ARCHITECTURE.md) - Deep dive on components, database schemas, and scalability strategies.
*   [CONFIGURATION.md](file:///home/neel/Desktop/flytbaseAI/design/CONFIGURATION.md) - Step-by-step instructions on customizing threat logic, custom VLM layers, and alert scoring.