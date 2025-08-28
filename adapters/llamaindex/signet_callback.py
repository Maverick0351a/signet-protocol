"""
Signet Protocol - LlamaIndex Integration
Callback handler for verified AI-to-AI communications in LlamaIndex.
"""

import json
import uuid
import requests
from typing import Any, Dict, List, Optional, Union
from llama_index.core.callbacks.base import BaseCallbackHandler
from llama_index.core.callbacks.schema import CBEventType, EventPayload

class SignetLlamaIndexHandler(BaseCallbackHandler):
    """
    LlamaIndex callback handler that routes tool calls through Signet Protocol.
    
    Usage:
        from signet_callback import SignetLlamaIndexHandler
        
        signet_handler = SignetLlamaIndexHandler(
            signet_url="http://localhost:8088",
            api_key="your-signet-api-key",
            forward_url="https://your-webhook.com/receive"
        )
        
        # Add to LlamaIndex service context
        from llama_index.core import Settings
        Settings.callback_manager.add_handler(signet_handler)
    """
    
    def __init__(
        self,
        signet_url: str,
        api_key: str,
        forward_url: Optional[str] = None,
        tenant: Optional[str] = None,
        auto_forward: bool = True,
        **kwargs
    ):
        super().__init__(
            event_starts_to_ignore=[],
            event_ends_to_ignore=[]
        )
        self.signet_url = signet_url.rstrip('/')
        self.api_key = api_key
        self.forward_url = forward_url
        self.tenant = tenant or "llamaindex"
        self.auto_forward = auto_forward
        self.session = requests.Session()
        
        # Track current trace for chaining
        self.current_trace_id = None
        self.verified_exchanges = []
    
    def on_event_start(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        """Called when an event starts."""
        if event_type == CBEventType.FUNCTION_CALL:
            # Generate trace ID for new conversation
            if not self.current_trace_id:
                self.current_trace_id = f"llamaindex-{uuid.uuid4()}"
            
            function_name = payload.get("function_call", {}).get("name", "unknown_function")
            print(f"🔗 Signet: Function '{function_name}' starting (trace: {self.current_trace_id})")
        
        return event_id
    
    def on_event_end(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when an event ends."""
        if event_type == CBEventType.FUNCTION_CALL:
            try:
                # Extract function call result
                function_call = payload.get("function_call", {})
                function_output = payload.get("function_call_response", "")
                
                # Parse and route through Signet if applicable
                if self._should_route_through_signet(function_call):
                    parsed_output = self._parse_function_output(function_output, function_call)
                    
                    if parsed_output:
                        receipt = self._send_to_signet(parsed_output)
                        if receipt:
                            self.verified_exchanges.append(receipt)
                            print(f"✅ Signet: Verified exchange recorded (hop: {receipt.get('hop')})")
                        else:
                            print("❌ Signet: Exchange verification failed")
            
            except Exception as e:
                print(f"⚠️ Signet: Error processing function output: {str(e)}")
        
        elif event_type == CBEventType.QUERY:
            # Query completed - export chain if we have multiple exchanges
            if len(self.verified_exchanges) > 1:
                self._export_chain()
    
    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """Start a new trace."""
        pass
    
    def end_trace(
        self,
        trace_id: Optional[str] = None,
        trace_map: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """End the current trace."""
        if self.verified_exchanges:
            print(f"🏁 Signet: Session complete - {len(self.verified_exchanges)} verified exchanges")
    
    def _should_route_through_signet(self, function_call: Dict[str, Any]) -> bool:
        """Determine if a function call should be routed through Signet."""
        function_name = function_call.get("name", "")
        
        # Route financial/invoice/data processing functions through Signet
        signet_functions = [
            'create_invoice', 'process_payment', 'generate_receipt',
            'update_invoice', 'create_order', 'process_transaction',
            'calculate_total', 'apply_discount', 'validate_payment'
        ]
        
        return function_name in signet_functions
    
    def _parse_function_output(
        self, 
        output: str, 
        function_call: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Parse function output to extract structured data suitable for Signet."""
        try:
            function_name = function_call.get("name", "unknown")
            function_args = function_call.get("arguments", {})
            
            # Try to parse output as JSON first
            if isinstance(output, str) and output.strip().startswith('{'):
                data = json.loads(output)
            elif isinstance(output, dict):
                data = output
            else:
                # Create structured data from function call and output
                data = {
                    "function_name": function_name,
                    "arguments": function_args,
                    "result": output
                }
            
            # Check if it looks like invoice/financial data
            if self._is_financial_data(data, function_name):
                return self._convert_to_signet_payload(data, function_name)
            
            return None
            
        except (json.JSONDecodeError, Exception):
            return None
    
    def _is_financial_data(self, data: Dict[str, Any], function_name: str) -> bool:
        """Check if data structure looks like financial/invoice data."""
        financial_fields = ['amount', 'currency', 'invoice_id', 'payment_id', 'customer', 'total', 'price']
        financial_functions = ['invoice', 'payment', 'order', 'transaction', 'receipt']
        
        # Check if data contains financial fields
        has_financial_fields = any(field in data for field in financial_fields)
        
        # Check if function name suggests financial operation
        has_financial_function = any(term in function_name.lower() for term in financial_functions)
        
        return has_financial_fields or has_financial_function
    
    def _convert_to_signet_payload(self, data: Dict[str, Any], function_name: str) -> Dict[str, Any]:
        """Convert parsed data to Signet Protocol payload format."""
        return {
            "payload_type": "openai.tooluse.invoice.v1",
            "target_type": "invoice.iso20022.v1",
            "trace_id": self.current_trace_id,
            "payload": {
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "arguments": json.dumps(data)
                    }
                }]
            },
            "forward_url": self.forward_url if self.auto_forward else None
        }
    
    def _send_to_signet(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send payload to Signet Protocol for verification."""
        try:
            headers = {
                "X-SIGNET-API-Key": self.api_key,
                "X-SIGNET-Idempotency-Key": f"{self.current_trace_id}-{uuid.uuid4()}",
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                f"{self.signet_url}/v1/exchange",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("receipt")
            else:
                print(f"❌ Signet API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Signet request failed: {str(e)}")
            return None
    
    def _export_chain(self) -> None:
        """Export the complete receipt chain."""
        if not self.current_trace_id:
            return
        
        try:
            response = self.session.get(
                f"{self.signet_url}/v1/receipts/export/{self.current_trace_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"📤 Signet: Chain exported - {len(self.verified_exchanges)} receipts")
                # Optionally save to file or send to webhook
            
        except Exception as e:
            print(f"⚠️ Signet: Chain export failed: {str(e)}")


# Convenience function for quick setup
def enable_signet_for_llamaindex(
    signet_url: str,
    api_key: str,
    forward_url: Optional[str] = None
) -> SignetLlamaIndexHandler:
    """
    One-liner to enable Signet verification for LlamaIndex.
    
    Usage:
        from signet_callback import enable_signet_for_llamaindex
        from llama_index.core import Settings
        
        signet_handler = enable_signet_for_llamaindex(
            "http://localhost:8088", 
            "your-api-key",
            "https://your-webhook.com"
        )
        
        Settings.callback_manager.add_handler(signet_handler)
    """
    return SignetLlamaIndexHandler(
        signet_url=signet_url,
        api_key=api_key,
        forward_url=forward_url
    )


# Example usage
if __name__ == "__main__":
    # Example: Using with LlamaIndex
    from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
    from llama_index.llms.openai import OpenAI
    
    # Enable Signet verification
    signet_handler = enable_signet_for_llamaindex(
        signet_url="http://localhost:8088",
        api_key="demo_key",
        forward_url="https://webhook.site/your-unique-url"
    )
    
    # Add to LlamaIndex settings
    Settings.callback_manager.add_handler(signet_handler)
    Settings.llm = OpenAI(temperature=0.1)
    
    print("✅ Signet Protocol enabled for LlamaIndex")
    print(f"📋 Trace ID: {signet_handler.current_trace_id}")
    
    # Example query that might trigger financial functions
    # documents = SimpleDirectoryReader("data").load_data()
    # index = VectorStoreIndex.from_documents(documents)
    # query_engine = index.as_query_engine()
    # response = query_engine.query("Create an invoice for $1000 consulting services")
    
    print(f"🔍 Verified exchanges: {len(signet_handler.verified_exchanges)}")
