# Developer's Quick Reference Card

**Drone Security Analyst Agent** - One-page cheat sheet for common tasks

---

## 🚀 First Time Setup (5 min)

```bash
cd /home/neel/Desktop/flytbaseAI
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -c "import torch; print('✓ Ready' if torch.cuda.is_available() else 'CPU mode')"
```

---

## 🎯 Common Commands

### Process Video
```bash
# Fast processing (10 FPS)
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 10 --export results.json

# High quality (30 FPS) - slower
python src/live_pipeline.py --video input.mp4 --fps 30 --export results.json

# Live stream from drone
python src/live_pipeline.py --rtsp rtsp://192.168.1.100:554/live --fps 5 --export results.json
```

### View Results
```bash
# Show all alerts
python -c "import json; d=json.load(open('results.json')); [print(f'{a[\"severity\"]}: {a[\"message\"]}') for a in d['alerts']]"

# Count by severity
python -c "import json; d=json.load(open('results.json')); from collections import Counter; print(Counter(a['severity'] for a in d['alerts']))"

# Get critical only
python -c "import json; d=json.load(open('results.json')); [print(f'[{a[\"threat_score\"]}] {a[\"message\"]}') for a in d['alerts'] if a['severity']=='CRITICAL']"
```

### Query Database
```bash
# Find all vehicle detections
python -c "from src.frame_indexer import FrameIndexer; db=FrameIndexer('data/frames.db'); frames=db.query_by_object('vehicle'); print(f'Found {len(frames)} frames')"

# Find events at specific location
python -c "from src.frame_indexer import FrameIndexer; db=FrameIndexer('data/frames.db'); frames=db.query_by_location('Main Gate'); print(f'Found {len(frames)} frames')"

# Find night-time activity
python -c "from src.frame_indexer import FrameIndexer; db=FrameIndexer('data/frames.db'); frames=db.query_by_activity_type('loitering'); print(f'Found {len(frames)} frames')"
```

### Ask Questions
```bash
python << 'EOF'
from src.agent import SecurityAnalystAgent
agent = SecurityAnalystAgent()

queries = [
    'What security threats were detected?',
    'How many repeat visitors were there?',
    'Show loitering incidents',
    'What vehicles were present?'
]

for q in queries:
    print(f'\nQ: {q}')
    print(f'A: {agent.run_query(q)}')
EOF
```

### Dashboard
```bash
# Launch interactive UI at http://localhost:8501
streamlit run src/dashboard.py
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific module
pytest tests/test_alerts.py -v
pytest tests/test_indexing.py -v
pytest tests/test_agent.py -v

# Test with output
pytest tests/ -v -s

# Quick sanity check
python -c "
from src.frame_indexer import FrameIndexer
from src.alert_engine import AlertEngine
from src.agent import SecurityAnalystAgent
print('✓ All modules importable')
"
```

---

## 🔧 Configuration

### Change Alert Rules
**File:** `src/alert_engine.py`
```python
# Line ~30: Adjust threat thresholds
THREAT_THRESHOLDS = {
    'CRITICAL': 9,
    'HIGH': 7,
    'MEDIUM': 4,
    'LOW': 1
}

# Line ~80: Modify alert rules in _check_rules()
if condition:
    alerts.append(Alert(...))
```

### Switch VLM Model
**File:** `src/vlm_processor.py`
```python
# Line ~15: Change model
processor = VLMProcessor(model_name="blip2")  # or "llava", "qwen-vl", "simulation"
```

### Change Database
**File:** `src/frame_indexer.py`
```python
# Line ~20: Set database path
indexer = FrameIndexer(db_path="/custom/path/database.db")
```

---

## 📊 Typical Workflow

```
1. Process video
   python src/live_pipeline.py --video input.mp4 --export results.json

2. Check results
   python -c "import json; d=json.load(open('results.json')); print(len(d['alerts']), 'alerts')"

3. Query specific events
   python -c "from src.frame_indexer import FrameIndexer; db=FrameIndexer('data/frames.db'); print(db.query_by_object('vehicle'))"

4. Ask questions
   python -c "from src.agent import SecurityAnalystAgent; a=SecurityAnalystAgent(); print(a.run_query('What threats?'))"

5. View dashboard
   streamlit run src/dashboard.py
```

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| GPU not detected | `python -c "import torch; print(torch.cuda.is_available())"` |
| Out of memory | Add `--fps 5` to reduce FPS |
| Model download fails | Check internet, set `HF_HOME=/path` |
| Database locked | `rm data/frames.db` and restart |
| Import errors | Reinstall: `pip install -r requirements.txt` |
| Slow processing | Use GPU: `python -c "import torch; print(torch.cuda.is_available())"` |

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `src/live_pipeline.py` | Main entry point - process video |
| `src/agent.py` | Q&A and orchestration |
| `src/frame_indexer.py` | Database queries |
| `src/alert_engine.py` | Generate alerts |
| `src/dashboard.py` | Web UI |
| `data/frames.db` | Results database |
| `results.json` | Output file |

---

## 🎯 Module Dependencies

```
live_pipeline.py
  → video_stream.py
  → frame_description.py
  → agent.py
    → frame_indexer.py
    → alert_engine.py
    → vlm_processor.py
  → dashboard.py
```

---

## 📦 Dependencies Reference

| Package | Version | Import | Purpose |
|---------|---------|--------|---------|
| torch | 2.1.1 | `import torch` | GPU/ML |
| transformers | 4.35.2 | `from transformers import...` | VLM models |
| langchain | 0.1.14 | `from langchain import...` | Agent |
| streamlit | 1.28.1 | `import streamlit` | Dashboard |
| opencv-python | 4.8.1 | `import cv2` | Video |
| chromadb | 0.4.17 | `import chromadb` | Embeddings |
| pytest | 7.4.3 | `pytest` | Testing |

---

## 💡 Pro Tips

1. **Fast test:** Use `--fps 20` to process 1 second per minute of video
2. **GPU check:** `nvidia-smi` shows GPU memory usage
3. **Background processing:** Add `&` to run tasks while using dashboard
4. **Export results:** JSON includes all metadata for external processing
5. **Custom alerts:** Just add rules to `src/alert_engine.py` `_check_rules()`
6. **Batch queries:** Loop over `query_by_*()` results
7. **Dashboard filters:** Use sidebar to filter by severity

---

## 🔗 Documentation Quick Links

| Need | File |
|------|------|
| Full setup | `README.md` |
| GPU setup | `README_GPU.md` |
| Copy-paste commands | `QUICK_START.md` |
| Understand features | `design/FEATURE_SPEC.md` |
| Understand design | `design/ARCHITECTURE.md` |
| Customize system | `design/CONFIGURATION.md` |
| Docs overview | `DOCS_README.md` |

---

**Print this card and keep it handy!**  
Last Updated: June 13, 2026
