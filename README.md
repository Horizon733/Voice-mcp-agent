# mcp-voice

Local voice agent: **STT** → **Gemini 2.5 Flash** (+ **MCP tools**) → **Jarvis TTS**.

| Mode | Best for |
|---|---|
| **Docker Compose (CPU)** | Same on Windows + Mac |
| **Native Windows + CUDA** | Fastest TTS |
| **Native Mac (MPS/CPU)** | Apple Silicon |

## Talk to the agent (Phase 3)

Terminal 1 — gateway:
```bash
# after venv + deps + voices/jarvis_conds.pt + GEMINI_API_KEY in .env
uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000
```

Terminal 2 — Jarvis Orb UI:
```bash
cd apps/jarvis-orb
npm install
npm run dev
```

Open **http://127.0.0.1:5173** → hold **HOLD TO TALK** → release → hear Jarvis.

### Simpler workshop mode (no gateway)

If attendees only need a minimal local flow (agent + MCP tools + voice), skip FastAPI/UI and run one script:

```bash
python scripts/voice_agent_cli.py --text "Remember my workshop is Friday" --print-tools
```

Or with audio input:

```bash
python scripts/voice_agent_cli.py --audio-in sample.wav --audio-out reply.wav --print-tools
```

This uses the same core pipeline modules but avoids HTTP routes/websockets during the workshop.

### Optional: wake word ("Hey Jarvis")

Say "Hey Jarvis" instead of holding the button. Uses [openWakeWord](https://github.com/dscripka/openWakeWord)'s pretrained `hey_jarvis` model, running fully local on the gateway (CPU via ONNX Runtime — no account, no API key, no per-attendee signup). The mic stream for wake-word listening never leaves your machine except to your own gateway process.

The model auto-downloads the first time the gateway starts (needs internet once; cached after that). Click **ENABLE WAKE WORD** in the UI, then say "Hey Jarvis" followed by your request — it auto-stops recording after you go quiet. If `WAKE WORD UNAVAILABLE` shows up, check the gateway logs for the download/load warning.

### MCP tools (no extra API keys)

| Tool | What it does |
|---|---|
| `web_search` | DuckDuckGo web search |
| `notes` | Unified memory tool with `action=add|list|search` (SQLite in `data/notes.db`) |

If Gemini fails at runtime and Groq fallback is configured, the fallback path also runs the same `web_search` and `notes` tools before answering.

Try saying:
- “Search the web for the latest AI chips headlines.”
- “Remember that my workshop is on Friday.”
- “What notes do you have saved for me?”

Standalone MCP server (for Cursor / other MCP clients):
```bash
python -m mcp_servers.assistant.server
```

---

## Quick start (Docker)

```bash
cp .env.example .env          # set GEMINI_API_KEY
# voices/jarvis-5s.wav (>5s)

docker compose build
docker compose run --rm gateway python scripts/build_jarvis_conds.py --device cpu --backend turbo
docker compose up
```

`docker compose up` now starts two services:
- `gateway` (FastAPI on `:8000`)
- `mcp-server` (stdio MCP server for external MCP clients)

If you only want the HTTP gateway:
```bash
docker compose up gateway
```

If you only want the standalone MCP server:
```bash
docker compose up mcp-server
```

UI still runs on the host:
```bash
cd apps/jarvis-orb && npm install && npm run dev
```

### NVIDIA GPU Docker (Windows/Linux only)
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

Gateway-only on GPU hosts:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build gateway
```

---

## Native setup (no Docker)

Python **3.11 or 3.12**:

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Mac:     source .venv/bin/activate

pip install -U pip wheel
pip install "setuptools>=70,<81"

# Windows NVIDIA:
pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
# Mac / CPU:
# pip install torch==2.6.0 torchaudio==2.6.0

pip install -r requirements.txt
cp .env.example .env   # GEMINI_API_KEY, TTS_DEVICE=auto
python scripts/build_jarvis_conds.py --device auto --backend turbo
uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000
```

Then start `apps/jarvis-orb` as above.

### Improve Transcription Speed/Quality (recommended first)

The gateway now supports STT tuning via `.env`:

```bash
# model
WHISPER_MODEL=medium.en

# decode profile: fast | balanced | accurate
STT_PROFILE=balanced

# auto chooses int8_float16 on cuda, int8 otherwise
STT_COMPUTE_TYPE=auto

# force English for better speed/stability (or use auto)
STT_LANGUAGE=en

# trim silence and tune search width
STT_VAD_FILTER=true
STT_BEAM_SIZE=2
```

Recommended low-latency setup on NVIDIA + conda:

```bash
WHISPER_MODEL=medium.en
STT_DEVICE=cuda
STT_PROFILE=fast
STT_COMPUTE_TYPE=auto
STT_LANGUAGE=en
STT_VAD_FILTER=true
STT_BEAM_SIZE=1
```

If GPU memory is still tight, use `small.en` with `STT_PROFILE=fast`.

---

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | status + mcp tool list |
| POST | `/stt` | audio → text |
| POST | `/tts` | text → wav |
| POST | `/v1/turn` | audio → transcript + tools + reply + wav |
| POST | `/v1/turn/text` | text → tools + reply + wav (debug) |
| WS | `/ws/turn` | binary audio in → JSON events out |

---

## Layout

```
apps/gateway/     FastAPI + STT/TTS + Gemini agent + tools
apps/jarvis-orb/  React orb UI (voice + wake word)
mcp_servers/      MCP stdio server (same tools)
data/notes.db     saved notes (created at runtime)
voices/           jarvis wav + conds
scripts/          smoke tests
```

Workshop guide: see `WORKSHOP.md`.

## Phase status

- [x] Phase 1 — STT + TTS + conds
- [x] Phase 2 — Gemini turn pipeline
- [x] Phase 3 — MCP tools + React voice UI
