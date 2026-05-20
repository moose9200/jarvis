# mock-oauth

Stand-in OAuth + fake-data server for offline JARVIS development.

## Run

```bash
# As a docker-compose profile (recommended)
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile mock up

# Or standalone for one-off testing
cd tools/mock-oauth
docker build -t jarvis-mock-oauth .
docker run --rm -p 9000:9000 jarvis-mock-oauth
```

Visit http://localhost:9100 to confirm it's up.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Hello page |
| `GET` | `/auth?client_id=…&redirect_uri=…&state=…&scope=…` | Stand-in for Google/Microsoft/Slack `/authorize`. Bounces straight back to `redirect_uri?code=mock_code_xxx&state=…`. |
| `POST` | `/token` | Stand-in for the provider's token-exchange endpoint. Accepts form OR JSON body with `code`. Returns `{access_token, refresh_token, token_type, expires_in, scope}`. Codes are single-use + 10-min TTL. |
| `GET` | `/api/gmail/messages` | Canned 2-message inbox. |
| `GET` | `/api/calendar/events` | Canned 2-event calendar. |
| `GET` | `/api/slack/channels` | Canned channel list. |
| `GET` | `/api/github/notifications` | Canned PR notification. |
| `GET` | `/api/linear/issues` | Canned blocked Linear issue. |

All API responses use the same shape JARVIS connectors expect, so once
auth.py points the real provider URLs at `http://mock-oauth:9100`, the
full flow runs offline.

## Status

Backend `auth.py` is **not yet wired** to fall back to mock-oauth based
on a `MOCK_OAUTH` env flag. That's a follow-up commit (~30 min) — until
then you can hit these endpoints directly from a test:

```bash
curl "http://localhost:9100/auth?client_id=test&redirect_uri=http://localhost:8000/api/auth/google/callback&state=abc"
# → 307 redirect with code=mock_code_…
curl -X POST http://localhost:9100/token -d "code=mock_code_…"
# → {"access_token":"mock_access_token_…", …}
```
