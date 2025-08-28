"""
Signet Protocol Airflow Hook
Connection management for Signet Protocol API.
"""

import json
import uuid
from typing import Any, Dict, Optional, List
from airflow.hooks.base import BaseHook
from airflow.models import Connection
import requests


class SignetHook(BaseHook):
    """
    Hook for interacting with Signet Protocol API.
    
    :param signet_conn_id: Airflow connection ID for Signet Protocol
    :param timeout: Request timeout in seconds
    """
    
    conn_name_attr = "signet_conn_id"
    default_conn_name = "signet_default"
    conn_type = "signet"
    hook_name = "Signet Protocol"
    
    def __init__(
        self,
        signet_conn_id: str = default_conn_name,
        timeout: int = 30,
    ):
        super().__init__()
        self.signet_conn_id = signet_conn_id
        self.timeout = timeout
        self._session = None
        self._base_url = None
        self._api_key = None
    
    def get_connection_form_widgets(self) -> Dict[str, Any]:
        """Return connection form widgets for Airflow UI."""
        from wtforms import StringField
        from wtforms.widgets import TextInput
        
        return {
            "api_key": StringField("API Key", widget=TextInput()),
        }
    
    def get_ui_field_behaviour(self) -> Dict[str, Any]:
        """Return UI field behaviour for connection form."""
        return {
            "hidden_fields": ["port", "schema"],
            "relabeling": {
                "host": "Signet Protocol URL",
                "login": "Tenant ID",
                "password": "API Key",
            },
            "placeholders": {
                "host": "http://localhost:8088",
                "login": "your-tenant-id",
                "password": "your-api-key",
            },
        }
    
    def get_conn(self) -> requests.Session:
        """Get connection session."""
        if self._session is None:
            connection = self.get_connection(self.signet_conn_id)
            
            self._base_url = connection.host.rstrip('/')
            self._api_key = connection.password
            
            self._session = requests.Session()
            self._session.headers.update({
                "Content-Type": "application/json",
                "X-SIGNET-API-Key": self._api_key,
                "User-Agent": "signet-airflow-provider/1.0.0"
            })
        
        return self._session
    
    def test_connection(self) -> tuple[bool, str]:
        """Test the Signet Protocol connection."""
        try:
            session = self.get_conn()
            response = session.get(f"{self._base_url}/healthz", timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return True, "Connection successful"
                else:
                    return False, "Health check failed"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def create_exchange(
        self,
        payload: Dict[str, Any],
        payload_type: str = "openai.tooluse.invoice.v1",
        target_type: str = "invoice.iso20022.v1",
        forward_url: Optional[str] = None,
        trace_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a verified exchange through Signet Protocol.
        
        :param payload: The data payload to exchange
        :param payload_type: Source payload type
        :param target_type: Target payload type
        :param forward_url: Optional URL to forward normalized data
        :param trace_id: Optional trace ID for chaining
        :param idempotency_key: Optional idempotency key
        :return: Exchange result with receipt
        """
        session = self.get_conn()
        
        # Generate IDs if not provided
        if not trace_id:
            trace_id = f"airflow-{uuid.uuid4()}"
        if not idempotency_key:
            idempotency_key = f"{trace_id}-{uuid.uuid4()}"
        
        # Prepare exchange payload
        exchange_data = {
            "payload_type": payload_type,
            "target_type": target_type,
            "payload": payload,
            "trace_id": trace_id,
        }
        
        if forward_url:
            exchange_data["forward_url"] = forward_url
        
        # Set idempotency header
        headers = {"X-SIGNET-Idempotency-Key": idempotency_key}
        
        response = session.post(
            f"{self._base_url}/v1/exchange",
            json=exchange_data,
            headers=headers,
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_receipt_chain(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get the complete receipt chain for a trace ID.
        
        :param trace_id: Trace ID to retrieve
        :return: List of receipts in the chain
        """
        session = self.get_conn()
        
        response = session.get(
            f"{self._base_url}/v1/receipts/chain/{trace_id}",
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()
    
    def export_chain(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a signed receipt chain bundle.
        
        :param trace_id: Trace ID to export
        :return: Signed export bundle
        """
        session = self.get_conn()
        
        response = session.get(
            f"{self._base_url}/v1/receipts/export/{trace_id}",
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            # Extract signature headers
            result = response.json()
            result["signature_headers"] = {
                "X-ODIN-Response-CID": response.headers.get("X-ODIN-Response-CID"),
                "X-ODIN-Signature": response.headers.get("X-ODIN-Signature"),
                "X-ODIN-KID": response.headers.get("X-ODIN-KID"),
            }
            return result
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()
    
    def wait_for_receipt(
        self,
        trace_id: str,
        min_hops: int = 1,
        max_wait_seconds: int = 300,
        poll_interval: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Wait for receipt chain to reach minimum number of hops.
        
        :param trace_id: Trace ID to monitor
        :param min_hops: Minimum number of hops to wait for
        :param max_wait_seconds: Maximum time to wait
        :param poll_interval: Polling interval in seconds
        :return: Receipt chain when condition is met
        """
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            chain = self.get_receipt_chain(trace_id)
            
            if chain and len(chain) >= min_hops:
                return chain
            
            time.sleep(poll_interval)
        
        return None
    
    def get_billing_dashboard(self) -> Dict[str, Any]:
        """Get billing dashboard data."""
        session = self.get_conn()
        
        response = session.get(
            f"{self._base_url}/v1/billing/dashboard",
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
