# Nearby Assistant

Two independent LangGraph assistants, each with its own Streamlit chat UI:

- **`places/`** — finds nearby places (gyms, restaurants, cafes, ...) using Google Maps Platform APIs.
- **`gmail/`** — reads, searches, and manages Gmail, with human-in-the-loop approval before any sending, replying, deleting, or archiving.

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
   | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) — used by both assistants |
   | `GOOGLE_MAPS_API_KEY` | [Google Cloud Console](https://console.cloud.google.com/google/maps-apis) — enable **Places API (New)** and **Geocoding API**, and make sure billing is enabled |

## Places assistant

The assistant is a LangGraph ReAct agent (`create_react_agent`) with two tools:

- **`geocode_location`** — resolves a place name/address typed by the user (e.g. "Koramangala, Bangalore") into latitude/longitude, via the Google **Geocoding API**.
- **`find_nearby_places`** — searches for places of a given type (`restaurant`, `gym`, `cafe`, ...) around coordinates, via the Google **Places API (New)** Nearby Search endpoint.

The Streamlit frontend additionally requests the browser's GPS location (via `streamlit-geolocation`) so the user can say "near me" without typing an address.

**Run it:**
```bash
uv run streamlit run places/app.py
```
Grant location access when prompted in the sidebar, then chat as usual (e.g. "gyms near me", "restaurants near Koramangala"). Browser geolocation only works over `localhost` or HTTPS.

**Terminal REPL:**
```bash
uv run places/main.py
```

## Gmail assistant

A LangGraph ReAct agent with 9 tools covering the Gmail API: `read_emails`, `search_email`, `list_labels`, `send_email`, `reply_email`, `delete_email`, `mark_read`, `mark_unread`, `archive_email`, `create_draft`.

Sending, replying, deleting, and archiving pause the graph via LangGraph's `interrupt()` and require explicit approval in the UI before taking effect — read-only and reversible actions (reading, searching, listing labels, marking read/unread, drafting) run without interruption. `delete_email` moves messages to Trash rather than permanently deleting them.

**One-time setup:** create an OAuth client (Desktop App type) in [Google Cloud Console](https://console.cloud.google.com/apis/credentials) with the Gmail API enabled, and download it as `gmail/credentials.json`.

**Run it:**
```bash
uv run streamlit run gmail/app.py
```
First run opens a browser for OAuth consent; the refresh token is cached in `gmail/token.json` afterwards. When the agent proposes a sensitive action, approve or deny it in the chat before it proceeds.

## Project structure

```
places/
  main.py       # LangGraph agent + Google Maps tools
  app.py        # Streamlit chat frontend
gmail/
  client.py     # Gmail OAuth + API service builder
  tools.py      # LangChain tools wrapping the Gmail API (human-in-the-loop on sensitive ones)
  agent.py      # LangGraph agent assembly (checkpointer + tools)
  app.py        # Streamlit chat frontend with approve/deny UI
  credentials.json, token.json   # gitignored — created during OAuth setup
example.env     # Template for required API keys / config
```

## Possible extensions

- **Routes API** — real driving/walking distance and ETA instead of straight-line radius ranking
- **Places Photo** — show a photo for each result
- **Maps JavaScript API** — render an interactive map with pins instead of text-only results
- **Static Maps API** — lightweight static map image alternative
- **Gmail attachments** — read/send with file attachments
