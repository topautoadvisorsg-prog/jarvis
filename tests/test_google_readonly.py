import ast
import base64
from datetime import datetime, timezone
from pathlib import Path

import pytest

from integrations.google_readonly import (
    CALENDAR_READONLY_SCOPE,
    GMAIL_READONLY_SCOPE,
    GoogleReadOnlyError,
    READONLY_SCOPES,
    connection_status,
    get_gmail_message,
    list_calendar_events,
    search_gmail,
)


class Call:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class GmailMessages:
    def list(self, **kwargs):
        assert kwargs["userId"] == "me"
        return Call({"messages": [{"id": "m1"}]})

    def get(self, **kwargs):
        if kwargs["format"] == "metadata":
            return Call(
                {
                    "id": "m1",
                    "threadId": "t1",
                    "snippet": "hello",
                    "labelIds": ["INBOX"],
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "a@example.com"},
                            {"name": "Subject", "value": "Update"},
                        ]
                    },
                }
            )
        body = base64.urlsafe_b64encode(b"Status is green.").decode().rstrip("=")
        return Call(
            {
                "id": "m1",
                "threadId": "t1",
                "payload": {
                    "headers": [{"name": "Subject", "value": "Update"}],
                    "mimeType": "text/plain",
                    "body": {"data": body},
                },
            }
        )


class GmailUsers:
    def messages(self):
        return GmailMessages()


class GmailService:
    def users(self):
        return GmailUsers()


class CalendarEvents:
    def list(self, **kwargs):
        assert kwargs["calendarId"] == "primary"
        return Call(
            {
                "items": [
                    {
                        "id": "e1",
                        "summary": "Sales call",
                        "start": {"dateTime": "2026-10-01T10:00:00-07:00"},
                        "end": {"dateTime": "2026-10-01T10:30:00-07:00"},
                        "description": "Discuss scope",
                    }
                ]
            }
        )


class CalendarService:
    def events(self):
        return CalendarEvents()


def test_scopes_are_exactly_gmail_and_calendar_readonly():
    assert set(READONLY_SCOPES) == {GMAIL_READONLY_SCOPE, CALENDAR_READONLY_SCOPE}
    assert all("send" not in scope and "modify" not in scope for scope in READONLY_SCOPES)


def test_mcp_surface_exposes_only_the_four_approved_read_tools():
    server_path = (
        Path(__file__).parents[1] / "integrations" / "google_readonly_server.py"
    )
    tree = ast.parse(server_path.read_text(encoding="utf-8"))
    tools = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
            and decorator.func.value.id == "mcp"
            and decorator.func.attr == "tool"
            for decorator in node.decorator_list
        )
    }
    assert tools == {
        "get_personal_google_status",
        "search_personal_gmail",
        "read_personal_gmail_message",
        "list_personal_calendar_events",
    }


def test_missing_token_reports_setup_required(tmp_path):
    result = connection_status({"JARVIS_GOOGLE_READONLY_DIR": str(tmp_path)})
    assert result["status"] == "setup_required"
    assert result["authority"]["canSendEmail"] is False
    assert result["authority"]["canCreateCalendarEvent"] is False


def test_token_with_broader_scope_fails_closed(tmp_path):
    (tmp_path / "token.json").write_text(
        '{"scopes":["https://www.googleapis.com/auth/gmail.modify"]}',
        encoding="utf-8",
    )
    result = connection_status({"JARVIS_GOOGLE_READONLY_DIR": str(tmp_path)})
    assert result["status"] == "scope_mismatch"


def test_malformed_token_fails_closed(tmp_path):
    (tmp_path / "token.json").write_text("[]", encoding="utf-8")
    result = connection_status({"JARVIS_GOOGLE_READONLY_DIR": str(tmp_path)})
    assert result["status"] == "invalid_credentials"
    assert result["authenticated"] is False


def test_gmail_search_and_read_are_bounded():
    listing = search_gmail("newer_than:1d", 5, service=GmailService())
    message = get_gmail_message("m1", service=GmailService())
    assert listing["count"] == 1
    assert listing["messages"][0]["subject"] == "Update"
    assert message["message"]["body"] == "Status is green."
    assert "untrusted" in message["contentHandling"]
    with pytest.raises(GoogleReadOnlyError, match="between 1 and 50"):
        search_gmail(max_messages=51, service=GmailService())


def test_calendar_list_is_read_only_and_bounded():
    now = lambda: datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    result = list_calendar_events(max_events=10, service=CalendarService(), now=now)
    assert result["count"] == 1
    assert result["events"][0]["summary"] == "Sales call"
    assert result["authority"]["canModifyCalendarEvent"] is False
    with pytest.raises(GoogleReadOnlyError, match="between 1 and 100"):
        list_calendar_events(max_events=101, service=CalendarService(), now=now)
