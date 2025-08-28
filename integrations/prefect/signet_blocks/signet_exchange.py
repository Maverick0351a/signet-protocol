"""
Signet Protocol Prefect Block
Prefect block for creating verified exchanges.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Union
from pydantic import Field, SecretStr
from prefect.blocks.core import Block
from prefect.logging import get_run_logger
import requests


class SignetExchange(Block):
    """
    Prefect block for interacting with Signet Protocol.
    
    This block provides methods to create verified exchanges, retrieve receipt chains,
    and export signed bundles through the Signet Protocol API.
    
    Attributes:
        signet_url: The base URL of the Signet Protocol server
        api_key: API key for authentication
        tenant: Optional tenant identifier
        timeout: Request timeout in seconds
    """
    
    _block_type_name = "Signet Exchange"
    _logo_url = "https://raw.githubusercontent.com/odin-protocol/signet-protocol/main/docs/assets/signet-logo.png"
    _description = "Block for creating verified exchanges through Signet Protocol"
    
    signet_url: str = Field(
        description="Base URL of the Signet Protocol server",
        example="http://localhost:8088"
    )
    api_key: SecretStr = Field(
        description="API key for Signet Protocol authentication"
    )
    tenant: Optional[str] = Field(
        default=None,
        description="Optional tenant identifier"
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session = None
    
    @property
    def session(self) -> requests.Session:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Content-Type": "application/json",
                "X-SIGNET-API-Key": self.api_key.get_secret_value(),
                "User-Agent": "signet-prefect-block/1.0.0"
            })
        return self._session
    
    def test_connection(self) -> bool:
        """
        Test connection to Signet Protocol server.
        
        Returns:
            True if connection is successful, False otherwise
        """
        logger = get_run_logger()
        
        try:
            response = self.session.get(
                f"{self.signet_url.rstrip('/')}/healthz",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    logger.info("✅ Signet Protocol connection successful")
                    return True
            
            logger.error(f"❌ Health check failed: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Connection test failed: {str(e)}")
            return False
    
    def create_exchange(
        self,
        payload: Union[Dict[str, Any], str],
        payload_type: str = "openai.tooluse.invoice.v1",
        target_type: str = "invoice.iso20022.v1",
        forward_url: Optional[str] = None,
        trace_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a verified exchange through Signet Protocol.
        
        Args:
            payload: The data payload to exchange
            payload_type: Source payload type
            target_type: Target payload type
            forward_url: Optional URL to forward normalized data
            trace_id: Optional trace ID for chaining
            idempotency_key: Optional idempotency key
            
        Returns:
            Exchange result with receipt information
        """
        logger = get_run_logger()
        
        # Parse payload if it's a string
        if isinstance(payload, str):
            try:
                payload_data = json.loads(payload)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON payload: {payload}")
        else:
            payload_data = payload
        
        # Generate IDs if not provided
        if not trace_id:
            trace_id = f"prefect-{uuid.uuid4()}"
        if not idempotency_key:
            idempotency_key = f"{trace_id}-{uuid.uuid4()}"
        
        logger.info(f"🔄 Creating Signet exchange with trace_id: {trace_id}")
        logger.info(f"📋 Payload type: {payload_type} -> {target_type}")
        
        # Prepare exchange payload
        exchange_data = {
            "payload_type": payload_type,
            "target_type": target_type,
            "payload": payload_data,
            "trace_id": trace_id,
        }
        
        if forward_url:
            exchange_data["forward_url"] = forward_url
            logger.info(f"🎯 Forward URL: {forward_url}")
        
        # Set idempotency header
        headers = {"X-SIGNET-Idempotency-Key": idempotency_key}
        
        try:
            response = self.session.post(
                f"{self.signet_url.rstrip('/')}/v1/exchange",
                json=exchange_data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                logger.info(f"✅ Exchange created successfully")
                logger.info(f"📄 Receipt hash: {result['receipt']['receipt_hash']}")
                logger.info(f"🔗 Hop: {result['receipt']['hop']}")
                
                # Log forward result if available
                if 'forwarded' in result:
                    forward_result = result['forwarded']
                    status_code = forward_result.get('status_code', 'unknown')
                    logger.info(f"📤 Forward status: {status_code}")
                    
                    if forward_result.get('status_code', 0) >= 400:
                        logger.warning(f"⚠️ Forward failed: {forward_result}")
                
                return result
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"❌ Exchange creation failed: {str(e)}")
            raise
    
    def get_receipt_chain(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get the complete receipt chain for a trace ID.
        
        Args:
            trace_id: Trace ID to retrieve
            
        Returns:
            List of receipts in the chain, or None if not found
        """
        logger = get_run_logger()
        
        try:
            response = self.session.get(
                f"{self.signet_url.rstrip('/')}/v1/receipts/chain/{trace_id}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                chain = response.json()
                logger.info(f"📋 Retrieved chain with {len(chain)} receipts")
                return chain
            elif response.status_code == 404:
                logger.warning(f"⚠️ No chain found for trace_id: {trace_id}")
                return None
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"❌ Chain retrieval failed: {str(e)}")
            raise
    
    def export_chain(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a signed receipt chain bundle.
        
        Args:
            trace_id: Trace ID to export
            
        Returns:
            Signed export bundle with signature headers, or None if not found
        """
        logger = get_run_logger()
        
        try:
            response = self.session.get(
                f"{self.signet_url.rstrip('/')}/v1/receipts/export/{trace_id}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract signature headers
                result["signature_headers"] = {
                    "X-ODIN-Response-CID": response.headers.get("X-ODIN-Response-CID"),
                    "X-ODIN-Signature": response.headers.get("X-ODIN-Signature"),
                    "X-ODIN-KID": response.headers.get("X-ODIN-KID"),
                }
                
                logger.info(f"📤 Chain exported successfully")
                
                # Log signature info
                cid = result["signature_headers"].get("X-ODIN-Response-CID")
                if cid:
                    logger.info(f"🔐 Bundle CID: {cid}")
                
                return result
            elif response.status_code == 404:
                logger.warning(f"⚠️ No chain found for export: {trace_id}")
                return None
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"❌ Chain export failed: {str(e)}")
            raise
    
    def wait_for_receipt(
        self,
        trace_id: str,
        min_hops: int = 1,
        max_wait_seconds: int = 300,
        poll_interval: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Wait for receipt chain to reach minimum number of hops.
        
        Args:
            trace_id: Trace ID to monitor
            min_hops: Minimum number of hops to wait for
            max_wait_seconds: Maximum time to wait
            poll_interval: Polling interval in seconds
            
        Returns:
            Receipt chain when condition is met, or None if timeout
        """
        import time
        
        logger = get_run_logger()
        logger.info(f"⏳ Waiting for {min_hops} hops on trace_id: {trace_id}")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            chain = self.get_receipt_chain(trace_id)
            
            if chain and len(chain) >= min_hops:
                logger.info(f"✅ Chain reached {len(chain)} hops")
                return chain
            
            current_hops = len(chain) if chain else 0
            logger.info(f"🔄 Current hops: {current_hops}/{min_hops}")
            
            time.sleep(poll_interval)
        
        logger.warning(f"⏰ Timeout waiting for {min_hops} hops")
        return None
    
    def get_billing_dashboard(self) -> Dict[str, Any]:
        """
        Get billing dashboard data.
        
        Returns:
            Billing dashboard information
        """
        logger = get_run_logger()
        
        try:
            response = self.session.get(
                f"{self.signet_url.rstrip('/')}/v1/billing/dashboard",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                dashboard = response.json()
                
                # Log key metrics
                if "metrics" in dashboard:
                    metrics = dashboard["metrics"]
                    logger.info(f"📊 VEx usage: {metrics.get('vex_usage', 0)}")
                    logger.info(f"📊 FU usage: {metrics.get('fu_usage', 0)}")
                
                return dashboard
            else:
                response.raise_for_status()
                
        except Exception as e:
            logger.error(f"❌ Billing dashboard retrieval failed: {str(e)}")
            raise


# Prefect task decorators for common operations
def create_signet_exchange_task(signet_block: SignetExchange):
    """
    Create a Prefect task for Signet exchanges.
    
    Args:
        signet_block: Configured SignetExchange block
        
    Returns:
        Prefect task function
    """
    from prefect import task
    
    @task(name="create_signet_exchange")
    def _create_exchange(
        payload: Union[Dict[str, Any], str],
        payload_type: str = "openai.tooluse.invoice.v1",
        target_type: str = "invoice.iso20022.v1",
        forward_url: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return signet_block.create_exchange(
            payload=payload,
            payload_type=payload_type,
            target_type=target_type,
            forward_url=forward_url,
            trace_id=trace_id,
        )
    
    return _create_exchange


def get_signet_chain_task(signet_block: SignetExchange):
    """
    Create a Prefect task for retrieving Signet chains.
    
    Args:
        signet_block: Configured SignetExchange block
        
    Returns:
        Prefect task function
    """
    from prefect import task
    
    @task(name="get_signet_chain")
    def _get_chain(trace_id: str) -> Optional[List[Dict[str, Any]]]:
        return signet_block.get_receipt_chain(trace_id)
    
    return _get_chain


def export_signet_chain_task(signet_block: SignetExchange):
    """
    Create a Prefect task for exporting Signet chains.
    
    Args:
        signet_block: Configured SignetExchange block
        
    Returns:
        Prefect task function
    """
    from prefect import task
    
    @task(name="export_signet_chain")
    def _export_chain(trace_id: str) -> Optional[Dict[str, Any]]:
        return signet_block.export_chain(trace_id)
    
    return _export_chain
