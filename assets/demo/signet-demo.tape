Output signet-demo.gif

Set FontSize 16
Set Width 1000
Set Height 650

Type "uvicorn server.main:app --port 8088" Enter
Sleep 2000
Type "curl -s http://localhost:8088/healthz" Enter
Sleep 1200
Type "curl -s -X POST http://localhost:8088/v1/exchange -H 'X-SIGNET-API-Key: demo_key' -H 'X-SIGNET-Idempotency-Key: d1' -H 'Content-Type: application/json' -d '{\"payload_type\":\"openai.tooluse.invoice.v1\",\"target_type\":\"invoice.iso20022.v1\",\"payload\":{\"tool_calls\":[]}}' | jq '.receipt.cid'" Enter
Sleep 2500
Type "curl -s -X POST http://localhost:8088/v1/export/bundle -H 'X-SIGNET-API-Key: demo_key' -d '{\"trace_id\":\"demo-abc-123\"}' | jq '.receipts|length'" Enter
Sleep 1800
Type "# Demo complete" Enter
Sleep 1200
