# JARVIS — AI Personal Assistant

A 3D JARVIS-inspired AI personal assistant. Aggregates calendar, email, tasks, and messages from 11 services (Gmail, Google Calendar, Outlook Mail, Outlook Calendar, Slack, Teams, WhatsApp, GitHub, Linear, Jira, Notion) into one prioritized daily view, driven by Claude via voice or chat.

## Architecture

- **Frontend:** React 18 + Vite + TypeScript + React Three Fiber 3D HUD
- **Backend:** Python 3.11 + FastAPI + SQLite
- **AI:** Claude `claude-sonnet-4-6` with tool use; `claude-haiku-4-5-20251001` for compression
- **Voice:** Web Speech API (STT) + ElevenLabs (TTS, Adam voice)

## Quick Start

### First-time setup
After cloning, run `make setup` to enable repo-owned git hooks (pre-push runs tests + tsc).

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in keys
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173.

## Project Layout

- `frontend/` — Vite app with HUD scene, panels, chat overlay
- `backend/` — FastAPI app with connectors, AI orchestration, OAuth
- `docs/` — specs and implementation plans
