# Workshop TODO Finder

Use this file as the starting point for attendees.

## Fastest way in VS Code

1. Open Search (Ctrl+Shift+F).
2. Search for: TODO(Workshop|:)
3. Files to include: apps/gateway/**,mcp_servers/assistant/**
4. Toggle .* (regex) ON.

## Suggested coding order

1. apps/gateway/tools.py
   - Implement web_search
   - Implement notes (add/list/search)
2. apps/gateway/agent.py
   - Implement Gemini request loop
   - Parse and execute tool calls
3. apps/gateway/groq_fallback.py
   - Implement fallback HTTP call and tool loop
4. apps/gateway/tts_engine.py
   - Implement model import/load and synthesis
5. apps/gateway/pipeline.py
   - Implement transcribe and startup wiring
6. apps/gateway/wake_word.py
   - Implement wake-word model load and score

## Terminal command alternative

PowerShell:
Select-String -Path apps\gateway\*.py,mcp_servers\assistant\*.py -Pattern "TODO" -CaseSensitive:$false

## Completion convention

When a TODO is done, replace the comment with:
DONE(Workshop): short note about what was implemented.

This keeps progress visible for all attendees.
