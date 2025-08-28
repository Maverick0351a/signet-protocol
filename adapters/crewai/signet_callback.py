"""
Signet Protocol - CrewAI Integration
Callback handler for verified AI-to-AI communications in CrewAI.
"""

import json
import uuid
import requests
from typing import Any, Dict, List, Optional, Union
from crewai.agent import BaseAgent
from crewai.task import Task
from crewai.crew import Crew

class SignetCrewAIHandler:
    """
    CrewAI integration that routes tool calls through Signet Protocol.
    
    Usage:
        from signet_callback import SignetCrewAIHandler
        
        signet_handler = SignetCrewAIHandler(
            signet_url="http://localhost:8088",
            api_key="your-signet-api-key",
            forward_url="https://your-webhook.com/receive"
        )
        
        # Wrap your crew
        verified_crew = signet_handler.wrap_crew(crew)
        result = verified_crew.kickoff()
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
        self.tenant = tenant or "crewai"
        self.auto_forward = auto_forward
        self.session = requests.Session()
        
        # Track current trace for chaining
        self.current_trace_id = None
        self.verified_exchanges = []
        self.original_tools = {}
    
    def wrap_crew(self, crew: Crew) -> Crew:
        """Wrap a CrewAI crew to route tool calls through Signet Protocol."""
        # Store original crew reference
        self.crew = crew
        
        # Generate trace ID for this crew session
        self.current_trace_id = f"crewai-{uuid.uuid4()}"
        
        # Wrap all agents in the crew
        for agent in crew.agents:
            self._wrap_agent(agent)
        
        # Wrap crew's kickoff method
        original_kickoff = crew.kickoff
        
        def wrapped_kickoff(*args, **kwargs):
            print(f"🔗 Signet: CrewAI session starting (trace: {self.current_trace_id})")
            
            try:
                result = original_kickoff(*args, **kwargs)
                
                # Session completed - export chain if we have exchanges
                if self.verified_exchanges:
                    print(f"🏁 Signet: CrewAI session complete - {len(self.verified_exchanges)} verified exchanges")
                    self._export_chain()
                
                return result
            
            except Exception as e:
                print(f"⚠️ Signet: CrewAI session error: {str(e)}")
                raise
        
        crew.kickoff = wrapped_kickoff
        return crew
    
    def _wrap_agent(self, agent: BaseAgent) -> None:
        """Wrap an individual agent's tools."""
        if hasattr(agent, 'tools') and agent.tools:
            for i, tool in enumerate(agent.tools):
                if self._should_route_tool(tool):
                    agent.tools[i] = self._wrap_tool(tool)
    
    def _should_route_tool(self, tool) -> bool:
        """Determine if a tool should be routed through Signet."""
        tool_name = getattr(tool, 'name', str(tool)).lower()
        
        # Route financial/invoice/data processing tools through Signet
        signet_tools = [
            'create_invoice', 'process_payment', 'generate_receipt',
            'update_invoice', 'create_order', 'process_transaction',
            'calculate_total', 'apply_discount', 'validate_payment',
            'invoice', 'payment', 'billing', 'financial'
        ]
        
        return any(signet_tool in tool_name for signet_tool in signet_tools)
    
    def _wrap_tool(self, original_tool):
        """Wrap a tool to route its output through Signet Protocol."""
        # Store original tool
        tool_id = id(original_tool)
        self.original_tools[tool_id] = original_tool
        
        # Get original run method
        if hasattr(original_tool, '_run'):
            original_run = original_tool._run
        elif hasattr(original_tool, 'run'):
            original_run = original_tool.run
        else:
            # Can't wrap this tool
            return original_tool
        
        def wrapped_run(*args, **kwargs):
            tool_name = getattr(original_tool, 'name', 'unknown_tool')
            print(f"🎯 Signet: Routing tool '{tool_name}' through protocol")
            
            try:
                # Execute original tool
                result = original_run(*args, **kwargs)
                
                # Parse and route through Signet
                parsed_output = self._parse_tool_output(result, tool_name, args, kwargs)
                
                if parsed_output:
                    receipt = self._send_to_signet(parsed_output)
                    if receipt:
                        self.verified_exchanges.append(receipt)
                        print(f"✅ Signet: Verified exchange recorded (hop: {receipt.get('hop')})")
                    else:
                        print("❌ Signet: Exchange verification failed")
                
                return result
            
            except Exception as e:
                print(f"⚠️ Signet: Error in wrapped tool: {str(e)}")
                raise
        
        # Replace the run method
        if hasattr(original_tool, '_run'):
            original_tool._run = wrapped_run
        elif hasattr(original_tool, 'run'):
            original_tool.run = wrapped_run
        
        return original_tool
    
    def _parse_tool_output(
        self, 
        output: Any, 
        tool_name: str, 
        args: tuple, 
        kwargs: dict
    ) -> Optional[Dict[str, Any]]:
        """Parse tool output to extract structured data suitable for Signet."""
        try:
            # Try to parse output as JSON first
            if isinstance(output, str) and output.strip().startswith('{'):
                data = json.loads(output)
            elif isinstance(output, dict):
                data = output
            else:
                # Create structured data from tool call and output
                data = {
                    "tool_name": tool_name,
                    "arguments": {
                        "args": args,
                        "kwargs": kwargs
                    },
                    "result": str(output)
                }
            
            # Check if it looks like financial data
            if self._is_financial_data(data, tool_name):
                return self._convert_to_signet_payload(data, tool_name)
            
            return None
            
        except (json.JSONDecodeError, Exception):
            return None
    
    def _is_financial_data(self, data: Dict[str, Any], tool_name: str) -> bool:
        """Check if data structure looks like financial/invoice data."""
        financial_fields = ['amount', 'currency', 'invoice_id', 'payment_id', 'customer', 'total', 'price']
        financial_terms = ['invoice', 'payment', 'order', 'transaction', 'receipt', 'billing']
        
        # Check if data contains financial fields
        has_financial_fields = any(field in data for field in financial_fields)
        
        # Check if tool name suggests financial operation
        has_financial_tool = any(term in tool_name.lower() for term in financial_terms)
        
        return has_financial_fields or has_financial_tool
    
    def _convert_to_signet_payload(self, data: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
        """Convert parsed data to Signet Protocol payload format."""
        return {
            "payload_type": "openai.tooluse.invoice.v1",
            "target_type": "invoice.iso20022.v1",
            "trace_id": self.current_trace_id,
            "payload": {
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": tool_name,
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


class SignetTool:
    """
    A CrewAI tool wrapper that automatically routes through Signet Protocol.
    
    Usage:
        from signet_callback import SignetTool
        
        @SignetTool(
            signet_url="http://localhost:8088",
            api_key="your-api-key"
        )
        def create_invoice(amount: float, currency: str = "USD") -> dict:
            return {
                "invoice_id": f"INV-{uuid.uuid4()}",
                "amount": amount,
                "currency": currency,
                "status": "created"
            }
    """
    
    def __init__(
        self,
        signet_url: str,
        api_key: str,
        forward_url: Optional[str] = None,
        tenant: Optional[str] = None
    ):
        self.signet_url = signet_url.rstrip('/')
        self.api_key = api_key
        self.forward_url = forward_url
        self.tenant = tenant or "crewai-tool"
        self.session = requests.Session()
    
    def __call__(self, func):
        """Decorator to wrap a function as a Signet-enabled tool."""
        def wrapper(*args, **kwargs):
            # Generate trace ID for this tool call
            trace_id = f"{self.tenant}-{uuid.uuid4()}"
            
            # Execute original function
            result = func(*args, **kwargs)
            
            # Route through Signet if it's financial data
            if self._is_financial_result(result, func.__name__):
                payload = self._create_signet_payload(result, func.__name__, trace_id)
                receipt = self._send_to_signet(payload)
                
                if receipt:
                    print(f"✅ Signet: Tool '{func.__name__}' verified (trace: {trace_id})")
                else:
                    print(f"❌ Signet: Tool '{func.__name__}' verification failed")
            
            return result
        
        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    def _is_financial_result(self, result: Any, func_name: str) -> bool:
        """Check if result looks like financial data."""
        if not isinstance(result, dict):
            return False
        
        financial_fields = ['amount', 'currency', 'invoice_id', 'payment_id', 'total', 'price']
        financial_terms = ['invoice', 'payment', 'order', 'transaction', 'receipt']
        
        has_financial_fields = any(field in result for field in financial_fields)
        has_financial_name = any(term in func_name.lower() for term in financial_terms)
        
        return has_financial_fields or has_financial_name
    
    def _create_signet_payload(self, result: dict, func_name: str, trace_id: str) -> dict:
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
            "forward_url": self.forward_url
        }
    
    def _send_to_signet(self, payload: dict) -> Optional[dict]:
        """Send to Signet Protocol."""
        try:
            headers = {
                "X-SIGNET-API-Key": self.api_key,
                "X-SIGNET-Idempotency-Key": f"{payload['trace_id']}-{uuid.uuid4()}",
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                f"{self.signet_url}/v1/exchange",
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
def enable_signet_for_crewai(
    signet_url: str,
    api_key: str,
    forward_url: Optional[str] = None
) -> SignetCrewAIHandler:
    """
    One-liner to enable Signet verification for CrewAI.
    
    Usage:
        from signet_callback import enable_signet_for_crewai
        
        signet_handler = enable_signet_for_crewai(
            "http://localhost:8088", 
            "your-api-key",
            "https://your-webhook.com"
        )
        
        verified_crew = signet_handler.wrap_crew(crew)
    """
    return SignetCrewAIHandler(
        signet_url=signet_url,
        api_key=api_key,
        forward_url=forward_url
    )


# Example usage
if __name__ == "__main__":
    # Example: Using with CrewAI
    from crewai import Agent, Task, Crew, Process
    
    # Enable Signet verification
    signet_handler = enable_signet_for_crewai(
        signet_url="http://localhost:8088",
        api_key="demo_key",
        forward_url="https://webhook.site/your-unique-url"
    )
    
    # Example Signet-enabled tool
    @SignetTool(
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
    
    # Create agents with Signet-enabled tools
    financial_agent = Agent(
        role='Financial Processor',
        goal='Process financial transactions securely',
        backstory='Expert in financial operations and compliance',
        tools=[create_invoice],
        verbose=True
    )
    
    # Create task
    task = Task(
        description='Create an invoice for $1000 consulting services',
        agent=financial_agent,
        expected_output='Invoice details with ID and verification'
    )
    
    # Create and wrap crew
    crew = Crew(
        agents=[financial_agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True
    )
    
    verified_crew = signet_handler.wrap_crew(crew)
    
    print("✅ Signet Protocol enabled for CrewAI")
    print(f"📋 Trace ID: {signet_handler.current_trace_id}")
    
    # Run the crew (would execute in real scenario)
    # result = verified_crew.kickoff()
    
    print(f"🔍 Verified exchanges: {len(signet_handler.verified_exchanges)}")
