"""
Signet Protocol - LangChain Integration
One-line callback handler for verified AI-to-AI communications.
"""

import json
import uuid
import requests
from typing import Any, Dict, List, Optional, Union
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult
from langchain.schema.messages import BaseMessage

class SignetCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that routes tool calls through Signet Protocol.
    
    Usage:
        from signet_callback import SignetCallbackHandler
        
        signet_handler = SignetCallbackHandler(
            signet_url="http://localhost:8088",
            api_key="your-signet-api-key",
            forward_url="https://your-webhook.com/receive"
        )
        
        # Add to any LangChain chain
        chain.run(input_text, callbacks=[signet_handler])
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
        super().__init__(**kwargs)
        self.signet_url = signet_url.rstrip('/')
        self.api_key = api_key
        self.forward_url = forward_url
        self.tenant = tenant or "langchain"
        self.auto_forward = auto_forward
        self.session = requests.Session()
        
        # Track current trace for chaining
        self.current_trace_id = None
        self.verified_exchanges = []
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts running."""
        tool_name = serialized.get("name", "unknown_tool")
        
        # Generate trace ID for new conversation
        if not self.current_trace_id:
            self.current_trace_id = f"langchain-{uuid.uuid4()}"
        
        print(f"🔗 Signet: Tool '{tool_name}' starting (trace: {self.current_trace_id})")
    
    def on_tool_end(
        self,
        output: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool ends running - route through Signet."""
        try:
            # Parse tool output as potential invoice/structured data
            tool_output = self._parse_tool_output(output)
            
            if tool_output:
                # Route through Signet Protocol
                receipt = self._send_to_signet(tool_output)
                if receipt:
                    self.verified_exchanges.append(receipt)
                    print(f"✅ Signet: Verified exchange recorded (hop: {receipt.get('hop')})")
                else:
                    print("❌ Signet: Exchange verification failed")
        
        except Exception as e:
            print(f"⚠️ Signet: Error processing tool output: {str(e)}")
    
    def on_agent_action(
        self,
        action: AgentAction,
        **kwargs: Any,
    ) -> None:
        """Called when agent takes an action."""
        # Check if this is a tool call that should go through Signet
        if self._should_route_through_signet(action):
            print(f"🎯 Signet: Routing agent action '{action.tool}' through protocol")
    
    def on_agent_finish(
        self,
        finish: AgentFinish,
        **kwargs: Any,
    ) -> None:
        """Called when agent finishes."""
        if self.verified_exchanges:
            print(f"🏁 Signet: Session complete - {len(self.verified_exchanges)} verified exchanges")
            
            # Optionally export the complete chain
            if len(self.verified_exchanges) > 1:
                self._export_chain()
    
    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any,
    ) -> None:
        """Called when LLM ends running."""
        # Check if LLM output contains structured data for Signet
        for generation in response.generations:
            for gen in generation:
                if self._contains_structured_data(gen.text):
                    print("📋 Signet: LLM generated structured data - considering for verification")
    
    def _parse_tool_output(self, output: str) -> Optional[Dict[str, Any]]:
        """
        Parse tool output to extract structured data suitable for Signet.
        Override this method to customize parsing for your use case.
        """
        try:
            # Try to parse as JSON first
            if output.strip().startswith('{'):
                data = json.loads(output)
                
                # Check if it looks like invoice data
                if self._is_invoice_like(data):
                    return self._convert_to_signet_payload(data)
            
            # Try to extract JSON from text
            import re
            json_match = re.search(r'\{[^{}]*\}', output)
            if json_match:
                data = json.loads(json_match.group())
                if self._is_invoice_like(data):
                    return self._convert_to_signet_payload(data)
            
            return None
            
        except (json.JSONDecodeError, Exception):
            return None
    
    def _is_invoice_like(self, data: Dict[str, Any]) -> bool:
        """Check if data structure looks like an invoice."""
        invoice_fields = ['amount', 'currency', 'invoice_id', 'customer', 'description']
        return any(field in data for field in invoice_fields)
    
    def _convert_to_signet_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parsed data to Signet Protocol payload format."""
        return {
            "payload_type": "openai.tooluse.invoice.v1",
            "target_type": "invoice.iso20022.v1",
            "trace_id": self.current_trace_id,
            "payload": {
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": "create_invoice",
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
    
    def _should_route_through_signet(self, action: AgentAction) -> bool:
        """Determine if an agent action should be routed through Signet."""
        # Route financial/invoice tools through Signet
        financial_tools = ['create_invoice', 'process_payment', 'generate_receipt']
        return action.tool in financial_tools
    
    def _contains_structured_data(self, text: str) -> bool:
        """Check if text contains structured data."""
        return '{' in text and '}' in text
    
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


class SignetRunnable:
    """
    LangChain Runnable wrapper that routes outputs through Signet Protocol.
    
    Usage:
        from signet_callback import SignetRunnable
        
        # Wrap any runnable
        verified_chain = SignetRunnable(
            runnable=your_chain,
            signet_url="http://localhost:8088",
            api_key="your-signet-api-key"
        )
        
        result = verified_chain.invoke({"input": "Create invoice for $100"})
    """
    
    def __init__(
        self,
        runnable,
        signet_url: str,
        api_key: str,
        forward_url: Optional[str] = None,
        **kwargs
    ):
        self.runnable = runnable
        self.signet_handler = SignetCallbackHandler(
            signet_url=signet_url,
            api_key=api_key,
            forward_url=forward_url,
            **kwargs
        )
    
    def invoke(self, input_data: Dict[str, Any], **kwargs) -> Any:
        """Invoke the wrapped runnable with Signet verification."""
        # Add Signet callback to the invocation
        callbacks = kwargs.get('callbacks', [])
        callbacks.append(self.signet_handler)
        kwargs['callbacks'] = callbacks
        
        return self.runnable.invoke(input_data, **kwargs)
    
    def stream(self, input_data: Dict[str, Any], **kwargs):
        """Stream the wrapped runnable with Signet verification."""
        callbacks = kwargs.get('callbacks', [])
        callbacks.append(self.signet_handler)
        kwargs['callbacks'] = callbacks
        
        return self.runnable.stream(input_data, **kwargs)


# Convenience function for quick setup
def enable_signet_verification(
    signet_url: str,
    api_key: str,
    forward_url: Optional[str] = None
) -> SignetCallbackHandler:
    """
    One-liner to enable Signet verification for LangChain.
    
    Usage:
        signet = enable_signet_verification(
            "http://localhost:8088", 
            "your-api-key",
            "https://your-webhook.com"
        )
        
        chain.run(input, callbacks=[signet])
    """
    return SignetCallbackHandler(
        signet_url=signet_url,
        api_key=api_key,
        forward_url=forward_url
    )


# Example usage
if __name__ == "__main__":
    # Example: Using with a simple LangChain chain
    from langchain.llms import OpenAI
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    
    # Create a simple chain
    llm = OpenAI(temperature=0)
    prompt = PromptTemplate(
        input_variables=["customer", "amount"],
        template="Create an invoice for {customer} with amount ${amount}. Return as JSON."
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    
    # Enable Signet verification
    signet_handler = enable_signet_verification(
        signet_url="http://localhost:8088",
        api_key="demo_key",
        forward_url="https://webhook.site/your-unique-url"
    )
    
    # Run with verification
    result = chain.run(
        customer="Acme Corp",
        amount="1000",
        callbacks=[signet_handler]
    )
    
    print(f"Result: {result}")
    print(f"Verified exchanges: {len(signet_handler.verified_exchanges)}")
