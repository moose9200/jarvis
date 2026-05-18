# JARVIS — AI Personal Assistant
**Spec date:** 2026-05-18  
**Status:** Approved

---

## Overview

JARVIS is a web-based AI personal assistant product with a 3D holographic HUD inspired by Iron Man's JARVIS. It aggregates tasks, meetings, and messages from all major productivity tools into one prioritized daily view, driven by voice or chat with Claude as the intelligence layer.

**Product target:** SaaS — users connect their own accounts, bring their own Anthropic API key.

---

## Repo Structure

```
jarvis/
├── frontend/          # React 18 + Vite + Three.js + React Three Fiber
├── backend/           # Python + FastAPI
│   └── connectors/    # Per-service OAuth + data modules
├── docs/
│   └── specs/
└── README.md
```

---

## Section 1: Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, React Three Fiber, Three.js |
| State | Zustand |
| Animation | Framer Motion |
| Styling | Tailwind CSS (2D overlays only) |
| Backend | Python 3.11+, FastAPI |
| Database | SQLite (tokens + email intelligence history) |
| HTTP client | httpx (async) |
| AI | Anthropic SDK — `claude-sonnet-4-6` |
| STT | Web Speech API (browser-native) |
| TTS | ElevenLabs API (`eleven_monolingual_v1`, "Adam" voice or custom clone) |
| Wake word | Browser `SpeechRecognition` passive listener |

---

## Section 2: JARVIS 3D UI

### Color Palette
| Token | Value |
|---|---|
| Background | `#0a0e1a` |
| Primary (cyan) | `#00d4ff` |
| Secondary (blue) | `#0066ff` |
| Text | `#ffffff` |
| Urgent accent | `#ff3333` |

### HUD Elements (always visible)
- **Holographic rings** — Three.js torus geometry, cyan/blue emissive, slow rotation
- **Particle field** — floating dots, low opacity background
- **Central orb** — pulses on wake, glows during voice input

### Floating Panels
| Position | Content |
|---|---|
| Top-left | Calendar — today's events (Google + Outlook) |
| Top-right | Email/Messages — priority queue |
| Bottom-left | Tasks — due today, overdue |
| Bottom-right | Active projects + GitHub PRs |
| Center overlay | Chat input (text mode) / voice waveform (voice mode) |

Panels mount/unmount with Framer Motion spring animations.

### Wake States
| State | Visual |
|---|---|
| Idle | Dim rings, slow pulse |
| Listening | Rings accelerate, orb brightens, waveform appears |
| Processing | Scanning animation across panels |
| Responding | Panels highlight as data loads, TTS plays |

### Chat/Voice Toggle
- Pill button, top-center
- Hotkey: `Ctrl+Space`
- Text mode: input field overlay
- Voice mode: mic waveform visualizer

---

## Section 3: Connectors + Auth

OAuth2 handled entirely by FastAPI backend. Frontend never holds tokens. All tokens stored in SQLite.

### Supported Connectors
| Connector | Auth | Data |
|---|---|---|
| Gmail | Google OAuth2 | Unread emails, send/receive history |
| Google Calendar | Google OAuth2 (shared flow) | Today's events |
| Outlook Mail | Microsoft MSAL | Unread emails |
| Outlook Calendar | Microsoft MSAL (shared flow) | Today's events |
| Slack | Slack OAuth2 | Channels, DMs, mentions |
| Microsoft Teams | Microsoft MSAL (shared flow) | Channels, DMs, @mentions |
| WhatsApp | Meta Business API (requires Meta Business account) | Unread messages |
| GitHub | GitHub OAuth App | PRs, issues, notifications |
| Linear | Linear OAuth2 | Assigned issues, in-progress |
| Jira | Atlassian OAuth2 | Assigned tickets |
| Notion | Notion OAuth | Task database pages |

### Backend Endpoints
```
GET  /api/feed                      → aggregated daily plan JSON
GET  /api/email/priority            → priority-scored inbox
POST /api/chat                      → Claude chat/tool use
POST /api/auth/{service}            → initiate OAuth flow
GET  /api/auth/{service}/callback   → exchange code, store token
GET  /api/auth/status               → connected services list
```

### First-Run Onboarding
JARVIS displays connector cards on first load. Each card has a "Connect" button that initiates its OAuth flow. Status dot goes green when connected. User can proceed with partial connections.

---

## Section 4: Email Intelligence Engine

### Goal
Score every incoming email by urgency + importance using behavioral patterns learned from the user's own history — not keyword rules.

### Signals Tracked Per Sender (SQLite)
| Signal | Measurement |
|---|---|
| Your avg response time | Time between their email → your reply |
| Their avg response time | Time between your email → their reply |
| Email frequency | Emails per week, trend direction |
| Thread depth | Message count in active threads |
| Time-of-day patterns | Emails sent outside 9–5 = urgency signal |
| Your reply rate | % of their emails you've replied to |

### Priority Score Formula
```
priority = (relationship_weight × 0.4)
         + (recency_score      × 0.3)
         + (urgency_signals    × 0.2)
         + (thread_depth       × 0.1)

relationship_weight = fast mutual reply times + high frequency
urgency_signals     = subject keywords (follow up, urgent, !!!)
                    + sent outside business hours
                    + explicit deadline mentions
```

### Cold Start
Until 50+ emails analyzed per sender: fall back to recency + sender domain heuristics. Score improves as history accumulates. New senders always start in cold-start mode regardless of account age.

### JARVIS Display
- Top 5 priority emails shown in top-right panel
- Red badge = response expected within 2h based on historical pattern with that sender
- Claude can read scores + previews when user asks "what emails need attention?"

---

## Section 5: AI Interface

### Claude Configuration
- Model: `claude-sonnet-4-6`
- System prompt: JARVIS persona — terse, confident, addresses user as "boss"
- Prompt caching: system prompt + tool definitions cached (reduces cost)
- Conversation memory: last 20 turns in-context; older turns summarized to SQLite + injected as compressed context

### Claude Tool Definitions
```python
# Read tools
get_calendar_events(date: str)
get_priority_emails(limit: int)
get_slack_messages(channels: list, hours: int)
get_teams_messages(channels: list, hours: int)
get_whatsapp_messages(limit: int)
get_github_notifications()
get_linear_issues()
get_jira_issues()
get_notion_tasks()
get_daily_plan()

# Action tools
send_email(to: str, subject: str, body: str)
create_task(title: str, due_date: str, source: str)
```

### Voice Pipeline
```
User speaks
  → browser SpeechRecognition (STT)
  → POST /api/chat { text, mode: "voice" }
  → FastAPI calls Claude with tools
  → Claude returns response text
  → ElevenLabs TTS → audio stream
  → Frontend plays audio, animates waveform in HUD
```

### Chat Pipeline
Identical to voice but input is typed text. TTS plays only if voice mode is active.

### Wake Word
```
Passive SpeechRecognition listens for "Hey JARVIS"
  → HUD activates (idle → listening state)
  → Continues listening for command utterance
  → Full utterance sent to /api/chat
```

---

## Build Order (Subsystems)

| Phase | Subsystem | Depends on |
|---|---|---|
| 1 | Frontend Shell (3D HUD + panels + toggle) | Nothing |
| 2 | Auth + Connector layer | Backend scaffold |
| 3 | Aggregation API + `/api/feed` | Connectors |
| 4 | Email Intelligence Engine | Gmail/Outlook connector |
| 5 | AI Interface (Claude + voice) | All connectors + API |

---

## Out of Scope (v1)

- Mobile app
- Multi-user / team features
- Self-hosted LLM option
- Billing / subscription management (add post-MVP)
