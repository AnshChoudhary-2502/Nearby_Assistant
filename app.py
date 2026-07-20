import streamlit as st
from streamlit_geolocation import streamlit_geolocation
from langchain_core.messages import HumanMessage, SystemMessage

from main import build_agent

st.set_page_config(page_title="Nearby Assistant", page_icon="📍")
st.title("📍 Nearby Assistant")


@st.cache_resource
def get_agent():
    return build_agent()


agent = get_agent()

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []  # for rendering only
if "lc_messages" not in st.session_state:
    st.session_state.lc_messages = []  # full LangGraph conversation state
if "location" not in st.session_state:
    st.session_state.location = None

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

for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask about nearby gyms, restaurants, or cafes...")
if user_input:
    st.session_state.display_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Drop any stale location SystemMessage and re-insert the latest coordinates
    # so the agent always sees fresh location data without it piling up in history.
    st.session_state.lc_messages = [
        m for m in st.session_state.lc_messages if not isinstance(m, SystemMessage)
    ]
    if st.session_state.location:
        loc = st.session_state.location
        st.session_state.lc_messages.insert(
            0,
            SystemMessage(
                content=(
                    f"The user's current coordinates are latitude={loc['latitude']}, "
                    f"longitude={loc['longitude']}. Use these directly with "
                    "find_nearby_places when the user says 'near me' instead of "
                    "calling geocode_location."
                )
            ),
        )
    st.session_state.lc_messages.append(HumanMessage(content=user_input))

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            result = agent.invoke({"messages": st.session_state.lc_messages})
            st.session_state.lc_messages = result["messages"]
            reply = result["messages"][-1].content
            st.markdown(reply)

    st.session_state.display_messages.append({"role": "assistant", "content": reply})
