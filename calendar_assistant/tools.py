from datetime import datetime, timezone

from langchain_core.tools import tool
from langgraph.types import interrupt

from client import get_calendar_service

_service = None


def _svc():
    global _service
    if _service is None:
        _service = get_calendar_service()
    return _service


def _confirm(action: str, **details) -> dict | None:
    """Pause the graph for human approval. Returns a cancellation dict if
    denied, or None if approved (caller proceeds with the action)."""
    decision = interrupt({"action": action, **details})
    if decision != "approve":
        return {"status": "cancelled", "action": action, "reason": "Not approved by user"}
    return None


def _summarize(event: dict) -> dict:
    start = event.get("start", {})
    end = event.get("end", {})
    return {
        "id": event.get("id"),
        "summary": event.get("summary"),
        "start": start.get("dateTime", start.get("date")),
        "end": end.get("dateTime", end.get("date")),
        "location": event.get("location"),
        "description": event.get("description"),
        "attendees": [a.get("email") for a in event.get("attendees", [])],
        "status": event.get("status"),
        "html_link": event.get("htmlLink"),
    }


@tool
def list_calendars() -> dict:
    """List all calendars the user has access to (id, name, whether it's the primary calendar)."""
    resp = _svc().calendarList().list().execute()
    return {
        "calendars": [
            {"id": c["id"], "summary": c.get("summary"), "primary": c.get("primary", False)}
            for c in resp.get("items", [])
        ]
    }


@tool
def list_events(max_results: int = 10, time_min: str | None = None, calendar_id: str = "primary") -> dict:
    """List upcoming events on a calendar, ordered by start time.
    time_min is an optional RFC3339 timestamp (e.g. '2026-07-22T00:00:00Z'); defaults to now."""
    if time_min is None:
        time_min = datetime.now(timezone.utc).isoformat()
    resp = (
        _svc()
        .events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return {"events": [_summarize(e) for e in resp.get("items", [])]}


@tool
def search_events(query: str, max_results: int = 10, calendar_id: str = "primary") -> dict:
    """Search events on a calendar by free-text query (matches title, description, location, attendees)."""
    resp = (
        _svc()
        .events()
        .list(calendarId=calendar_id, q=query, maxResults=max_results, singleEvents=True, orderBy="startTime")
        .execute()
    )
    return {"events": [_summarize(e) for e in resp.get("items", [])]}


@tool
def get_event(event_id: str, calendar_id: str = "primary") -> dict:
    """Get full details of a single event by id."""
    event = _svc().events().get(calendarId=calendar_id, eventId=event_id).execute()
    return _summarize(event)


@tool
def create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = "",
    attendees: list[str] | None = None,
    timezone_name: str = "UTC",
    calendar_id: str = "primary",
) -> dict:
    """Create a new calendar event. start_time/end_time are RFC3339 timestamps
    (e.g. '2026-07-23T10:00:00'). Requires human approval before creating."""
    cancelled = _confirm(
        "create_event",
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        location=location,
        attendees=attendees or [],
    )
    if cancelled:
        return cancelled

    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start_time, "timeZone": timezone_name},
        "end": {"dateTime": end_time, "timeZone": timezone_name},
    }
    if attendees:
        body["attendees"] = [{"email": a} for a in attendees]

    event = _svc().events().insert(calendarId=calendar_id, body=body).execute()
    return {"status": "created", **_summarize(event)}


@tool
def update_event(
    event_id: str,
    calendar_id: str = "primary",
    summary: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    description: str | None = None,
    location: str | None = None,
    timezone_name: str = "UTC",
) -> dict:
    """Update fields of an existing event by id. Only provided fields are changed.
    Requires human approval before applying changes."""
    cancelled = _confirm(
        "update_event",
        event_id=event_id,
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        location=location,
    )
    if cancelled:
        return cancelled

    event = _svc().events().get(calendarId=calendar_id, eventId=event_id).execute()
    if summary is not None:
        event["summary"] = summary
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location
    if start_time is not None:
        event["start"] = {"dateTime": start_time, "timeZone": timezone_name}
    if end_time is not None:
        event["end"] = {"dateTime": end_time, "timeZone": timezone_name}

    updated = _svc().events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
    return {"status": "updated", **_summarize(updated)}


@tool
def delete_event(event_id: str, calendar_id: str = "primary") -> dict:
    """Delete an event by id. Requires human approval before deleting."""
    cancelled = _confirm("delete_event", event_id=event_id)
    if cancelled:
        return cancelled
    _svc().events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return {"status": "deleted", "id": event_id}


@tool
def quick_add_event(text: str, calendar_id: str = "primary") -> dict:
    """Create an event from a natural-language description (e.g. 'Lunch with Sam
    tomorrow at noon'), using Google Calendar's own text parsing. Requires human approval."""
    cancelled = _confirm("quick_add_event", text=text)
    if cancelled:
        return cancelled
    event = _svc().events().quickAdd(calendarId=calendar_id, text=text).execute()
    return {"status": "created", **_summarize(event)}
