# Copyright 2025 ODIN Protocol Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Signet Protocol - Simple HTTP Client
One-line helper for verified AI-to-AI communications.
"""

import json
import uuid
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SignetResponse:
    """Response from Signet Protocol exchange."""
    success: bool
    trace_id: str
    normalized: Optional[Dict[str, Any]] = None
    receipt: Optional[Dict[str, Any]] = None
    forwarded: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None

class SignetClient:
    """
    Simple HTTP client for Signet Protocol.
    
    Usage:
        client = SignetClient("http://localhost:8088", "your-api-key")
        result = client.exchange({"amount": 100, "currency": "USD"})
    """
    
    def __init__(
        self,
        signet_url: str,
        api_key: str,
        forward_url: Optional[str] = None,
        tenant: Optional[str] = None,
        timeout: int = 30
    ):
        self.signet_url = signet_url.rstrip('/')
        self.api_key = api_key
        self.forward_url = forward_url
        self.tenant = tenant or "client"
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "X-SIGNET-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "signet-client-python/1.0"
        })
    
    def exchange(
        self,
        data: Dict[str, Any],
        forward_url: Optional[str] = None,
        trace_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> SignetResponse:
        """
        Send data through Signet Protocol for verification.
        
        Args:
            data: The data to verify (will be converted to invoice format)
            forward_url: Override default forward URL
            trace_id: Specific trace ID (auto-generated if not provided)
            idempotency_key: Idempotency key (auto-generated if not provided)
            
        Returns:
            SignetResponse with verification results
        """
        try:
            # Generate IDs if not provided
            if not trace_id:
                trace_id = f"{self.tenant}-{uuid.uuid4()}"
            if not idempotency_key:
                idempotency_key = f"{trace_id}-{uuid.uuid4()}"
            
            # Convert data to Signet payload format
            payload = self._create_payload(data, trace_id, forward_url)
            
            # Set request headers
            headers = {
                "X-SIGNET-Idempotency-Key": idempotency_key
            }
            
            # Make request
            response = self.session.post(
                f"{self.signet_url}/v1/exchange",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            # Parse response
            return self._parse_response(response, trace_id)
            
        except requests.RequestException as e:
            return SignetResponse(
                success=False,
                trace_id=trace_id or "unknown",
                error=f"Request failed: {str(e)}"
            )
        except Exception as e:
            return SignetResponse(
                success=False,
                trace_id=trace_id or "unknown",
                error=f"Unexpected error: {str(e)}"
            )
    
    def get_chain(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve the complete receipt chain for a trace.
        
        Args:
            trace_id: The trace ID to retrieve
            
        Returns:
            List of receipts or None if not found
        """
        try:
            response = self.session.get(
                f"{self.signet_url}/v1/receipts/chain/{trace_id}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception:
            return None
    
    def export_chain(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a signed receipt chain bundle.
        
        Args:
            trace_id: The trace ID to export
            
        Returns:
            Signed export bundle or None if not found
        """
        try:
            response = self.session.get(
                f"{self.signet_url}/v1/receipts/export/{trace_id}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception:
            return None
    
    def health_check(self) -> bool:
        """
        Check if Signet Protocol server is healthy.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.signet_url}/healthz",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _create_payload(
        self,
        data: Dict[str, Any],
        trace_id: str,
        forward_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert user data to Signet Protocol payload format."""
        
        # Use provided forward_url or instance default
        final_forward_url = forward_url or self.forward_url
        
        # Convert data to function arguments JSON
        arguments_json = json.dumps(data)
        
        return {
            "payload_type": "openai.tooluse.invoice.v1",
            "target_type": "invoice.iso20022.v1",
            "trace_id": trace_id,
            "payload": {
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": "create_invoice",
                        "arguments": arguments_json
                    }
                }]
            },
            "forward_url": final_forward_url
        }
    
    def _parse_response(self, response: requests.Response, trace_id: str) -> SignetResponse:
        """Parse HTTP response into SignetResponse."""
        try:
            if response.status_code == 200:
                data = response.json()
                return SignetResponse(
                    success=True,
                    trace_id=data.get("trace_id", trace_id),
                    normalized=data.get("normalized"),
                    receipt=data.get("receipt"),
                    forwarded=data.get("forwarded"),
                    status_code=200
                )
            else:
                # Try to parse error response
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", f"HTTP {response.status_code}")
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                
                return SignetResponse(
                    success=False,
                    trace_id=trace_id,
                    error=error_msg,
                    status_code=response.status_code
                )
                
        except Exception as e:
            return SignetResponse(
                success=False,
                trace_id=trace_id,
                error=f"Response parsing failed: {str(e)}",
                status_code=response.status_code
            )


# Convenience functions for one-liner usage
def signet_exchange(
    signet_url: str,
    api_key: str,
    data: Dict[str, Any],
    forward_url: Optional[str] = None,
    **kwargs
) -> SignetResponse:
    """
    One-liner to send data through Signet Protocol.
    
    Usage:
        result = signet_exchange(
            "http://localhost:8088",
            "your-api-key", 
            {"amount": 100, "currency": "USD"},
            "https://webhook.site/your-url"
        )
    """
    client = SignetClient(signet_url, api_key, forward_url)
    return client.exchange(data, **kwargs)

def verify_invoice(
    signet_url: str,
    api_key: str,
    invoice_data: Dict[str, Any],
    webhook_url: Optional[str] = None
) -> SignetResponse:
    """
    One-liner to verify invoice data through Signet Protocol.
    
    Usage:
        result = verify_invoice(
            "http://localhost:8088",
            "your-api-key",
            {
                "invoice_id": "INV-001",
                "amount": 1000.00,
                "currency": "USD",
                "customer_name": "Acme Corp",
                "description": "Professional services"
            },
            "https://your-system.com/webhook"
        )
    """
    return signet_exchange(signet_url, api_key, invoice_data, webhook_url)


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    client = SignetClient(
        signet_url="http://localhost:8088",
        api_key="demo_key",
        forward_url="https://postman-echo.com/post"
    )
    
    # Test health check
    if client.health_check():
        print("✅ Signet Protocol server is healthy")
        
        # Test exchange
        invoice_data = {
            "invoice_id": "INV-12345",
            "amount": 1500.00,
            "currency": "USD",
            "customer_name": "Example Customer",
            "description": "Consulting services"
        }
        
        result = client.exchange(invoice_data)
        
        if result.success:
            print(f"✅ Exchange successful!")
            print(f"   Trace ID: {result.trace_id}")
            print(f"   Receipt Hash: {result.receipt.get('receipt_hash') if result.receipt else 'N/A'}")
            print(f"   Forwarded: {'Yes' if result.forwarded else 'No'}")
            
            # Retrieve the chain
            chain = client.get_chain(result.trace_id)
            if chain:
                print(f"   Chain Length: {len(chain)} receipts")
            
            # Export the chain
            export = client.export_chain(result.trace_id)
            if export:
                print(f"   Export Bundle: {len(export.get('chain', []))} receipts")
        else:
            print(f"❌ Exchange failed: {result.error}")
    else:
        print("❌ Signet Protocol server is not available")
    
    # Test one-liner
    print("\n--- One-liner test ---")
    result = verify_invoice(
        "http://localhost:8088",
        "demo_key",
        {
            "invoice_id": "INV-ONELINER",
            "amount": 500.00,
            "currency": "USD",
            "customer_name": "One-liner Customer"
        }
    )
    
    print(f"One-liner result: {'✅ Success' if result.success else '❌ Failed'}")
    if result.error:
        print(f"Error: {result.error}")
