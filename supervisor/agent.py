import sys
from pathlib import Path

# The three specialist packages (gmail_assistant, calendar_assistant,
# places_assistant) are no longer standalone entry points — they're only
# importable as packages from the repo root, which isn't on sys.path when
# this script runs from within supervisor/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph_supervisor import create_supervisor

from calendar_assistant.agent import build_calendar_agent
from gmail_assistant.agent import build_gmail_agent
from places_assistant.agent import build_agent as build_places_agent

SUPERVISOR_PROMPT = (
    "You are the front door for a personal assistant made up of three "
    "specialists: 'places_assistant', 'gmail_assistant', and "
    "'calendar_assistant'. Do not answer domain questions yourself — hand "
    "off to the right specialist(s).\n\n"
    "- places_assistant: finding nearby restaurants, gyms, cafes, and other "
    "places, given a location name or coordinates.\n"
    "- gmail_assistant: reading, searching, sending, replying to, deleting, "
    "archiving, and labeling email.\n"
    "- calendar_assistant: listing, searching, creating, updating, and "
    "deleting calendar events.\n\n"
    "For requests that span multiple specialists (e.g. 'find a nearby cafe "
    "and add it to my calendar for lunch tomorrow'), hand off to one "
    "specialist at a time and use its result to inform the next handoff. "
    "Some specialist actions pause for the user's approval before taking "
    "effect — if that happens, wait for the user's decision before "
    "continuing with any further handoffs. Once all specialists you need "
    "have responded, summarize the outcome for the user yourself."
)


def build_supervisor():
    places_agent = build_places_agent()
    places_agent.name = "places_assistant"

    gmail_agent = build_gmail_agent()
    gmail_agent.name = "gmail_assistant"

    calendar_agent = build_calendar_agent()
    calendar_agent.name = "calendar_assistant"

    model = ChatAnthropic(model="claude-haiku-4-5")
    checkpointer = MemorySaver()

    workflow = create_supervisor(
        agents=[places_agent, gmail_agent, calendar_agent],
        model=model,
        prompt=SUPERVISOR_PROMPT,
        # full_history + no synthetic handoff-back messages: when a specialist
        # pauses on interrupt(), create_supervisor's default "last_message"
        # trimming plus the handoff-back injection make it look like the
        # specialist already finished and returned control, which corrupts
        # the paused state and breaks resuming the approval.
        output_mode="full_history",
        add_handoff_back_messages=False,
    )
    return workflow.compile(checkpointer=checkpointer)
