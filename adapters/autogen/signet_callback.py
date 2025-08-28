"""
Signet Protocol - AutoGen Integration
Callback handler for verified AI-to-AI communications in AutoGen.
"""

import json
import uuid
import requests
from typing import Any, Dict, List, Optional, Union, Callable
import autogen
from autogen import ConversableAgent, GroupChat, GroupChatManager

class SignetAutoGenHandler:
    """
    AutoGen integration that routes function calls through Signet Protocol.
    
    Usage:
        from signet_callback import SignetAutoGenHandler
        
        signet_handler = SignetAutoGenHandler(
            signet_url="http://localhost:8088",
            api_key="your-signet-api-key",
            forward_url="https://your-webhook.com/receive"
        )
        
        # Wrap your agents
        verified_agent = signet_handler.wrap_agent(agent)
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
        self.signet_url = signet_url.rstrip('/')
        self.api_key = api_key
        self.forward_url = forward_url
        self.tenant = tenant or "autogen"
        self.auto_forward = auto_forward
        self.session = requests.Session()
        
        # Track current trace for chaining
        self.current_trace_id = None
        self.verified_exchanges = []
        self.wrapped_agents = set()
    
    def wrap_agent(self, agent: ConversableAgent) -> ConversableAgent:
        """Wrap an AutoGen agent to route function calls through Signet Protocol."""
        if id(agent) in self.wrapped_agents:
            return agent  # Already wrapped
        
        # Generate trace ID for this session
        if not self.current_trace_id:
            self.current_trace_id = f"autogen-{uuid.uuid4()}"
        
        # Store original function map
        original_function_map = getattr(agent, '_function_map', {})
        
        # Wrap each function in the function map
        wrapped_function_map = {}
        for name, func_info in original_function_map.items():
            if self._should_route_function(name):
                wrapped_function_map[name] = self._wrap_function(func_info, name)
            else:
                wrapped_function_map[name] = func_info
        
        # Replace the function map
        agent._function_map = wrapped_function_map
        
        # Wrap the generate_reply method to track conversation flow
        original_generate_reply = agent.generate_reply
        
        def wrapped_generate_reply(messages=None, sender=None, **kwargs):
            # Check if this is the start of a new conversation
            if not self.current_trace_id:
                self.current_trace_id = f"autogen-{uuid.uuid4()}"
                print(f"🔗 Signet: AutoGen conversation starting (trace: {self.current_trace_id})")
            
            try:
                reply = original_generate_reply(messages, sender, **kwargs)
                return reply
            except Exception as e:
                print(f"⚠️ Signet: Error in agent reply: {str(e)}")
                raise
        
        agent.generate_reply = wrapped_generate_reply
        
        # Mark as wrapped
        self.wrapped_agents.add(id(agent))
        
        print(f"✅ Signet: Wrapped AutoGen agent '{agent.name}'")
        return agent
    
    def wrap_group_chat(self, group_chat: GroupChat) -> GroupChat:
        """Wrap all agents in a group chat."""
        for agent in group_chat.agents:
            self.wrap_agent(agent)
        return group_chat
    
    def _should_route_function(self, function_name: str) -> bool:
        """Determine if a function should be routed through Signet."""
        # Route financial/invoice/data processing functions through Signet
        signet_functions = [
            'create_invoice', 'process_payment', 'generate_receipt',
            'update_invoice', 'create_order', 'process_transaction',
            'calculate_total', 'apply_discount', 'validate_payment',
            'invoice', 'payment', 'billing', 'financial'
        ]
        
        return any(signet_func in function_name.lower() for signet_func in signet_functions)
    
    def _wrap_function(self, func_info: Dict[str, Any], function_name: str) -> Dict[str, Any]:
        """Wrap a function to route its output through Signet Protocol."""
        original_func = func_info.get('function')
        if not original_func:
            return func_info
        
        def wrapped_function(*args, **kwargs):
            print(f"🎯 Signet: Routing function '{function_name}' through protocol")
            
            try:
                # Execute original function
                result = original_func(*args, **kwargs)
                
                # Parse and route through Signet
                parsed_output = self._parse_function_output(result, function_name, args, kwargs)
                
                if parsed_output:
                    receipt = self._send_to_signet(parsed_output)
                    if receipt:
                        self.verified_exchanges.append(receipt)
                        print(f"✅ Signet: Verified exchange recorded (hop: {receipt.get('hop')})")
                    else:
                        print("❌ Signet: Exchange verification failed")
                
                return result
            
            except Exception as e:
                print(f"⚠️ Signet: Error in wrapped function: {str(e)}")
                raise
        
        # Create new function info with wrapped function
        wrapped_info = func_info.copy()
        wrapped_info['function'] = wrapped_function
        
        return wrapped_info
    
    def _parse_function_output(
        self, 
        output: Any, 
        function_name: str, 
        args: tuple, 
        kwargs: dict
    ) -> Optional[Dict[str, Any]]:
        """Parse function output to extract structured data suitable for Signet."""
        try:
            # Try to parse output as JSON first
            if isinstance(output, str) and output.strip().startswith('{'):
                data = json.loads(output)
            elif isinstance(output, dict):
                data = output
            else:
                # Create structured data from function call and output
                data = {
                    "function_name": function_name,
                    "arguments": {
                        "args": list(args),
                        "kwargs": kwargs
                    },
                    "result": str(output)
                }
            
            # Check if it looks like financial data
            if self._is_financial_data(data, function_name):
                return self._convert_to_signet_payload(data, function_name)
            
            return None
            
        except (json.JSONDecodeError, Exception):
            return None
    
    def _is_financial_data(self, data: Dict[str, Any], function_name: str) -> bool:
        """Check if data structure looks like financial/invoice data."""
        financial_fields = ['amount', 'currency', 'invoice_id', 'payment_id', 'customer', 'total', 'price']
        financial_terms = ['invoice', 'payment', 'order', 'transaction', 'receipt', 'billing']
        
        # Check if data contains financial fields
        has_financial_fields = any(field in data for field in financial_fields)
        
        # Check if function name suggests financial operation
        has_financial_function = any(term in function_name.lower() for term in financial_terms)
        
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
    
    def export_chain(self) -> Optional[Dict[str, Any]]:
        """Export the complete receipt chain."""
        if not self.current_trace_id:
            return None
        
        try:
            response = self.session.get(
                f"{self.signet_url}/v1/receipts/export/{self.current_trace_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                export_data = response.json()
                print(f"📤 Signet: Chain exported - {len(self.verified_exchanges)} receipts")
                return export_data
            
            return None
            
        except Exception as e:
            print(f"⚠️ Signet: Chain export failed: {str(e)}")
            return None
    
    def get_verification_summary(self) -> Dict[str, Any]:
        """Get a summary of verified exchanges in this session."""
        return {
            "trace_id": self.current_trace_id,
            "total_exchanges": len(self.verified_exchanges),
            "exchanges": self.verified_exchanges,
            "wrapped_agents": len(self.wrapped_agents)
        }


def create_signet_function(
    signet_url: str,
    api_key: str,
    forward_url: Optional[str] = None
) -> Callable:
    """
    Decorator to create AutoGen functions that automatically route through Signet Protocol.
    
    Usage:
        @create_signet_function(
            signet_url="http://localhost:8088",
            api_key="your-api-key"
        )
        def create_invoice(amount: float, currency: str = "USD") -> dict:
            return {
                "invoice_id": f"INV-{uuid.uuid4()}",
                "amount": amount,
                "currency": currency
            }
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Execute original function
            result = func(*args, **kwargs)
            
            # Route through Signet if it's financial data
            if _is_financial_result(result, func.__name__):
                trace_id = f"autogen-func-{uuid.uuid4()}"
                payload = _create_signet_payload(result, func.__name__, trace_id, signet_url, api_key, forward_url)
                receipt = _send_to_signet(payload, signet_url, api_key)
                
                if receipt:
                    print(f"✅ Signet: Function '{func.__name__}' verified (trace: {trace_id})")
                else:
                    print(f"❌ Signet: Function '{func.__name__}' verification failed")
            
            return result
        
        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


