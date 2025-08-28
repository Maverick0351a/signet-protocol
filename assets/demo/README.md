# Demo Asset Notes

Place generated screencast GIF/MP4 files in this folder.
Suggested tools:
- asciinema + agg (terminal)
- vhs (https://github.com/charmbracelet/vhs)
- screenkey (optional keystroke overlay)

Recommended flow:
1. Run local server (uvicorn ...)
2. Show: health check -> exchange -> export bundle -> verify offline
3. Keep under 15s total.

Example commands (captured):
```
uvicorn server.main:app --port 8088 &
curl -s http://localhost:8088/healthz
curl -s -X POST http://localhost:8088/v1/exchange -H "X-SIGNET-API-Key: demo_key" -H "X-SIGNET-Idempotency-Key: d1" -H "Content-Type: application/json" -d '{"payload_type":"openai.tooluse.invoice.v1","target_type":"invoice.iso20022.v1","payload":{"tool_calls":[]}}' | jq '.receipt.cid'
python - <<'PY'
from signet_verify import verify_receipt; import json,sys
r=json.load(sys.stdin) if False else {}
PY
```

Add final GIF as `assets/demo/signet-demo.gif`.
