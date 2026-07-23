"""DEPRECATED shim — use apps.gateway.main instead.

Kept so older docs/commands still work:
    uvicorn api.main:app --port 8000

New unified app (preferred):
    uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000
"""
from apps.gateway.main import app  # noqa: F401

print(
    "[deprecated] api.main is a shim; prefer `uvicorn apps.gateway.main:app` "
    "(same /health /stt /tts /v1/turn routes)."
)