def _is_financial_result(result: Any, func_name: str) -> bool:
    """Check if result looks like financial data."""
    if not isinstance(result, dict):
        return False
    
    financial_fields = ['amount', 'currency', 'invoice_id', 'payment_id', 'total', 'price']
    financial_terms = ['invoice', 'payment', 'order', 'transaction', 'receipt']
    
    has_financial_fields = any(field in result for field in financial_fields)
    has_financial_name = any(term in func_name.lower() for term in financial_terms)
    
    return has_financial_fields or has_financial_name


def _create_signet_payload(result: dict, func_name: str, trace_id: str, signet_url: str, api_key: str, forward_url: Optional[str]) -> dict:
    """Create Signet Protocol payload."""
    return {
        "payload_type": "openai.tooluse.invoice.v1",
        "target_type": "invoice.iso20022.v1",
        "trace_id": trace_id,
        "payload": {
            "tool_calls": [{
                "type": "function",
                "function": {
                    "name": func_name,
                    "arguments": json.dumps(result)
                }
            }]
        },
        "forward_url": forward_url
    }


def _send_to_signet(payload: dict, signet_url: str, api_key: str) -> Optional[dict]:
    """Send to Signet Protocol."""
    try:
        headers = {
            "X-SIGNET-API-Key": api_key,
            "X-SIGNET-Idempotency-Key": f"{payload['trace_id']}-{uuid.uuid4()}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{signet_url}/v1/exchange",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("receipt")
        return None
        
    except Exception:
        return None


# Convenience function for quick setup
def enable_signet_for_autogen(
    signet_url: str,
    api_key: str,
    forward_url: Optional[str] = None
) -> SignetAutoGenHandler:
    """
    One-liner to enable Signet verification for AutoGen.
    
    Usage:
        from signet_callback import enable_signet_for_autogen
        
        signet_handler = enable_signet_for_autogen(
            "http://localhost:8088", 
            "your-api-key",
            "https://your-webhook.com"
        )
        
        verified_agent = signet_handler.wrap_agent(agent)
    """
    return SignetAutoGenHandler(
        signet_url=signet_url,
        api_key=api_key,
        forward_url=forward_url
    )


# Example usage
if __name__ == "__main__":
    # Example: Using with AutoGen
    import autogen
    
    # Enable Signet verification
    signet_handler = enable_signet_for_autogen(
        signet_url="http://localhost:8088",
        api_key="demo_key",
        forward_url="https://webhook.site/your-unique-url"
    )
    
    # Example Signet-enabled function
    @create_signet_function(
        signet_url="http://localhost:8088",
        api_key="demo_key"
    )
    def create_invoice(amount: float, currency: str = "USD") -> dict:
        """Create an invoice with the given amount and currency."""
        return {
            "invoice_id": f"INV-{uuid.uuid4()}",
            "amount": amount,
            "currency": currency,
            "status": "created",
            "created_at": "2025-01-27T12:00:00Z"
        }
    
    # Create AutoGen agent with Signet-enabled functions
    config_list = [
        {
            "model": "gpt-4",
            "api_key": "your-openai-api-key"
        }
    ]
    
    financial_agent = autogen.ConversableAgent(
        name="FinancialAgent",
        system_message="You are a financial processing agent. Use the create_invoice function to create invoices.",
        llm_config={"config_list": config_list},
        function_map={"create_invoice": create_invoice}
    )
    
    user_proxy = autogen.UserProxyAgent(
        name="UserProxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        code_execution_config=False
    )
    
    # Wrap agents with Signet
    verified_financial_agent = signet_handler.wrap_agent(financial_agent)
    verified_user_proxy = signet_handler.wrap_agent(user_proxy)
    
    print("✅ Signet Protocol enabled for AutoGen")
    print(f"📋 Trace ID: {signet_handler.current_trace_id}")
    
    # Example conversation (would execute in real scenario)
    # user_proxy.initiate_chat(
    #     financial_agent,
    #     message="Create an invoice for $1000 consulting services"
    # )
    
    print(f"🔍 Verified exchanges: {len(signet_handler.verified_exchanges)}")
    
    # Get verification summary
    summary = signet_handler.get_verification_summary()
    print(f"📊 Verification Summary: {summary}")
