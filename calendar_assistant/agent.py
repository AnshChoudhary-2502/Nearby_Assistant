from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from calendar_assistant.tools import (
    create_event,
    delete_event,
    get_event,
    list_calendars,
    list_events,
    quick_add_event,
    search_events,
    update_event,
)

TOOLS = [
    list_calendars,
    list_events,
    search_events,
    get_event,
    create_event,
    update_event,
    delete_event,
    quick_add_event,
]

SYSTEM_PROMPT = (
    "You are a Google Calendar assistant. You can list calendars, list and "
    "search events, look up event details, and create, update, delete, or "
    "quick-add events on the user's behalf. "
    "Creating, updating, deleting, and quick-adding events require human "
    "approval and will pause for confirmation before taking effect — "
    "explain what you're about to do when proposing one of those actions. "
    "Always use search_events or list_events to find the right event before "
    "acting on it, confirm ambiguous details like date, time, and timezone "
    "with the user, and assume the 'primary' calendar unless told otherwise."
)


def build_calendar_agent():
    # Interrupts inside a tool discard the results of any *other* tool calls
    # made in the same batch, since the whole step aborts before it's
    # checkpointed. Forcing one tool call per turn avoids orphaning those
    # sibling calls when a sensitive tool pauses for approval.
    llm = ChatAnthropic(model="claude-haiku-4-5").bind_tools(TOOLS, parallel_tool_calls=False)
    checkpointer = MemorySaver()
    return create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT, checkpointer=checkpointer)
