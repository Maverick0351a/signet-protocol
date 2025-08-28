"""
Signet Protocol Dagster IO Manager
IO manager with receipt persistence for verified exchanges.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Union
from dagster import (
    IOManager,
    InputContext,
    OutputContext,
    io_manager,
    ConfigurableResource,
    get_dagster_logger,
)
from pydantic import Field
import requests


class SignetIOManager(IOManager, ConfigurableResource):
    """
    Dagster IO manager that routes data through Signet Protocol with receipt persistence.
    
    This IO manager automatically creates verified exchanges for outputs and stores
    receipt information as metadata. It can also retrieve and validate receipt chains.
    
    Attributes:
        signet_url: Base URL of the Signet Protocol server
        api_key: API key for authentication
        auto_verify: Whether to automatically verify outputs
        store_receipts: Whether to store receipt metadata
        forward_url: Optional URL to forward normalized data
        timeout: Request timeout in seconds
    """
    
    signet_url: str = Field(
        description="Base URL of the Signet Protocol server"
    )
    api_key: str = Field(
        description="API key for Signet Protocol authentication"
    )
    auto_verify: bool = Field(
        default=True,
        description="Whether to automatically verify outputs through Signet"
    )
    store_receipts: bool = Field(
        default=True,
        description="Whether to store receipt metadata"
    )
    forward_url: Optional[str] = Field(
        default=None,
        description="Optional URL to forward normalized data"
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session = None
        self._receipts_store = {}  # In-memory receipt store
    
    @property
    def session(self) -> requests.Session:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Content-Type": "application/json",
                "X-SIGNET-API-Key": self.api_key,
                "User-Agent": "signet-dagster-io-manager/1.0.0"
            })
        return self._session
    
    def handle_output(self, context: OutputContext, obj: Any) -> None:
        """
        Handle output by creating verified exchange and storing receipt.
        
        Args:
            context: Dagster output context
            obj: The output object to handle
        """
        logger = get_dagster_logger()
        
        # Skip verification if auto_verify is disabled
        if not self.auto_verify:
            logger.info("Auto-verify disabled, skipping Signet exchange")
            return
        
        # Check if object is suitable for Signet verification
        if not self._is_verifiable(obj):
            logger.info(f"Object type {type(obj)} not suitable for Signet verification")
            return
        
        try:
            # Convert object to Signet payload
            payload = self._convert_to_signet_payload(obj, context)
            
            if not payload:
                logger.info("Could not convert object to Signet payload")
                return
            
            # Generate trace ID from run context
            run_id = context.run_id
            step_key = context.step_key
            trace_id = f"dagster-{run_id}-{step_key}"
            
            logger.info(f"🔄 Creating Signet exchange for output: {step_key}")
            logger.info(f"📋 Trace ID: {trace_id}")
            
            # Create verified exchange
            result = self._create_exchange(
                payload=payload,
                trace_id=trace_id,
                context=context
            )
            
            if result and self.store_receipts:
                # Store receipt metadata
                receipt_key = f"{run_id}:{step_key}"
                self._receipts_store[receipt_key] = {
                    "trace_id": trace_id,
                    "receipt": result["receipt"],
                    "normalized": result.get("normalized"),
                    "timestamp": result["receipt"]["ts"],
                }
                
                logger.info(f"✅ Receipt stored for {step_key}")
                logger.info(f"📄 Receipt hash: {result['receipt']['receipt_hash']}")
                
                # Add receipt metadata to context
                context.add_output_metadata({
                    "signet_trace_id": trace_id,
                    "signet_receipt_hash": result["receipt"]["receipt_hash"],
                    "signet_hop": result["receipt"]["hop"],
                    "signet_verified": True,
                })
        
        except Exception as e:
            logger.error(f"❌ Signet verification failed: {str(e)}")
            # Don't fail the pipeline, just log the error
            context.add_output_metadata({
                "signet_verified": False,
                "signet_error": str(e),
            })
    
    def load_input(self, context: InputContext) -> Any:
        """
        Load input and optionally validate receipt chain.
        
        Args:
            context: Dagster input context
            
        Returns:
            The loaded input object
        """
        logger = get_dagster_logger()
        
        # Get upstream output metadata
        upstream_output = context.upstream_output
        if upstream_output:
            metadata = upstream_output.metadata
            trace_id = metadata.get("signet_trace_id")
            
            if trace_id:
                logger.info(f"🔍 Validating receipt chain for trace_id: {trace_id}")
                
                # Retrieve and validate receipt chain
                chain = self._get_receipt_chain(trace_id)
                
                if chain:
                    logger.info(f"✅ Receipt chain validated: {len(chain)} hops")
                    
                    # Add chain metadata to input context
                    context.add_input_metadata({
                        "signet_chain_length": len(chain),
                        "signet_chain_validated": True,
                    })
                else:
                    logger.warning(f"⚠️ Could not retrieve receipt chain for {trace_id}")
        
        # For this IO manager, we don't actually load/store the data
        # We just handle the Signet verification aspect
        # The actual data loading would be handled by composition with other IO managers
        return None
    
    def _is_verifiable(self, obj: Any) -> bool:
        """Check if object is suitable for Signet verification."""
        # Check for dictionary-like objects that could be invoices
        if isinstance(obj, dict):
            # Look for invoice-like fields
            invoice_fields = ['amount', 'currency', 'invoice_id', 'customer', 'description']
            return any(field in obj for field in invoice_fields)
        
        # Check for JSON strings
        if isinstance(obj, str):
            try:
                data = json.loads(obj)
                return self._is_verifiable(data)
            except json.JSONDecodeError:
                return False
        
        return False
    
    def _convert_to_signet_payload(self, obj: Any, context: OutputContext) -> Optional[Dict[str, Any]]:
        """Convert object to Signet Protocol payload format."""
        try:
            # Parse object data
            if isinstance(obj, str):
                data = json.loads(obj)
            elif isinstance(obj, dict):
                data = obj
            else:
                return None
            
            # Create tool call format
            return {
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": "create_invoice",
                        "arguments": json.dumps(data)
                    }
                }]
            }
        
        except Exception:
            return None
    
    def _create_exchange(
        self,
        payload: Dict[str, Any],
        trace_id: str,
        context: OutputContext,
    ) -> Optional[Dict[str, Any]]:
        """Create verified exchange through Signet Protocol."""
        try:
            # Generate idempotency key
            idempotency_key = f"{trace_id}-{uuid.uuid4()}"
            
            # Prepare exchange data
            exchange_data = {
                "payload_type": "openai.tooluse.invoice.v1",
                "target_type": "invoice.iso20022.v1",
                "payload": payload,
                "trace_id": trace_id,
            }
            
            if self.forward_url:
                exchange_data["forward_url"] = self.forward_url
            
            # Set headers
            headers = {"X-SIGNET-Idempotency-Key": idempotency_key}
            
            # Make request
            response = self.session.post(
                f"{self.signet_url.rstrip('/')}/v1/exchange",
                json=exchange_data,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
        
        except Exception as e:
            get_dagster_logger().error(f"Exchange creation failed: {str(e)}")
            return None
    
    def _get_receipt_chain(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get receipt chain for trace ID."""
        try:
            response = self.session.get(
                f"{self.signet_url.rstrip('/')}/v1/receipts/chain/{trace_id}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                response.raise_for_status()
        
        except Exception as e:
            get_dagster_logger().error(f"Chain retrieval failed: {str(e)}")
            return None
    
    def get_stored_receipt(self, run_id: str, step_key: str) -> Optional[Dict[str, Any]]:
        """Get stored receipt for a specific run and step."""
        receipt_key = f"{run_id}:{step_key}"
        return self._receipts_store.get(receipt_key)
    
    def export_chain(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Export signed receipt chain bundle."""
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
                
                return result
            elif response.status_code == 404:
                return None
            else:
                response.raise_for_status()
        
        except Exception as e:
            get_dagster_logger().error(f"Chain export failed: {str(e)}")
            return None


@io_manager(
    config_schema={
        "signet_url": str,
        "api_key": str,
        "auto_verify": bool,
        "store_receipts": bool,
        "forward_url": str,
        "timeout": int,
    }
)
def signet_io_manager(context) -> SignetIOManager:
    """
    Factory function for creating SignetIOManager.
    
    Usage in Dagster:
        @job(resource_defs={"io_manager": signet_io_manager})
        def my_job():
            ...
    """
    return SignetIOManager(
        signet_url=context.resource_config["signet_url"],
        api_key=context.resource_config["api_key"],
        auto_verify=context.resource_config.get("auto_verify", True),
        store_receipts=context.resource_config.get("store_receipts", True),
        forward_url=context.resource_config.get("forward_url"),
        timeout=context.resource_config.get("timeout", 30),
    )


class SignetReceiptStore:
    """
    Persistent receipt store for Dagster runs.
    
    This class provides methods to store and retrieve receipt information
    across Dagster runs, enabling receipt chain tracking and validation.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or "signet_receipts.json"
        self._receipts = self._load_receipts()
    
    def _load_receipts(self) -> Dict[str, Any]:
        """Load receipts from storage."""
        try:
            import os
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _save_receipts(self) -> None:
        """Save receipts to storage."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self._receipts, f, indent=2)
        except Exception as e:
            get_dagster_logger().error(f"Failed to save receipts: {str(e)}")
    
    def store_receipt(
        self,
        run_id: str,
        step_key: str,
        trace_id: str,
        receipt: Dict[str, Any],
        normalized: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store receipt information."""
        receipt_key = f"{run_id}:{step_key}"
        self._receipts[receipt_key] = {
            "trace_id": trace_id,
            "receipt": receipt,
            "normalized": normalized,
            "stored_at": receipt["ts"],
        }
        self._save_receipts()
    
    def get_receipt(self, run_id: str, step_key: str) -> Optional[Dict[str, Any]]:
        """Get stored receipt."""
        receipt_key = f"{run_id}:{step_key}"
        return self._receipts.get(receipt_key)
    
    def get_receipts_by_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all receipts for a trace ID."""
        return [
            receipt for receipt in self._receipts.values()
            if receipt.get("trace_id") == trace_id
        ]
    
    def cleanup_old_receipts(self, days: int = 30) -> int:
        """Clean up receipts older than specified days."""
        import time
        from datetime import datetime, timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_ts = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        old_keys = [
            key for key, receipt in self._receipts.items()
            if receipt.get("stored_at", "") < cutoff_ts
        ]
        
        for key in old_keys:
            del self._receipts[key]
        
        if old_keys:
            self._save_receipts()
        
        return len(old_keys)
