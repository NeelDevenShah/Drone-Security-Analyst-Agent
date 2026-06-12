# Drone Security Analyst Agent - Feature Specification

## Product Value
The Drone Security Analyst Agent turns a docked drone into an always-on property security analyst. Instead of asking owners or guards to manually watch hours of footage, the agent watches the live video feed with telemetry context, detects meaningful events, and produces searchable evidence such as "a blue Ford F150 entered twice today" or immediate alerts such as "person loitering at midnight near main gate."

For property owners, the real-world impact is faster incident response, fewer missed events, and a reliable daily security record. The system enhances security with automated monitoring while still giving humans clear, explainable alerts and an investigation trail when something happens.

## Key Requirements

### 1. Real-Time Event Understanding
The agent must process live drone video frames and telemetry together, then convert them into structured security observations.

**Must capture:**
- Timestamp and property location
- Drone telemetry such as position, altitude, and source metadata
- Objects and activities such as person, vehicle, gate, road, perimeter, or empty scene
- Natural-language description suitable for human review

**Example output:**
`00:12:31 near Main Gate: person detected, loitering activity, high confidence`

### 2. Immediate Security Alerts
The agent must raise alerts when an observation indicates a security-relevant event, with severity and reason attached.

**Required alert cases:**
- Person loitering during late-night hours
- Vehicle activity after hours or repeated visits by the same object class
- Activity near perimeter, fence, gate, or restricted zones

**Example alert:**
`HIGH: Person loitering near main gate at midnight. Threat score 8/10.`

### 3. Searchable Evidence and Daily Recall
The agent must store analyzed events so property owners can ask questions later and get useful answers without replaying footage manually.

**Required queries:**
- "Show all vehicle events today"
- "Was anyone near the main gate at midnight?"
- "Which objects appeared more than once?"

**Expected result:**
The system returns matching frame records with timestamps, object labels, activity type, location, and alert context.

---

## Architecture Overview

### Data Pipeline
```
Simulated Frames + Telemetry
        ↓
VLM Analysis (BLIP-2)
        ↓
Frame Metadata Extraction
        ↓
Hybrid Indexing (SQLite + ChromaDB)
        ↓
LangChain Agent
        ↓
Alert Engine (Rules + LLM)
        ↓
Streamlit Dashboard
```

### Core Components
1. **Data Simulator**: Generates realistic frame descriptions and telemetry
2. **VLM Processor**: Analyzes frames and extracts structured metadata
3. **Frame Indexer**: Stores frames with embeddings for semantic search
4. **Alert Engine**: Rule-based + LLM hybrid alerting
5. **LangChain Agent**: Orchestrates analysis, reasoning, and Q&A
6. **Dashboard**: Streamlit UI for visualization and queries

---

## Use Cases

### Use Case 1: Daily Security Monitoring
Agent processes frames throughout the day, logs all vehicles and people, flags unusual activity.

### Use Case 2: Incident Investigation
User queries: "Show all frames with people at 00:01" → Agent returns matching frames with full context.

### Use Case 3: Pattern Detection
Agent detects: "Blue Ford F150 appeared at 08:00 and 23:45 today" → Flags repeat visit as MEDIUM alert.

### Use Case 4: Shift Summary
Agent generates end-of-day report: vehicles detected, incidents, recommendations.

---

## Success Metrics
- **Correctness**: VLM generates accurate, contextual frame descriptions
- **Alert Quality**: Relevant alerts with low false positives
- **Scalability**: Efficient indexing for large frame sets
- **User Experience**: Clear, actionable reports and alerts
