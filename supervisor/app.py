import uuid

import streamlit as st
from streamlit_geolocation import streamlit_geolocation
from langgraph.types import Command

from agent import build_supervisor

st.set_page_config(page_title="Nearby Assistant", page_icon="🧭")
st.title("🧭 Nearby Assistant")
st.caption("Ask about nearby places, email, or your calendar — one assistant, three specialists.")


@st.cache_resource
def get_agent():
    return build_supervisor()


agent = get_agent()

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "pending_interrupt" not in st.session_state:
    st.session_state.pending_interrupt = None
if "location" not in st.session_state:
    st.session_state.location = None

config = {"configurable": {"thread_id": st.session_state.thread_id}}

with st.sidebar:
    st.subheader("Your location")
    loc = streamlit_geolocation()
    if loc and loc.get("latitude") and loc.get("longitude"):
        st.session_state.location = {"latitude": loc["latitude"], "longitude": loc["longitude"]}
    if st.session_state.location:
        st.success(
            f"Lat: {st.session_state.location['latitude']:.5f}, "
            f"Lng: {st.session_state.location['longitude']:.5f}"
        )
    else:
        st.info("Click the location marker above to share your location, or just name a place in chat.")


def extract_reply(messages):
    """Find the last message with real text. The supervisor sometimes ends its
    turn with an empty-content message once a specialist has already answered,
    so messages[-1] alone isn't reliable."""
    for message in reversed(messages):
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
            if text.strip():
                return text
    return "Done."


def advance(result):
    """Drive the graph forward; stop and stash state if it hits an interrupt."""
    if "__interrupt__" in result:
        st.session_state.pending_interrupt = result["__interrupt__"][0].value
    else:
        st.session_state.pending_interrupt = None
        reply = extract_reply(result["messages"])
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
    user_input = st.chat_input("Ask about nearby places, your email, or your calendar...")
    if user_input:
        st.session_state.display_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Fold location into the message text itself (rather than a separate
        # SystemMessage) since the supervisor's history is checkpointer-owned
        # here — we can't easily strip a stale SystemMessage before each turn.
        agent_input = user_input
        if st.session_state.location:
            loc = st.session_state.location
            agent_input = (
                f"[User's current coordinates: latitude={loc['latitude']}, "
                f"longitude={loc['longitude']}. Use these directly for 'near me' "
                f"requests instead of geocoding.]\n{user_input}"
            )

        with st.chat_message("assistant"):
            with st.spinner("Working..."):
                result = agent.invoke({"messages": [("user", agent_input)]}, config)
        advance(result)
        st.rerun()
