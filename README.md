# Nearby Assistant

One Streamlit chat assistant, backed by a LangGraph supervisor that routes each request to the right specialist:

- **`places_assistant/`** — finds nearby places (gyms, restaurants, cafes, ...) using Google Maps Platform APIs.
- **`gmail_assistant/`** — reads, searches, and manages Gmail, with human-in-the-loop approval before any sending, replying, deleting, or archiving.
- **`calendar_assistant/`** — reads, searches, and manages Google Calendar events, with human-in-the-loop approval before any create, update, delete, or quick-add.

The three specialists are internal packages, not standalone apps — `supervisor/` is the only entry point.

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
   | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) — used by the supervisor and all three specialists |
   | `GOOGLE_MAPS_API_KEY` | [Google Cloud Console](https://console.cloud.google.com/google/maps-apis) — enable **Places API (New)** and **Geocoding API**, and make sure billing is enabled |

3. **Gmail/Calendar OAuth (one-time):** create an OAuth client (Desktop App type) in [Google Cloud Console](https://console.cloud.google.com/apis/credentials) with the Gmail API and Google Calendar API enabled, and download the credentials as `gmail_assistant/credentials.json` and `calendar_assistant/credentials.json` respectively. The first request that touches each API opens a browser for consent; the refresh token is then cached in that package's `token.json`.

## Run it

```bash
uv run streamlit run supervisor/app.py
```

Grant location access when prompted in the sidebar to enable "near me" place searches. When the assistant proposes a sensitive Gmail/Calendar action, approve or deny it in the chat before it proceeds.

## How routing works

`supervisor/agent.py` builds all three specialist agents (each still a `create_react_agent` with its own tools and, for Gmail/Calendar, its own `interrupt()`-based approval flow) and wires them into a `langgraph-supervisor` graph with a single top-level checkpointer. The supervisor LLM reads the user's message and hands off to whichever specialist(s) it needs, one at a time, using each specialist's response to decide on further handoffs.

Two non-default settings matter for correctness: `output_mode="full_history"` and `add_handoff_back_messages=False`. The library's defaults trim message history and inject a "transferred back to supervisor" message as soon as a specialist's turn ends — including when that turn actually just paused on an approval `interrupt()`. That combination made the paused state look finished, breaking resume after approve/deny.

## Project structure

```
places_assistant/
  agent.py      # LangGraph agent + Google Maps tools
calendar_assistant/
  client.py     # Google Calendar OAuth + API service builder
  tools.py      # LangChain tools wrapping the Calendar API (human-in-the-loop on mutating ones)
  agent.py      # LangGraph agent assembly (checkpointer + tools)
  credentials.json, token.json   # gitignored — created during OAuth setup
gmail_assistant/
  client.py     # Gmail OAuth + API service builder
  tools.py      # LangChain tools wrapping the Gmail API (human-in-the-loop on sensitive ones)
  agent.py      # LangGraph agent assembly (checkpointer + tools)
  credentials.json, token.json   # gitignored — created during OAuth setup
supervisor/
  agent.py      # Builds the three specialists and wires them into a langgraph-supervisor graph
  app.py        # Streamlit chat frontend with approve/deny UI and location sharing
example.env     # Template for required API keys / config
```

## Possible extensions

- **Routes API** — real driving/walking distance and ETA instead of straight-line radius ranking
- **Places Photo** — show a photo for each result
- **Maps JavaScript API** — render an interactive map with pins instead of text-only results
- **Static Maps API** — lightweight static map image alternative
- **Gmail attachments** — read/send with file attachments
