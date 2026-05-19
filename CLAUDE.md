# JARVIS — Claude Code Session Instructions

## READ THIS FIRST, EVERY SESSION

1. Read `docs/BUILD_PROGRESS.md` — shows exactly what's done and what's next
2. Read `docs/JARVIS_V2_MASTER_PROMPT.md` — full spec with all steps
3. Continue from where progress tracker says. Never restart from Step 0.

## Session rules
- Implement ONE step at a time. Finish it fully before moving on.
- After completing ANY sub-task: update `docs/BUILD_PROGRESS.md` immediately
- After completing a full step: `git add -A && git commit -m "step X: description"`
- If tokens running low: update progress tracker, commit, tell user exactly where to resume
- Never leave a step half-done without committing and updating progress

## How to resume after token limit
User will say "continue" or "resume". You:
1. Read `docs/BUILD_PROGRESS.md` for current state
2. Read git log: `git log --oneline -20`
3. Continue from last incomplete item

## Repo
- Backend: `backend/` (FastAPI, Python 3.11)
- Frontend: `frontend/` (React 18, Vite, TypeScript)
- Spec: `docs/JARVIS_V2_MASTER_PROMPT.md`
- Progress: `docs/BUILD_PROGRESS.md`

## Stack
PostgreSQL + Redis + Celery + S3 + pgvector
Anthropic / OpenAI / Groq / Mistral (provider-agnostic)
Three.js + React Three Fiber + Zustand + Tailwind
