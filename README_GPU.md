# Drone Security Analyst Agent - GPU Quick Start

Real-time drone video analysis with AI-powered threat detection. Process live video feeds, detect objects, generate alerts, and query results—all on GPU.

## 🚀 GPU Setup (Colab or Rented GPU)

### 1. Clone & Setup (2 min)

```bash
# Clone repo
git clone <your-repo> flytbaseAI
cd flytbaseAI

# Create environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -q
```

### 2. Verify GPU & Dependencies (1 min)

```bash
# Check GPU
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"

# Check key packages
python -c "import cv2, langchain, transformers, streamlit; print('✓ All packages loaded')"
```

### 3. Download & Test VLM Model (5-10 min on GPU)

```bash
# Download BLIP-2 model (~7GB)
python -c "
from transformers import Blip2Processor, Blip2ForConditionalGeneration
import torch

print('Downloading BLIP-2 model...')
processor = Blip2Processor.from_pretrained('Salesforce/blip2-opt-2.7b')
model = Blip2ForConditionalGeneration.from_pretrained('Salesforce/blip2-opt-2.7b', torch_dtype=torch.float16, device_map='auto')
print('✓ Model loaded to GPU')
print(f'Model device: {next(model.parameters()).device}')
"
```

**Expected output:**
```
Downloading BLIP-2 model...
✓ Model loaded to GPU
Model device: cuda:0
```

---

## 📹 Process Live Video

### Option A: Use Sample Video (Fast Test)

```bash
# Process sample video from disk
python src/live_pipeline.py \
  --video sample_data/09172008flight1tape1_5.mpg \
  --fps 10 \
  --db data/drone_analysis.db \
  --export results.json
```

**Expected output:**
```
✓ Processing video: sample_data/09172008flight1tape1_5.mpg
✓ Frame 1: [08:00] Main Gate - vehicle detected
✓ Frame 2: [12:00] Garage - repeat visitor alert (threat: 5/10)
✓ Frame 3: [23:45] Main Gate - midnight loitering alert (threat: 8/10)
...
✓ Processed 50 frames in 23 seconds
✓ Generated 7 alerts
✓ Results saved to results.json
```

### Option B: Stream from RTSP Camera/Drone

```bash
# Stream from RTSP source (e.g., drone)
python src/live_pipeline.py \
  --rtsp rtsp://drone-ip:554/stream \
  --fps 5 \
  --db data/drone_analysis.db \
  --export results.json
```

**For RTSP setup:**
- Drone RTSP URL: `rtsp://[drone-ip]:[port]/[stream-path]`
- Common drone formats: DJI, Parrot, Auterion
- Test connectivity: `ffprobe rtsp://drone-ip:554/stream`

---

## 🔍 Query Results

### View All Alerts

```bash
python -c "
import json
with open('results.json') as f:
    data = json.load(f)
    
print(f'Total Frames: {len(data[\"frames\"])}')
print(f'Total Alerts: {len(data[\"alerts\"])}')

print('\n=== CRITICAL ALERTS ===')
for alert in data['alerts']:
    if alert['severity'] == 'CRITICAL':
        print(f'[{alert[\"timestamp\"]}] {alert[\"message\"]} (Threat: {alert[\"threat_score\"]}/10)')
"
```

### Search by Object Type

```bash
python -c "
from src.frame_indexer import FrameIndexer

indexer = FrameIndexer('data/drone_analysis.db')

# Find all vehicle detections
vehicles = indexer.query_by_object('vehicle')
print(f'Found {len(vehicles)} vehicle events')
for frame in vehicles:
    print(f'  [{frame[\"timestamp\"]}] {frame[\"location\"]}: {frame[\"description\"][:60]}...')
"
```

### Ask Questions about Results

```bash
python -c "
from src.agent import SecurityAnalystAgent

agent = SecurityAnalystAgent()

# Ask about findings
result = agent.run_query('What security issues were detected?')
print(result)
"
```

---

## 🎯 Full Workflow (GPU)

**One command to run everything:**

