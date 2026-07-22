from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from gmail_assistant.tools import (
    archive_email,
    create_draft,
    delete_email,
    list_labels,
    mark_read,
    mark_unread,
    read_emails,
    reply_email,
    search_email,
    send_email,
)

TOOLS = [
    read_emails,
    search_email,
    list_labels,
    send_email,
    reply_email,
    delete_email,
    mark_read,
    mark_unread,
    archive_email,
    create_draft,
]

SYSTEM_PROMPT = (
    "You are a Gmail assistant. You can read, search, send, reply to, "
    "delete, archive, and label emails on the user's behalf. "
    "Sending, replying, deleting, and archiving emails require human "
    "approval and will pause for confirmation before taking effect — "
    "explain what you're about to do when proposing one of those actions. "
    "Always use search_email or read_emails to find the right message "
    "before acting on it, and confirm details like recipient and subject "
    "with the user if they're ambiguous."
)


def build_gmail_agent():
    # Interrupts inside a tool discard the results of any *other* tool calls
    # made in the same batch, since the whole step aborts before it's
    # checkpointed. Forcing one tool call per turn avoids orphaning those
    # sibling calls when a sensitive tool pauses for approval.
    llm = ChatAnthropic(model="claude-haiku-4-5").bind_tools(TOOLS, parallel_tool_calls=False)
    checkpointer = MemorySaver()
    return create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT, checkpointer=checkpointer)
