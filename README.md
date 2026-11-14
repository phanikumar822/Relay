# Relay: Autonomous Tech Event Discovery Agent

Relay is an autonomous agentic system built with **FastAPI**, **LangGraph**, and **Gemini** that continuously discovers, verifies, categorizes, and dispatches upcoming hackathons, meetups, and developer workshops.

---

## Key Features

- **Multi-Stage LangGraph Agent Pipeline**:
  - **Parser Node**: Extracts topics, target dates, locations, and delay parameters from natural language prompts.
  - **Search Node**: Executes live multi-query web searches across platforms (Devpost, Devfolio, Unstop, Meetup) via Tavily.
  - **Verifier Node**: Filters out outdated content and invalid landing pages with candidate validation and fallback resilience.
  - **Ranker & Tagger Node**: Classifies events into priority tiers (`HIGH`, `MEDIUM`, `LOW`) and extracts attendance (`Online` / `Offline`) and registration cost (`Free` / `Paid`) metadata.
  - **Deduplication Node**: Verifies URLs against MongoDB to prevent redundant event notifications across runs.

- **Dual Execution Modes**:
  - **⚡ Immediate Execution**: Runs single-shot discovery and dispatches an immediate email digest.
  - **📅 Multi-Day Scheduled Execution**: Runs a recurring daily loop until a user-selected target date, observing daily API limits ($T_{\text{run}} \le 60\text{m}$) and calculating dynamic sleep cycles ($T_{\text{sleep}} = 24\text{h} - T_{\text{run}}$).

- **Interactive Event Dashboard**:
  - Real-time MongoDB task status and history polling.
  - Priority-ordered filter bar displaying online, offline, and free counts across priority tiers.
  - **📅 Add to Google Calendar**: One-click calendar event creation.
  - **📊 Export Digest**: Download collected events as CSV or formatted Markdown.

- **Production Resilience**:
  - Automated Gemini API key rotation and rate-limit recovery (`HTTP 429` / `504 Deadline Exceeded`).
  - Seamless fallback between live MongoDB and `mongomock_motor` in-memory store.

---

## Tech Stack

- **Backend**: FastAPI, Python 3.11, Pydantic v2
- **Agent Framework**: LangGraph, LangChain, Google Gemini API (`gemini-3.6-flash`)
- **Search & Scraping**: Tavily Search API
- **Database**: MongoDB (via Motor async driver) with mock fallback
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3 (Modular design)
- **Delivery**: Asynchronous SMTP mailer (`aiosmtplib`)

---

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/phanikumar822/Relay.git
cd Relay
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Required keys:
- `GEMINI_API_KEY`: Google Gemini API key
- `TAVILY_API_KEY`: Tavily Search API key
- `MONGODB_URL`: MongoDB connection string (defaults to `mongodb://localhost:27017`)
- `SECRET_KEY`: Random secret string for JWT authentication

### 4. Run the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.