```bash
# 1. Process video
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 10 --export results.json && \
# 2. Show alerts
python -c "import json; d=json.load(open('results.json')); print(f'Alerts: {len(d[\"alerts\"])}'); [print(f'{a[\"severity\"]}: {a[\"message\"]}') for a in d['alerts'][:5]]" && \
# 3. Start dashboard
streamlit run src/dashboard.py
```

**Timeline:**
- ⏱️ Video processing: 20-30 sec (GPU accelerated)
- ⏱️ Alert generation: 5-10 sec
- ⏱️ Dashboard startup: 3 sec

---

## 📊 Dashboard (Live Monitoring)

```bash
streamlit run src/dashboard.py
```

Opens at `http://localhost:8501`

**Features:**
- 📈 Real-time metrics (frames processed, alerts generated)
- 🚨 Alert list with severity filtering
- 🔍 Search frames by object, location, time
- 💬 Ask questions in natural language
- 📋 Generate shift reports

---

## ✅ Verification Checklist

After setup, verify each component works:

```bash
# 1. Dependencies ✓
python -c "import torch, cv2, langchain; print('✓ Core packages')"

# 2. GPU Access ✓
python -c "import torch; print(f'✓ GPU: {torch.cuda.is_available()}')"

# 3. VLM Model ✓
python -c "from transformers import Blip2Processor; print('✓ VLM available')"

# 4. Database ✓
python -c "from src.frame_indexer import FrameIndexer; db = FrameIndexer('data/test.db'); print('✓ Database')"

# 5. Alert Engine ✓
python -c "from src.alert_engine import AlertEngine; engine = AlertEngine(); print('✓ Alerts')"

# 6. Live Pipeline ✓
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 20 --export test_results.json
```

All should show ✓

---

## 🐛 Troubleshooting

### GPU Not Detected

```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"
python -c "import torch; print(torch.cuda.get_device_name())"

# Force CPU mode
export CUDA_VISIBLE_DEVICES=""
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 20
```

### Out of Memory

```bash
# Reduce FPS and model precision
python src/live_pipeline.py \
  --video sample_data/09172008flight1tape1_5.mpg \
  --fps 5 \
  --mixed-precision
```

### Slow Processing

```bash
# Check GPU utilization
nvidia-smi

# Increase batch size
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --batch-size 8
```

### Model Download Timeout

```bash
# Use smaller model
python -c "
from transformers import Blip2Processor, Blip2ForConditionalGeneration
import torch
model = Blip2ForConditionalGeneration.from_pretrained(
    'Salesforce/blip2-opt-2.7b',
    torch_dtype=torch.float16,
    device_map='auto'
)
print('✓ Model ready')
"
```

---

## 📁 Output Files

After processing:

- `results.json` - All frames, objects, alerts, with timestamps
- `data/drone_analysis.db` - Indexed frames for fast querying
- `data/shift_summary.txt` - Human-readable report

---

## 🎮 Quick Commands Reference

| Task | Command |
|------|---------|
| Process video | `python src/live_pipeline.py --video file.mp4 --export results.json` |
| Stream drone | `python src/live_pipeline.py --rtsp rtsp://ip:554/stream` |
| View alerts | `python -c "import json; print(json.load(open('results.json'))['alerts'])"` |
| Search objects | `python -c "from src.frame_indexer import FrameIndexer; db=FrameIndexer('data/drone_analysis.db'); print(db.query_by_object('vehicle'))"` |
| Ask question | `python -c "from src.agent import SecurityAnalystAgent; a=SecurityAnalystAgent(); print(a.run_query('What threats?'))"` |
| Dashboard | `streamlit run src/dashboard.py` |
| Run tests | `pytest tests/ -v` |
| Check GPU | `python -c "import torch; print(torch.cuda.is_available())"` |

---

## 🔗 File Locations

```
flytbaseAI/
├── src/
│   ├── live_pipeline.py          ← Main command (process videos)
│   ├── frame_indexer.py          ← Query results
│   ├── agent.py                  ← Ask questions
│   ├── dashboard.py              ← Web UI
│   └── vlm_processor.py           ← Model management
├── sample_data/
│   └── 09172008flight1tape1_5.mpg ← Test video
├── data/
│   └── frames.db                 ← Query results here
└── results.json                   ← Output file
```

---

**Last Updated:** June 13, 2026 | **Status:** GPU-Ready
