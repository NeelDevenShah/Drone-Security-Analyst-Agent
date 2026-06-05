# Drone Security Analyst - Quick Start Guide

**For GPU/Colab Environments**

## 🚀 One-Line Setup

```bash
cd /home/neel/Desktop/flytbaseAI && pip install opencv-python torch torchvision transformers langchain streamlit chromadb sentence-transformers -q && python main.py
```

## ⚡ Quick Commands

### 1. **Generate Simulated Data** (1 min)

```bash
python src/data_simulator.py
```

✅ Creates: `data/simulated_frames.json` with 10 test frames

### 2. **Test Full Pipeline** (2-3 min)

```bash
python main.py
```

✅ Processes frames → Generates alerts → Outputs report

### 3. **Test Live Video Processing** (30 sec - 5 min depending on video)

```bash
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 10 --export results.json
```

✅ Streams video → Analyzes frames → Stores results

### 4. **Launch Interactive Dashboard** (Web UI)

```bash
streamlit run src/dashboard.py
```

✅ Opens at `http://localhost:8501`

- Load frames
- View alerts
- Run queries
- Q&A interface

### 5. **Run Tests** (1 min)

```bash
pytest tests/ -v
```

✅ Validates all components

---

## 📋 Command Reference

| Command                                      | Purpose             | Time   |
| -------------------------------------------- | ------------------- | ------ |
| `python src/data_simulator.py`               | Generate test data  | 1s     |
| `python main.py`                             | Full pipeline test  | 2min   |
| `python src/live_pipeline.py --video <file>` | Process video       | 1-5min |
| `python src/frame_description.py`            | Test CV description | 1s     |
| `python src/video_stream.py`                 | Test video loading  | 5s     |
| `streamlit run src/dashboard.py`             | Launch UI           | 5s     |
| `pytest tests/ -v`                           | Run all tests       | 1min   |

---

## 🎯 Typical Workflow

```bash
# 1. Setup (first time only)
pip install -q opencv-python torch transformers streamlit

# 2. Generate test data
python src/data_simulator.py

# 3. Process with pipeline
python main.py

# 4. Stream live video
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --export output.json

# 5. View results
cat output.json | head -50
```

---

## 🖥️ For Colab/GPU Environments

### Setup Cell

```python
!cd /home/neel/Desktop/flytbaseAI
!pip install -q opencv-python torch torchvision transformers langchain streamlit chromadb sentence-transformers
```

### Run Pipeline Cell

```python
import sys
sys.path.insert(0, '/home/neel/Desktop/flytbaseAI/src')
from live_pipeline import LiveSecurityAnalysisPipeline

pipeline = LiveSecurityAnalysisPipeline(
    video_source='/home/neel/Desktop/flytbaseAI/sample_data/09172008flight1tape1_5.mpg',
    db_path='/tmp/frames.db',
    fps_limit=15
)

pipeline.start()
# ... processing happens ...
pipeline.print_final_report()
pipeline.export_results('/tmp/results.json')
```

---

## 📊 Output Examples

### After `python main.py`:

```
✓ Processed 10 frames
✓ Generated 14 alerts
  🔴 High/Critical: 5
  🟡 Medium: 10
  🟢 Low: 14
```

### After `python src/live_pipeline.py`:

```
✓ Opened video stream: sample_data/09172008flight1tape1_5.mpg
  Resolution: 720x480
  FPS: 30
  Total Frames: 9000

Progress: 30 frames processed
  Alerts: HIGH:2, MEDIUM:5, LOW:3

[ALERT] 🟠 Person loitering at Main Gate
```

---

## 🔧 Configuration

### Change FPS (video processing speed)

```bash
python src/live_pipeline.py --video <file> --fps 20  # Default: 10
```

### Custom database location

```bash
python src/live_pipeline.py --video <file> --db /custom/path/frames.db
```

### Export results to JSON

```bash
python src/live_pipeline.py --video <file> --export my_results.json
```

---

## ✅ Verification Checklist

Run these to verify everything works:

```bash
# 1. Check imports
python -c "import cv2; print('✓ OpenCV')"
python -c "import torch; print('✓ PyTorch')"
python -c "import langchain; print('✓ LangChain')"

# 2. Check data
ls -lh data/simulated_frames.json

# 3. Quick test
python src/data_simulator.py && python main.py

# 4. Video test
python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg --fps 10
```

---

## 🐛 Troubleshooting

### No module named 'cv2'

```bash
pip install opencv-python
```

### No module named 'torch'

```bash
# For CPU
pip install torch torchvision

# For GPU (CUDA 11.8)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Video file not found

```bash
ls -la sample_data/
# Should show: 09172008flight1tape1_5.mpg
```

### Port 8501 already in use

```bash
streamlit run src/dashboard.py --server.port 8502
```

---

## 📝 Key Files

| File                         | Purpose                                    |
| ---------------------------- | ------------------------------------------ |
| `main.py`                    | Main entry point - simulated data pipeline |
| `src/live_pipeline.py`       | Live video streaming & analysis            |
| `src/video_stream.py`        | Video loading & frame extraction           |
| `src/frame_description.py`   | Frame analysis (CV fallback)               |
| `src/agent.py`               | Agent orchestration                        |
| `data/simulated_frames.json` | Test data                                  |

---

## 🎥 Live Video Streaming Flow

```
Video File (MP4/MPG)
    ↓
[VideoStreamProcessor] → Load & extract frames
    ↓
[FrameDescriptionGenerator] → Analyze each frame
    ↓
[Agent] → Generate alerts
    ↓
[Database] → Store results
    ↓
[Output] → JSON/Console/Database
```

---

## 💾 Database Operations

### View stored frames

```bash
sqlite3 data/frames.db "SELECT COUNT(*) FROM frames;"
```

### View alerts

```bash
sqlite3 data/frames.db "SELECT * FROM alerts LIMIT 5;"
```

### Export to CSV

```bash
sqlite3 data/frames.db ".mode csv" ".output frames.csv" "SELECT * FROM frames;"
```

---

## 🚀 Next Steps

1. **Test locally**: `python main.py`
2. **Stream video**: `python src/live_pipeline.py --video sample_data/09172008flight1tape1_5.mpg`
3. **Export results**: Add `--export output.json`
4. **Analyze**: `cat output.json | python -m json.tool`
5. **Dashboard**: `streamlit run src/dashboard.py` (if local)

---

## 📞 Need Help?

- Check errors: All scripts print `✓` for success, `✗` for errors
- View logs: Run with `-u` flag for unbuffered output: `python -u src/live_pipeline.py`
- Test components: `pytest tests/ -v`

---

**Ready to go! Start with:** `python main.py`
