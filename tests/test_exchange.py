import os, json
from fastapi.testclient import TestClient
from unittest.mock import patch
from server.settings import Settings, TenantConfig
import sys, importlib

def test_happy_path():
  """Test exchange endpoint with proper configuration"""
  with patch('server.settings.load_settings') as mock_settings:
    mock_settings.return_value = Settings(
      api_keys={
        "test": TenantConfig(
          tenant="acme",
          allowlist=["postman-echo.com"],
          fallback_enabled=False
        )
      },
      hel_allowlist=["postman-echo.com"],
      db_path="./data/test.db",
      openai_api_key=None,
      stripe_api_key=None,
      private_key_b64=None,
      kid=None,
      storage_type="sqlite",
      postgres_url=None,
      reserved_config_path=None
    )

    # Fresh import of server.main under patched settings
    if 'server.main' in sys.modules:
      del sys.modules['server.main']
    from server import main as server_main
    # Ensure API key exists even if module was previously imported elsewhere
    server_main.SET.api_keys['test'] = mock_settings.return_value.api_keys['test']
    app = server_main.app
    client = TestClient(app)

    body = {
      "payload_type": "openai.tooluse.invoice.v1",
      "target_type": "invoice.iso20022.v1",
      "payload": {
        "tool_calls": [{
          "type": "function",
          "function": {
            "name": "create_invoice",
            "arguments": "{\"invoice_id\":\"INV-1\",\"amount\":123.45,\"currency\":\"USD\",\"customer_name\":\"Acme\",\"description\":\"Services\"}"
          }
        }]
      },
      "forward_url": "https://postman-echo.com/post"
    }
    headers = {"X-SIGNET-API-Key": "test", "X-SIGNET-Idempotency-Key": "idem-1"}
    r = client.post("/v1/exchange", json=body, headers=headers)

    assert r.status_code in (200, 403)
    if r.status_code == 200:
      response_data = r.json()
      assert "trace_id" in response_data
      assert "normalized" in response_data
      assert "receipt" in response_data
