"""Server-side hallucination guardrails for JARVIS responses.

Catches the most common failure mode: the AI claims to have performed an
external action (sent email, created task, etc.) without actually
invoking the corresponding tool. Designed to be called once at the end
of a chat turn, with the response text and the list of tool names that
were dispatched in that turn.

Returns a list of detected violations which callers can use to:
  - Prepend a correction warning to the response
  - Emit a `correction` SSE event so the frontend can show a banner
  - Log to telemetry / Sentry for retraining the model prompt

The detector is intentionally conservative: it only fires on past-tense
action verbs that are very unlikely to be metaphorical in this product
context (e.g. "sent the email", "created the task"). False positives on
"I'll send" or "ready to send" are avoided by matching past-tense /
perfect-aspect phrasing only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# ── Action-claim regex → tool names that satisfy the claim ───────────────
#
# Multi-tool tuples mean ANY of the listed tools satisfies the claim.
# Patterns target past-tense / perfect aspect to minimise false positives
# on future-tense phrases like "I will send" or "ready to send".

_ACTION_TO_TOOLS: list[tuple[re.Pattern, tuple[str, ...]]] = [
    # email sending — explicit past-tense
    (
        re.compile(
            r"\b(sent|emailed|delivered|fired off|shot off|dropped|drafted and sent)\b[^.!?]{0,80}\b(email|message|note|reply)\b",
            re.IGNORECASE,
        ),
        ("send_email",),
    ),
    (
        re.compile(
            r"\bemail (?:is |has been |was )?(?:sent|delivered|on its way|out the door)\b",
            re.IGNORECASE,
        ),
        ("send_email",),
    ),
    # task creation
    (
        re.compile(
            r"\b(created|filed|opened|logged) (?:a |an |the )?(task|ticket|issue|story)\b",
            re.IGNORECASE,
        ),
        ("create_task",),
    ),
    # github push / PR
    (
        re.compile(
            r"\b(pushed|merged|opened|created) (?:a |the )?(pr|pull request|branch|commit)\b",
            re.IGNORECASE,
        ),
        ("push_to_github",),
    ),
    # calendar scheduling
    (
        re.compile(
            r"\b(scheduled|booked|added) (?:a |the )?(meeting|event|appointment|call)\b",
            re.IGNORECASE,
        ),
        ("create_event",),
    ),
    # generic "Done, boss" at start of response (catches the exact pattern
    # the user reported). Requires SOME action tool was actually called.
    (
        re.compile(r"^\s*done,?\s*boss[.!]?", re.IGNORECASE),
        (
            "send_email",
            "create_task",
            "push_to_github",
            "create_event",
            "create_decision",
            "snooze_decision",
        ),
    ),
]


@dataclass
class GuardrailViolation:
    """A single uncalled-action claim detected in a response.

    Attributes:
        phrase: The text fragment that triggered the rule. Truncated to
            keep logs readable.
        required_tools: Tool names that would have satisfied the claim.
        matched_at: Character offset in the original response.
    """

    phrase: str
    required_tools: tuple[str, ...]
    matched_at: int


def detect_uncalled_action_claims(
    response_text: str,
    tools_called: list[str],
) -> list[GuardrailViolation]:
    """Return action claims in `response_text` not backed by a matching tool.

    Args:
        response_text: Final assistant text shown to the user.
        tools_called: List of tool names dispatched in this chat turn
            (across all sub-turns of the tool loop).

    Returns:
        List of violations, possibly empty. Each violation has the
        matched phrase, the tool name(s) that would have satisfied it,
        and the character offset.
    """
    if not response_text:
        return []
    called = set(tools_called or [])
    violations: list[GuardrailViolation] = []
    for pattern, required in _ACTION_TO_TOOLS:
        m = pattern.search(response_text)
        if not m:
            continue
        if any(t in called for t in required):
            continue
        violations.append(
            GuardrailViolation(
                phrase=m.group(0)[:120],
                required_tools=required,
                matched_at=m.start(),
            )
        )
    return violations


def annotate_response(response_text: str, violations: list[GuardrailViolation]) -> str:
    """Prepend an honesty correction when violations exist.

    The correction is verbose on purpose — we want the user to see that
    JARVIS caught itself lying. Future iterations may simply strip the
    offending claim instead, but the loud correction is more trustworthy
    for the early-trust phase of the product.
    """
    if not violations:
        return response_text
    phrases = "; ".join(f"\"{v.phrase[:80]}\"" for v in violations)
    return (
        "[guardrail] My draft above claimed an action I did not actually "
        f"perform ({phrases}). The action was NOT executed — most likely "
        "because the required tool was not invoked or it returned an "
        "error. Please re-issue the request, or reconnect the relevant "
        "integration if a tool is failing.\n\n---\n\n"
        + response_text
    )
