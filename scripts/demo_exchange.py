import os, json, uuid, requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8088")
API_KEY = os.getenv("SP_DEMO_KEY", os.getenv("AB_DEMO_KEY", "my_dev_key"))

def main():
    idem = str(uuid.uuid4())
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
    r = requests.post(f"{API_URL}/v1/exchange", json=body, headers={
        "X-SIGNET-API-Key": API_KEY,
        "X-SIGNET-Idempotency-Key": idem
    })
    print("status:", r.status_code)
    print(r.headers)
    print(json.dumps(r.json(), indent=2))

if __name__ == "__main__":
    main()
