#!/usr/bin/env python3
"""
Signet Protocol Python Client SDK

Simple HTTP client for interacting with Signet Protocol servers.
Provides easy-to-use functions for verified exchanges.
"""

import json
import uuid
from typing import Dict, Any, Optional

import httpx


class SignetClient:
    """Signet Protocol HTTP client"""
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        """Initialize client with server URL and API key"""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        
        self.headers = {
            'Content-Type': 'application/json',
            'X-SIGNET-API-Key': api_key,
            'User-Agent': 'Signet-Python-SDK/1.0'
        }
    
    async def exchange(
        self,
        payload_type: str,
        target_type: str,
        payload: Dict[str, Any],
        forward_url: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform a verified exchange"""
        
        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"client-{uuid.uuid4().hex[:16]}"
        
        # Prepare request
        request_data = {
            'payload_type': payload_type,
            'target_type': target_type,
            'payload': payload,
            'forward_url': forward_url,
            'idempotency_key': idempotency_key
        }
        
        headers = self.headers.copy()
        headers['X-SIGNET-Idempotency-Key'] = idempotency_key
        
        # Make request
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/exchange",
                json=request_data,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
    
    async def get_receipt(self, receipt_id: str) -> Dict[str, Any]:
        """Get a receipt by ID"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/v1/receipts/{receipt_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
    
    async def export_audit_trail(self, tenant_id: str) -> Dict[str, Any]:
        """Export audit trail bundle"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/v1/export/{tenant_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check server health"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/healthz")
            
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()


# Convenience functions
async def verify_invoice(
    server_url: str,
    api_key: str,
    invoice_data: Dict[str, Any],
    forward_url: str
) -> Dict[str, Any]:
    """One-line invoice verification"""
    client = SignetClient(server_url, api_key)
    
    # Convert invoice to OpenAI tool use format
    payload = {
        'tool_calls': [{
            'type': 'function',
            'function': {
                'name': 'create_invoice',
                'arguments': json.dumps(invoice_data)
            }
        }]
    }
    
    return await client.exchange(
        payload_type='openai.tooluse.invoice.v1',
        target_type='invoice.iso20022.v1',
        payload=payload,
        forward_url=forward_url
    )


async def quick_exchange(
    server_url: str,
    api_key: str,
    data: Dict[str, Any],
    forward_url: str
) -> Dict[str, Any]:
    """Quick exchange with automatic type detection"""
    client = SignetClient(server_url, api_key)
    
    return await client.exchange(
        payload_type='generic.json.v1',
        target_type='generic.json.v1',
        payload=data,
        forward_url=forward_url
    )


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example():
        # Initialize client
        client = SignetClient(
            base_url="http://localhost:8088",
            api_key="demo_key"
        )
        
        # Check health
        health = await client.health_check()
        print(f"Server health: {health}")
        
        # Perform exchange
        result = await client.exchange(
            payload_type="openai.tooluse.invoice.v1",
            target_type="invoice.iso20022.v1",
            payload={
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": "create_invoice",
                        "arguments": '{"invoice_id":"INV-001","amount":1000,"currency":"USD"}'
                    }
                }]
            },
            forward_url="https://webhook.site/your-unique-url"
        )
        
        print(f"Exchange result: {result}")
    
    # Run example
    asyncio.run(example())