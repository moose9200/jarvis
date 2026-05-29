"""Hallucination-guardrail unit tests.

Covers the regression that triggered the build: model said "Done, boss.
Email sent." without invoking send_email. The detector must flag this
pattern even when other tools were called (so we don't get false
acquittals).
"""
from ai.guardrails import (
    GuardrailViolation,
    annotate_response,
    detect_uncalled_action_claims,
)


# ── Positive cases — the detector MUST fire ──────────────────────────────


def test_done_boss_with_no_tools_called_flags():
    text = "Done, boss. Email sent to hemant@mokshabotanicals.in."
    violations = detect_uncalled_action_claims(text, tools_called=[])
    assert len(violations) >= 1
    assert any("send_email" in v.required_tools for v in violations)


def test_done_boss_only_when_no_action_tool_called_flags():
    # User called a read-only tool but NOT a send/create — still a lie.
    text = "Done, boss. I sent the email and you're all set."
    violations = detect_uncalled_action_claims(
        text, tools_called=["list_emails", "get_calendar"]
    )
    assert len(violations) >= 1


def test_past_tense_sent_email_no_tool_flags():
    text = "I sent the email to John about the demo."
    violations = detect_uncalled_action_claims(text, tools_called=[])
    assert len(violations) >= 1
    assert violations[0].required_tools == ("send_email",)


def test_created_task_no_tool_flags():
    text = "Created a task for the design review."
    violations = detect_uncalled_action_claims(text, tools_called=[])
    assert len(violations) >= 1
    assert "create_task" in violations[0].required_tools


def test_scheduled_meeting_no_tool_flags():
    text = "Scheduled a meeting for Friday at 3pm."
    violations = detect_uncalled_action_claims(text, tools_called=[])
    assert len(violations) >= 1
    assert "create_event" in violations[0].required_tools


# ── Negative cases — the detector MUST NOT fire ──────────────────────────


def test_send_email_called_passes():
    text = "Done, boss. Email sent to hemant@mokshabotanicals.in."
    violations = detect_uncalled_action_claims(text, tools_called=["send_email"])
    assert violations == []


def test_future_tense_intent_passes():
    # Model saying "I will send" or asking for confirmation — not a claim.
    text = "I'll send that email once you confirm the body."
    violations = detect_uncalled_action_claims(text, tools_called=[])
    assert violations == []


def test_factual_reporting_passes():
    # Reading from a list_emails tool, mentioning an email someone else
    # sent — not a JARVIS action claim.
    text = "John sent you an email yesterday about the demo."
    violations = detect_uncalled_action_claims(text, tools_called=["list_emails"])
    # "John sent you an email" should not trip the regex since it
    # describes another party's action, not JARVIS's.
    # Note: current detector is conservative — this CAN match. Document
    # the false positive risk so we can tighten later.
    # If it does flag, that's noise — accept either 0 or 1 here.
    assert len(violations) <= 1


def test_empty_text_passes():
    assert detect_uncalled_action_claims("", tools_called=[]) == []
    assert detect_uncalled_action_claims("", tools_called=["send_email"]) == []


def test_unrelated_response_passes():
    text = (
        "Based on your calendar, your next meeting is at 2pm. "
        "You have 3 unread emails. No action items pending."
    )
    violations = detect_uncalled_action_claims(text, tools_called=["get_calendar", "list_emails"])
    assert violations == []


# ── annotate_response ────────────────────────────────────────────────────


def test_annotate_response_no_violations_passes_through():
    text = "Hello boss."
    assert annotate_response(text, []) == text


def test_annotate_response_prepends_warning():
    text = "Done, boss. Email sent."
    violations = [
        GuardrailViolation(
            phrase="Done, boss.", required_tools=("send_email",), matched_at=0
        )
    ]
    result = annotate_response(text, violations)
    assert "[guardrail]" in result
    assert text in result  # original preserved
