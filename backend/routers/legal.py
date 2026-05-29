"""Public legal documents (Privacy / Terms / Cookies / AUP / AI disclosure).

Serves the raw markdown bodies from `/app/legal/` over HTTP. The frontend
fetches these and renders them with react-markdown — keeping the source
of truth in a single set of files reviewers can diff.

No auth — these documents MUST be reachable anonymously so:
  - Google OAuth consent screen verification (USER TODO #10) can link to
    Privacy + ToS during the review process
  - Microsoft App verification (USER TODO #11) likewise
  - New visitors can read the policies before creating an account

Cached at the edge: 1-hour `Cache-Control` so reviewers' bots don't pound
the backend, but short enough that small edits propagate fast.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter()


# Map slug → markdown filename. Keep tightly enumerated so we don't
# accidentally serve arbitrary files from the legal directory.
_DOCS = {
    "privacy": "PRIVACY_POLICY.md",
    "terms": "TERMS_OF_SERVICE.md",
    "cookies": "COOKIE_POLICY.md",
    "aup": "ACCEPTABLE_USE_POLICY.md",
    "ai-disclosure": "AI_DISCLOSURE.md",
}

# Resolve the legal directory at import time. In production this is
# `/app/legal/` (Dockerfile `COPY . .` brings the repo root into /app/).
# Tests can override via `JARVIS_LEGAL_DIR` env var.
def _resolve_legal_dir() -> Path:
    override = os.getenv("JARVIS_LEGAL_DIR")
    if override:
        return Path(override)
    in_container = Path("/app/legal")
    if in_container.is_dir():
        return in_container
    # Fallback: walk up to the repo root and look for ./legal/
    return Path(__file__).resolve().parent.parent.parent / "legal"


_LEGAL_DIR = _resolve_legal_dir()


def _read(filename: str) -> str:
    path = _LEGAL_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=500, detail=f"legal doc missing: {filename}")
    return path.read_text(encoding="utf-8")


@router.get("/{slug}", response_class=PlainTextResponse)
def get_legal_doc(slug: str) -> PlainTextResponse:
    """Return the raw markdown body for the requested legal slug."""
    filename = _DOCS.get(slug)
    if not filename:
        raise HTTPException(
            status_code=404,
            detail=f"unknown legal slug; must be one of {sorted(_DOCS)}",
        )
    body = _read(filename)
    return PlainTextResponse(
        body,
        media_type="text/markdown; charset=utf-8",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("", response_class=PlainTextResponse)
def list_legal_docs() -> PlainTextResponse:
    """Discover-endpoint listing available slugs."""
    return PlainTextResponse(
        "\n".join(sorted(_DOCS)),
        headers={"Cache-Control": "public, max-age=3600"},
    )
