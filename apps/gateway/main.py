"""Unified gateway: STT, Gemini+MCP tools, TTS, and voice WebSocket.

Run locally:
    uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import base64
import json
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from apps.gateway import config
from apps.gateway.pipeline import ConfigError, models, run_turn, synthesize, transcribe
from apps.gateway.wake_word import FRAME_SAMPLES, WAKE_THRESHOLD


@asynccontextmanager
async def lifespan(_app: FastAPI):
    models.load()
    yield


app = FastAPI(
    title="mcp-voice gateway",
    description="STT + Gemini 2.5 Flash + MCP tools + Jarvis TTS",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)


class TextTurnRequest(BaseModel):
    text: str = Field(..., min_length=1)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "whisper_model": config.WHISPER_MODEL,
        "stt_device": config.STT_DEVICE,
        "stt_profile": config.STT_PROFILE,
        "stt_compute_type": config.STT_COMPUTE_TYPE,
        "stt_language": config.STT_LANGUAGE,
        "tts_device": models.tts_device,
        "tts_backend": models.tts_backend,
        "jarvis_conds_loaded": models.conds_loaded,
        "gemini_configured": models.gemini is not None,
        "gemini_model": config.GEMINI_MODEL,
        "groq_fallback_enabled": models.groq_enabled,
        "groq_model": config.GROQ_MODEL,
        "mcp_tools": models.mcp_tools,
        "wake_word_loaded": models.wake_word.loaded,
    }


@app.post("/stt")
async def stt(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    try:
        text = transcribe(audio_bytes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"text": text}


@app.post("/tts")
async def tts(req: TTSRequest):
    try:
        audio = synthesize(req.text)
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=audio, media_type="audio/wav")


@app.post("/v1/turn")
async def turn(file: UploadFile = File(...)):
    """Full turn: audio -> STT -> Gemini(+MCP tools) -> Jarvis TTS."""
    audio_bytes = await file.read()
    try:
        result = run_turn(audio_bytes)
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return JSONResponse(
        {
            "transcript": result["transcript"],
            "reply_text": result["reply_text"],
            "tools": result.get("tools", []),
            "audio_base64": base64.b64encode(result["audio_out"]).decode("ascii"),
            "audio_format": "wav",
        }
    )


@app.post("/v1/turn/text")
async def turn_text(req: TextTurnRequest):
    """Text-only turn (useful for debugging tools without mic)."""
    from apps.gateway.pipeline import ask_gemini

    try:
        reply_text, tool_trace = ask_gemini(req.text)
        audio = synthesize(reply_text)
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return JSONResponse(
        {
            "transcript": req.text,
            "reply_text": reply_text,
            "tools": tool_trace,
            "audio_base64": base64.b64encode(audio).decode("ascii"),
            "audio_format": "wav",
        }
    )


@app.websocket("/ws/turn")
async def ws_turn(websocket: WebSocket):
    """Push-to-talk path: client sends one binary audio blob, then receives JSON events.

    Client protocol:
      1) connect
      2) send binary audio (webm/wav/ogg bytes)
      3) receive JSON events: status | transcript | tool | reply_text | audio | done | error
    """
    await websocket.accept()
    events: list[dict] = []

    try:
        audio_bytes = await websocket.receive_bytes()

        def on_event(event: dict) -> None:
            events.append(event)

        try:
            result = run_turn(audio_bytes, on_event=on_event)
        except ConfigError as exc:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
            await websocket.close()
            return

        # Replay collected events, injecting audio at the end before done
        for event in events:
            if event.get("type") == "done":
                continue
            await websocket.send_text(json.dumps(event, default=str))

        await websocket.send_text(
            json.dumps(
                {
                    "type": "audio",
                    "format": "wav",
                    "base64": base64.b64encode(result["audio_out"]).decode("ascii"),
                }
            )
        )
        await websocket.send_text(json.dumps({"type": "done"}))
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/wake")
async def ws_wake(websocket: WebSocket):
    """Continuous mic stream -> openWakeWord 'hey jarvis' detector.

    Client protocol:
      1) connect
      2) stream raw 16-bit PCM mono 16kHz frames, any chunk size, back-to-back
      3) receive {"type": "wake", "score": float} whenever the wake word fires
    """
    await websocket.accept()
    if not models.wake_word.loaded:
        await websocket.send_text(
            json.dumps({"type": "error", "message": "Wake-word model not loaded on the gateway"})
        )
        await websocket.close()
        return

    buffer = np.array([], dtype=np.int16)
    try:
        while True:
            chunk = await websocket.receive_bytes()
            buffer = np.concatenate([buffer, np.frombuffer(chunk, dtype=np.int16)])
            while len(buffer) >= FRAME_SAMPLES:
                frame, buffer = buffer[:FRAME_SAMPLES], buffer[FRAME_SAMPLES:]
                score = models.wake_word.score(frame)
                if score >= WAKE_THRESHOLD:
                    await websocket.send_text(json.dumps({"type": "wake", "score": score}))
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
