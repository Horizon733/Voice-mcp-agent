# talk-to-your-tools

Voice-first agentic AI workshop demo using Gemini + MCP with a phased implementation plan.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- **macOS (Apple Silicon) only**: PyAudio needs the native PortAudio library to build —
  install it first with `brew install portaudio`. Whisper transcription runs on CPU on
  Mac (faster-whisper/CTranslate2 has no Apple GPU/MPS backend), which is expected and
  still fast enough for real-time use.
- **Windows/Linux with an NVIDIA GPU**: `uv sync` installs a CUDA-enabled build of
  torch/torchaudio automatically (see `[tool.uv.sources]` in `pyproject.toml`). Without
  a CUDA-capable GPU, remove that override or let it fall back to CPU.

## Quickstart

1. Install `uv`:
   - Windows (PowerShell):
     ```powershell
     irm https://astral.sh/uv/install.ps1 | iex
     ```
   - macOS/Linux:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Copy environment template:
   ```bash
   cp .env.example .env
   ```
   On Windows cmd:
   ```cmd
   copy .env.example .env
   ```
4. Start the scaffold app:
   ```bash
   python -m src.main
   ```

## Project Layout

- `src/config.py`: env vars, model names, and constants
- `src/stt.py`: speech-to-text module scaffold (Phase 1)
- `src/tts.py`: text-to-speech module scaffold (Phase 2)
- `src/agent.py`: Gemini orchestration scaffold (Phase 3)
- `src/main.py`: entry point scaffold (Phase 4)
- `mcp_servers/*.py`: MCP server scaffolds (Phase 5)
- `mcp_config.json`: MCP server client config
