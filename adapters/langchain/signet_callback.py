#!/usr/bin/env python3
"""
Signet Protocol LangChain Adapter

One-line integration with LangChain for automatic
verification of AI interactions and tool usage.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from uuid import uuid4

try:
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.schema import AgentAction, AgentFinish, LLMResult
except ImportError:
    # Fallback for different LangChain versions
    try:
        from langchain_core.callbacks.base import BaseCallbackHandler
        from langchain_core.agents import AgentAction, AgentFinish
        from langchain_core.outputs import LLMResult
    except ImportError:
        raise ImportError("LangChain not found. Install with: pip install langchain")

from ...sdk.python.signet_client import SignetClient


class SignetCallback(BaseCallbackHandler):
    """LangChain callback for Signet Protocol verification"""
    
    def __init__(
        self,
        signet_url: str,
        api_key: str,
        forward_url: str,
        auto_verify: bool = True,
        payload_type: str = "openai.tooluse.invoice.v1",
        target_type: str = "invoice.iso20022.v1"
    ):
        """Initialize Signet callback
        
        Args:
            signet_url: Signet Protocol server URL
            api_key: API key for Signet server
            forward_url: URL to forward verified data
            auto_verify: Automatically verify tool calls
            payload_type: Source payload type
            target_type: Target payload type
        """
        super().__init__()
        self.client = SignetClient(signet_url, api_key)
        self.forward_url = forward_url
        self.auto_verify = auto_verify
        self.payload_type = payload_type
        self.target_type = target_type
        self.receipts = []
        self.session_id = f"langchain-{uuid4().hex[:12]}"
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """Called when tool starts"""
        if self.auto_verify:
            # Prepare tool call for verification
            tool_data = {
                'tool_name': serialized.get('name', 'unknown'),
                'input': input_str,
                'session_id': self.session_id,
                'timestamp': kwargs.get('timestamp')
            }
            
            # Store for verification on tool end
            self._current_tool_data = tool_data
    
    def on_tool_end(
        self,
        output: str,
        **kwargs: Any
    ) -> None:
        """Called when tool ends - verify the interaction"""
        if self.auto_verify and hasattr(self, '_current_tool_data'):
            try:
                # Create payload in OpenAI tool use format
                payload = {
                    'tool_calls': [{
                        'type': 'function',
                        'function': {
                            'name': self._current_tool_data['tool_name'],
                            'arguments': json.dumps({
                                'input': self._current_tool_data['input'],
                                'output': output,
                                'session_id': self.session_id
                            })
                        }
                    }]
                }
                
                # Verify asynchronously (fire and forget)
                asyncio.create_task(self._verify_tool_call(payload))
                
            except Exception as e:
                print(f"Signet verification error: {e}")
    
    def on_agent_action(
        self,
        action: AgentAction,
        **kwargs: Any
    ) -> None:
        """Called when agent takes an action"""
        if self.auto_verify:
            # Prepare agent action for verification
            action_data = {
                'tool': action.tool,
                'tool_input': action.tool_input,
                'log': action.log,
                'session_id': self.session_id
            }
            
            self._current_action_data = action_data
    
    def on_agent_finish(
        self,
        finish: AgentFinish,
        **kwargs: Any
    ) -> None:
        """Called when agent finishes"""
        if self.auto_verify and hasattr(self, '_current_action_data'):
            try:
                # Create payload for agent completion
                payload = {
                    'tool_calls': [{
                        'type': 'function',
                        'function': {
                            'name': 'agent_complete',
                            'arguments': json.dumps({
                                'action': self._current_action_data,
                                'result': finish.return_values,
                                'session_id': self.session_id
                            })
                        }
                    }]
                }
                
                # Verify asynchronously
                asyncio.create_task(self._verify_tool_call(payload))
                
            except Exception as e:
                print(f"Signet agent verification error: {e}")
    
    async def _verify_tool_call(self, payload: Dict[str, Any]) -> None:
        """Verify tool call with Signet Protocol"""
        try:
            result = await self.client.exchange(
                payload_type=self.payload_type,
                target_type=self.target_type,
                payload=payload,
                forward_url=self.forward_url,
                idempotency_key=f"{self.session_id}-{len(self.receipts)}"
            )
            
            # Store receipt
            self.receipts.append(result)
            
            print(f"✓ Signet verification complete: {result.get('trace_id')}")
            
        except Exception as e:
            print(f"✗ Signet verification failed: {e}")
    
    def get_receipts(self) -> List[Dict[str, Any]]:
        """Get all receipts from this session"""
        return self.receipts.copy()
    
    async def export_audit_trail(self) -> Dict[str, Any]:
        """Export audit trail for this session"""
        return await self.client.export_audit_trail(self.session_id)


def enable_signet_verification(
    signet_url: str,
    api_key: str,
    forward_url: str = "https://webhook.site/unique-url",
    **kwargs
) -> SignetCallback:
    """
    One-line function to enable Signet verification for LangChain
    
    Args:
        signet_url: Signet Protocol server URL
        api_key: API key for Signet server
        forward_url: URL to forward verified data
        **kwargs: Additional arguments for SignetCallback
    
    Returns:
        SignetCallback instance to use with LangChain
    
    Example:
        ```python
        from signet_callback import enable_signet_verification
        
        # Enable verification in one line
        signet = enable_signet_verification(
            "http://localhost:8088", 
            "your-api-key"
        )
        
        # Use with LangChain
        chain.run(input, callbacks=[signet])
        ```
    """
    return SignetCallback(
        signet_url=signet_url,
        api_key=api_key,
        forward_url=forward_url,
        **kwargs
    )


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example():
        # Enable Signet verification
        signet = enable_signet_verification(
            "http://localhost:8088",
            "demo_key",
            "https://webhook.site/your-unique-url"
        )
        
        # Simulate tool usage (normally done by LangChain)
        signet.on_tool_start(
            {'name': 'calculator'},
            "What is 2 + 2?"
        )
        
        signet.on_tool_end("4")
        
        # Wait for async verification
        await asyncio.sleep(1)
        
        # Get receipts
        receipts = signet.get_receipts()
        print(f"Generated {len(receipts)} receipts")
    
    asyncio.run(example())