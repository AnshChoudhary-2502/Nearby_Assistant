import base64
from email.mime.text import MIMEText

from langchain_core.tools import tool
from langgraph.types import interrupt

from gmail_assistant.client import get_gmail_service

_service = None


def _svc():
    global _service
    if _service is None:
        _service = get_gmail_service()
    return _service


def _headers_to_dict(headers):
    return {h["name"]: h["value"] for h in headers}


def _confirm(action: str, **details) -> dict | None:
    """Pause the graph for human approval. Returns a cancellation dict if
    denied, or None if approved (caller proceeds with the action)."""
    decision = interrupt({"action": action, **details})
    if decision != "approve":
        return {"status": "cancelled", "action": action, "reason": "Not approved by user"}
    return None


@tool
def read_emails(max_results: int = 10, label: str = "INBOX") -> dict:
    """Read the most recent emails from a given label (default: INBOX).
    Returns id, from, subject, date, and snippet for each message."""
    resp = _svc().users().messages().list(userId="me", labelIds=[label], maxResults=max_results).execute()
    messages = []
    for m in resp.get("messages", []):
        msg = (
            _svc()
            .users()
            .messages()
            .get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        headers = _headers_to_dict(msg["payload"]["headers"])
        messages.append(
            {
                "id": msg["id"],
                "from": headers.get("From"),
                "subject": headers.get("Subject"),
                "date": headers.get("Date"),
                "snippet": msg.get("snippet"),
                "unread": "UNREAD" in msg.get("labelIds", []),
            }
        )
    return {"messages": messages}


@tool
def search_email(query: str, max_results: int = 10) -> dict:
    """Search emails using Gmail search syntax (e.g. 'from:alice@example.com is:unread').
    Returns id, from, subject, date, and snippet for each match."""
    resp = _svc().users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = []
    for m in resp.get("messages", []):
        msg = (
            _svc()
            .users()
            .messages()
            .get(userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        headers = _headers_to_dict(msg["payload"]["headers"])
        messages.append(
            {
                "id": msg["id"],
                "from": headers.get("From"),
                "subject": headers.get("Subject"),
                "date": headers.get("Date"),
                "snippet": msg.get("snippet"),
            }
        )
    return {"messages": messages}


@tool
def list_labels() -> dict:
    """List all Gmail labels (system and user-created) in the mailbox."""
    resp = _svc().users().labels().list(userId="me").execute()
    return {"labels": [{"id": l["id"], "name": l["name"]} for l in resp.get("labels", [])]}


@tool
def send_email(to: str, subject: str, body: str) -> dict:
    """Send a new email to a recipient. Requires human approval before sending."""
    cancelled = _confirm("send_email", to=to, subject=subject, body=body)
    if cancelled:
        return cancelled

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = _svc().users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"status": "sent", "id": sent["id"], "to": to, "subject": subject}


@tool
def reply_email(message_id: str, body: str) -> dict:
    """Reply to an existing email thread by message id. Requires human approval before sending."""
    original = (
        _svc()
        .users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "Message-ID", "References"],
        )
        .execute()
    )
    headers = _headers_to_dict(original["payload"]["headers"])
    to = headers.get("From", "")
    subject = headers.get("Subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    cancelled = _confirm("reply_email", to=to, subject=subject, body=body)
    if cancelled:
        return cancelled

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    message["In-Reply-To"] = headers.get("Message-ID", "")
    message["References"] = headers.get("References", headers.get("Message-ID", ""))
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = (
        _svc()
        .users()
        .messages()
        .send(userId="me", body={"raw": raw, "threadId": original["threadId"]})
        .execute()
    )
    return {"status": "sent", "id": sent["id"], "to": to, "subject": subject}


@tool
def delete_email(message_id: str) -> dict:
    """Move an email to Trash by message id (recoverable for 30 days). Requires human approval."""
    cancelled = _confirm("delete_email", message_id=message_id)
    if cancelled:
        return cancelled
    _svc().users().messages().trash(userId="me", id=message_id).execute()
    return {"status": "trashed", "id": message_id}


@tool
def mark_read(message_id: str) -> dict:
    """Mark an email as read by message id."""
    _svc().users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()
    return {"status": "marked_read", "id": message_id}


@tool
def mark_unread(message_id: str) -> dict:
    """Mark an email as unread by message id."""
    _svc().users().messages().modify(userId="me", id=message_id, body={"addLabelIds": ["UNREAD"]}).execute()
    return {"status": "marked_unread", "id": message_id}


@tool
def archive_email(message_id: str) -> dict:
    """Archive an email (remove it from the Inbox) by message id. Requires human approval."""
    cancelled = _confirm("archive_email", message_id=message_id)
    if cancelled:
        return cancelled
    _svc().users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["INBOX"]}).execute()
    return {"status": "archived", "id": message_id}


@tool
def create_draft(to: str, subject: str, body: str) -> dict:
    """Create a draft email (not sent) with the given recipient, subject, and body."""
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = _svc().users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return {"status": "draft_created", "id": draft["id"], "to": to, "subject": subject}
