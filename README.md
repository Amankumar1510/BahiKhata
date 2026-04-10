# 📒 BahiKhata — SmartLedger AI

A ledger management app for Indian shopkeepers, powered by AI. Track customers, suppliers, and transactions using natural language commands in English, Hindi, or Hinglish.

## Project Structure

```
BahiKhata/
├── backend/          # FastAPI backend (Supabase + LangGraph AI agent)
│   └── app/
│       ├── api/      # REST endpoints (auth, parties, ledger, AI)
│       ├── core/     # Config, security
│       ├── models/   # Pydantic data models
│       └── services/ # Supabase client, AI engine & tools
├── frontend/         # Vanilla JS single-page frontend
│   ├── index.html
│   ├── style.css
│   └── app.js
└── requirements.txt  # Python dependencies
```

---

## Prerequisites

- Python 3.10+
- A [Supabase](https://supabase.com) project with `parties` and `transactions` tables
- A [Groq](https://console.groq.com) API key for the AI agent

---

## Backend Setup

### 1. Create and activate a virtual environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r ../requirements.txt
```

### 3. Configure environment variables

Create a `.env` file inside the `backend/` folder:

```env
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
GROQ_API_KEY=<your-groq-api-key>
```

### 4. Run the backend server

```bash
cd backend
uvicorn app.main:app --reload
```

The API will be available at: **http://localhost:8000**

- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

## Frontend Setup

The frontend is a plain HTML/JS/CSS app — no build step or Node.js required.

### Option A — Open directly in browser *(simplest)*

Just open the file in your browser:

```
frontend/index.html
```

Double-click it in File Explorer, or drag it into a browser window.

### Option B — Serve with Python's built-in HTTP server *(recommended, avoids CORS edge cases)*

```bash
cd frontend
python -m http.server 5500
```

Then open: **http://localhost:5500**

### Option C — Use VS Code Live Server

If you have the [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) extension:

1. Open the `frontend/` folder in VS Code
2. Right-click `index.html` → **Open with Live Server**

---

## Running Both Together

Run these in two separate terminals:

**Terminal 1 — Backend:**
```bash
cd backend
venv\Scripts\activate       # or: source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
python -m http.server 5500
```

Then open **http://localhost:5500** in your browser.

---

## API Overview

| Group | Base Path | Description |
|-------|-----------|-------------|
| Auth | `/api/v1/auth` | Login, Signup, Logout |
| Parties | `/api/v1/parties` | Manage customers & suppliers |
| Ledger | `/api/v1/ledger` | Record & view transactions |
| AI | `/api/v1/ai` | Natural language commands |

Full interactive API reference: http://localhost:8000/docs

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python |
| Database & Auth | Supabase (PostgreSQL + RLS) |
| AI Agent | LangGraph + Groq LPU (Llama) |
| Frontend | Vanilla HTML / CSS / JavaScript |
