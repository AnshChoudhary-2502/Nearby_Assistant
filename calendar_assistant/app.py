import uuid

import streamlit as st
from langgraph.types import Command

from agent import build_calendar_agent

st.set_page_config(page_title="Calendar Assistant", page_icon="📅")
st.title("📅 Calendar Assistant")


@st.cache_resource
def get_agent():
    return build_calendar_agent()


agent = get_agent()

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "pending_interrupt" not in st.session_state:
    st.session_state.pending_interrupt = None

config = {"configurable": {"thread_id": st.session_state.thread_id}}


def advance(result):
    """Drive the graph forward; stop and stash state if it hits an interrupt."""
    if "__interrupt__" in result:
        st.session_state.pending_interrupt = result["__interrupt__"][0].value
    else:
        st.session_state.pending_interrupt = None
        reply = result["messages"][-1].content
        st.session_state.display_messages.append({"role": "assistant", "content": reply})


for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.pending_interrupt:
    payload = st.session_state.pending_interrupt
    with st.chat_message("assistant"):
        st.warning(f"⚠️ Approval required: **{payload['action']}**")
        for key, value in payload.items():
            if key != "action":
                st.markdown(f"**{key}:** {value}")
        col1, col2 = st.columns(2)
        approve = col1.button("✅ Approve", use_container_width=True)
        deny = col2.button("❌ Deny", use_container_width=True)

    if approve or deny:
        resume_value = "approve" if approve else "deny"
        with st.spinner("Working..."):
            result = agent.invoke(Command(resume=resume_value), config)
        advance(result)
        st.rerun()
else:
    user_input = st.chat_input("Ask me to check, create, or manage your calendar events...")
    if user_input:
        st.session_state.display_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Working..."):
                result = agent.invoke({"messages": [("user", user_input)]}, config)
        advance(result)
        st.rerun()
