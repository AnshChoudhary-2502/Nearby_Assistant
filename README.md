# Nearby Assistant

A conversational assistant that finds nearby places — gyms, restaurants, cafes, etc. — using Google Maps Platform APIs, built with [LangGraph](https://github.com/langchain-ai/langgraph) and served through a [Streamlit](https://streamlit.io/) chat UI.

## How it works

The assistant is a LangGraph ReAct agent (`create_react_agent`) with two tools:

- **`geocode_location`** — resolves a place name/address typed by the user (e.g. "Koramangala, Bangalore") into latitude/longitude, via the Google **Geocoding API**.
- **`find_nearby_places`** — searches for places of a given type (`restaurant`, `gym`, `cafe`, ...) around coordinates, via the Google **Places API (New)** Nearby Search endpoint.

The LLM (Claude, via `langchain-anthropic`) decides when to call each tool based on the conversation, then presents the results conversationally.

The Streamlit frontend additionally requests the browser's GPS location (via `streamlit-geolocation`) so the user can say "near me" without typing an address — the coordinates are injected into the agent's context each turn.

## Setup

1. Install dependencies (requires [`uv`](https://docs.astral.sh/uv/)):
   ```bash
   uv sync
   ```

2. Copy the example environment file and fill in your keys:
   ```bash
   cp example.env .env
   ```

   | Variable | Where to get it |
   |---|---|
   | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) |
   | `GOOGLE_MAPS_API_KEY` | [Google Cloud Console](https://console.cloud.google.com/google/maps-apis) — enable **Places API (New)** and **Geocoding API** on this key, and make sure billing is enabled on the project |

## Running it

**Streamlit chat UI (recommended):**
```bash
uv run streamlit run app.py
```
Grant location access when prompted in the sidebar, then chat as usual (e.g. "gyms near me", "restaurants near Koramangala").

Note: browser geolocation only works over `localhost` or HTTPS — if you deploy this, make sure it's served over HTTPS.

**Terminal REPL:**
```bash
uv run main.py
```

## Project structure

```
main.py    # LangGraph agent + Google Maps tools
app.py     # Streamlit chat frontend
example.env  # Template for required API keys
```

## Possible extensions

- **Routes API** — real driving/walking distance and ETA instead of straight-line radius ranking
- **Places Photo** — show a photo for each result
- **Maps JavaScript API** — render an interactive map with pins instead of text-only results
- **Static Maps API** — lightweight static map image alternative
