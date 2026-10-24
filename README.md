# NazarSetu (नज़रसेतु) 🛡️
> **See the Problem. Bridge to Action.**  
> *From a single photograph to meaningful civic action — powered by autonomous AI agents.*

**Category:** Agentic AI / Smart Cities / Civic Technology  
**Edition:** Hackathon MVP  
**Tech Stack:** Python 3.11+, Streamlit, OpenAI Multimodal API & Function Calling, SQLite, Pillow, Pandas

---

## 🌟 Overview

**NazarSetu** bridges the critical gap between citizen awareness and civic execution. Rather than simply describing a photograph, an autonomous AI agent inspects the visual evidence, executes real Python software tools to identify the responsible municipal ward, selects the operational department, runs a smart duplicate check against existing reports, securely registers confirmed complaints with persistent SQLite audit trails, and tracks resolution progress through conversational inquiries.

---

## 🏗️ Architecture

```
nazarsetu/
├── app.py                  # Main Streamlit Web Application (4 Product Views)
├── agent.py                # Autonomous Agent Loop, Tool Calling & Action Trail
├── vision.py               # AI Multimodal Vision & Resilient Heuristic Analyzer
├── tools.py                # Agent Tools (ward lookup, routing, duplicate check, status)
├── database.py             # SQLite Persistence with Audit Event Timelines
├── config.py               # Settings, Heuristics, Priority Rules & Constants
├── components.py           # Indian Civic-Tech Design System, Issue DNA & Trackers
├── generate_samples.py     # Script to generate 1-click hackathon test images
├── data/
│   ├── demo_wards.csv      # Fictional Ward Jurisdiction Dataset
│   ├── nazarsetu.db        # SQLite Persistent Storage
│   └── samples/            # 1-Click Demo Evidence Photographs
├── tests/
│   └── test_core.py        # 12 Core Automated Unit Tests
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Key Features

### 1. Citizen Reporting Studio
- **Drag-and-Drop Upload & One-Click Demos:** Upload any real photo or test with 1-click samples (Pothole, Garbage, Streetlight, Waterlogging, Non-Civic).
- **Vision AI Inspection:** Identifies civic problems and rejects non-civic photos (e.g. pets, selfies) with clear explanations.
- **Citizen Review & Correction:** Citizens retain full agency to adjust classifications, severity, or descriptions.
- **Explicit Confirmation Requirement:** Submissions are never registered without affirmative citizen confirmation.

### 2. Issue DNA (Signature Feature)
A structured, visually striking card summarizing:
- **Problem Identified** with category icon
- **Visible Evidence** (specific structural/environmental findings)
- **Suggested Priority** (High/Medium/Low based on documented safety rules)
- **Assigned Department** & **Location Jurisdiction**
- **Recommended Action** & **Uncertainty Flags**

### 3. Autonomous Action Engine & Tool Calling
The agent executes real Python tools:
- `analyze_issue(image)`: Multimodal classification.
- `select_department(issue_type)`: Routes to Roads, Waste Management, Lighting, or Drainage.
- `find_responsible_ward(city, locality)`: Looks up local jurisdictional dataset.
- `check_duplicate(issue_type, locality, image_hash)`: SHA-256 duplicate guard.
- `register_complaint(confirmed_details)`: Generates `NS-DEMO-XXXXXXXX` ID and records initial event.
- `get_complaint_status(complaint_id)`: Live database lookup.
- `get_complaint_timeline(complaint_id)`: Chronological audit history.

### 4. Agent Action Trail
A vertical timeline progress tracker generated from **actual execution events**, never fabricated reasoning. Shows checkmarks, tool names, parameters, explanations, and expandable JSON execution payloads.

### 5. Smart Duplicate Guard
Computes a SHA-256 hash of the evidence photo and queries unresolved complaints in the same locality. If a potential duplicate is detected, alerts the citizen with the existing ID while giving them the choice to track the original or file a separate incident.

### 6. Conversational Complaint Tracking Assistant
- Interactive chatbot allowing citizens to query: *"What is the status of NS-DEMO-A101B202?"* or *"Check my pothole report"*.
- Agent invokes `get_complaint_status` and `get_complaint_timeline` to return verifiable, real-time facts.
- Displays a 3-Stage Visual Status Tracker (`Pending` ➔ `In Progress` ➔ `Resolved`).

### 7. Demo Administration Command Center
- Real-time counters: Total, Pending, In Progress, Resolved.
- Filterable register by issue category, department, and status.
- Interactive status dispatch controls: Municipal officers can update status with timestamped operational notes. Changes reflect immediately in the AI tracking assistant!

---

## 🛠️ Installation & Quickstart

### Prerequisites
- Python 3.11+
- Git

### 1. Setup Virtual Environment
```bash
git clone <repo-url> NazarSetu
cd NazarSetu

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your OpenAI API key for real vision & tool-calling agent capabilities:
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```
> **Note on Fallback Mode:** If no API key is provided, NazarSetu automatically runs in **Offline Fallback Mode** with deterministic tool execution and local heuristic image analysis. All tools, databases, and UI workflows remain 100% operational!

### 3. Run Automated Tests
```bash
pytest tests/test_core.py -v
```
*(All 12 tests pass verifying routing, lookup, database persistence, timelines, duplicate guard, and error handling).*

### 4. Launch Application
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## ⏱️ 90-Second Hackathon Presentation Script

- **[0:00 - 0:15] The Hook:** *"Judges, everyday citizens see potholes, overflowing bins, and broken streetlights, but reporting them is frustrating, opaque, and often leads nowhere. Meet **NazarSetu** — See the Problem, Bridge to Action."*
- **[0:15 - 0:35] Scene 1: Autonomous Vision & Issue DNA:** *(Click '🕳️ Pothole' from the sidebar, then 'Analyze Issue').* *"A citizen simply uploads a photo. NazarSetu doesn't just describe the image. Our agent extracts **Issue DNA**: identifying deep crater depth, calculating High priority based on vehicular safety rules, and routing jurisdiction to the Indiranagar East ward."*
- **[0:35 - 0:50] Scene 2: Verifiable Agent Action Trail:** *(Scroll to the Action Trail).* *"Notice this isn't hardcoded text. The agent autonomously executed four real Python tools: `select_department`, `find_responsible_ward`, `check_duplicate`, and SHA-256 signature hashing. Every step is an auditable municipal event."*
- **[0:50 - 1:10] Scene 3: Confirmed Registration:** *(Check confirmation box, click 'Confirm & Register Complaint').* *"With explicit citizen consent, the agent registers the complaint in SQLite, generating tracking ID `NS-DEMO-XXXXXXXX`."*
- **[1:10 - 1:25] Scene 4: Conversational Tracking & Live Persistence:** *(Open 'Tracking Assistant' tab, click 'Check NS-DEMO-A101B202').* *"Citizens ask natural questions. The agent calls `get_complaint_status` to show a clean 3-stage progress bar."*
- **[1:25 - 1:30] Scene 5: The Punchline:** *(Open 'Admin Command Center', change status to 'Resolved', re-query in Tracking Assistant).* *"When the municipal team updates the status, the AI assistant immediately reflects it from the database. Real understanding. Real tool execution. Real civic impact."*

---

## ⚖️ Hackathon MVP Limitations & Disclaimers

1. **Fictional Ward Dataset:** Ward IDs (e.g. `DEMO-WARD-BLR-074`) and nodal officer names are demonstration fixtures and do not correspond to active municipal rosters.
2. **No Official Municipal Dispatch:** This prototype stores records locally in SQLite (`data/nazarsetu.db`). No government municipal APIs or emergency services were contacted.
3. **Tracking ID Format:** All generated tracking numbers use the prefix `NS-DEMO-` to avoid confusion with official municipal grievance numbers.
4. **Human-in-the-Loop:** Citizen review and affirmative confirmation are strictly enforced before any complaint is registered in the database.
