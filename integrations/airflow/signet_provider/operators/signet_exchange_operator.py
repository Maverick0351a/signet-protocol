"""
Signet Protocol Exchange Operator
Airflow operator for creating verified exchanges.
"""

import json
import uuid
from typing import Any, Dict, Optional, Sequence, Union
from airflow.models import BaseOperator
from airflow.utils.context import Context
from airflow.utils.decorators import apply_defaults
from ..hooks.signet_hook import SignetHook


class SignetExchangeOperator(BaseOperator):
    """
    Operator for creating verified exchanges through Signet Protocol.
    
    This operator creates a verified exchange, optionally forwards the normalized
    data to a webhook, and stores the receipt information in XCom for downstream tasks.
    
    :param payload: The data payload to exchange (can be templated)
    :param payload_type: Source payload type (default: openai.tooluse.invoice.v1)
    :param target_type: Target payload type (default: invoice.iso20022.v1)
    :param forward_url: Optional URL to forward normalized data (can be templated)
    :param trace_id: Optional trace ID for chaining (can be templated)
    :param signet_conn_id: Airflow connection ID for Signet Protocol
    :param wait_for_forward: Whether to wait for forward response
    :param store_receipt: Whether to store receipt in XCom
    :param store_normalized: Whether to store normalized data in XCom
    """
    
    template_fields: Sequence[str] = (
        "payload",
        "forward_url", 
        "trace_id",
        "idempotency_key"
    )
    template_fields_renderers = {
        "payload": "json",
    }
    
    ui_color = "#4A90E2"
    ui_fgcolor = "#FFFFFF"
    
    @apply_defaults
    def __init__(
        self,
        payload: Union[Dict[str, Any], str],
        payload_type: str = "openai.tooluse.invoice.v1",
        target_type: str = "invoice.iso20022.v1",
        forward_url: Optional[str] = None,
        trace_id: Optional[str] = None,
        signet_conn_id: str = "signet_default",
        wait_for_forward: bool = True,
        store_receipt: bool = True,
        store_normalized: bool = True,
        idempotency_key: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.payload = payload
        self.payload_type = payload_type
        self.target_type = target_type
        self.forward_url = forward_url
        self.trace_id = trace_id
        self.signet_conn_id = signet_conn_id
        self.wait_for_forward = wait_for_forward
        self.store_receipt = store_receipt
        self.store_normalized = store_normalized
        self.idempotency_key = idempotency_key
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute the Signet exchange."""
        hook = SignetHook(signet_conn_id=self.signet_conn_id)
        
        # Parse payload if it's a string
        if isinstance(self.payload, str):
            try:
                payload_data = json.loads(self.payload)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON payload: {self.payload}")
        else:
            payload_data = self.payload
        
        # Generate trace ID if not provided
        trace_id = self.trace_id or f"airflow-{context['dag_run'].run_id}-{self.task_id}"
        
        # Generate idempotency key if not provided
        idempotency_key = self.idempotency_key or f"{trace_id}-{uuid.uuid4()}"
        
        self.log.info(f"Creating Signet exchange with trace_id: {trace_id}")
        self.log.info(f"Payload type: {self.payload_type} -> {self.target_type}")
        
        # Create the exchange
        result = hook.create_exchange(
            payload=payload_data,
            payload_type=self.payload_type,
            target_type=self.target_type,
            forward_url=self.forward_url,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )
        
        self.log.info(f"Exchange created successfully")
        self.log.info(f"Receipt hash: {result['receipt']['receipt_hash']}")
        self.log.info(f"Hop: {result['receipt']['hop']}")
        
        # Store data in XCom for downstream tasks
        if self.store_receipt:
            context['task_instance'].xcom_push(
                key='signet_receipt',
                value=result['receipt']
            )
        
        if self.store_normalized:
            context['task_instance'].xcom_push(
                key='signet_normalized',
                value=result['normalized']
            )
        
        # Store trace ID for chaining
        context['task_instance'].xcom_push(
            key='signet_trace_id',
            value=trace_id
        )
        
        # Log forward result if available
        if 'forwarded' in result:
            forward_result = result['forwarded']
            self.log.info(f"Forward status: {forward_result.get('status_code', 'unknown')}")
            if forward_result.get('status_code', 0) >= 400:
                self.log.warning(f"Forward failed: {forward_result}")
        
        return result


class SignetChainOperator(BaseOperator):
    """
    Operator for retrieving and exporting Signet receipt chains.
    
    :param trace_id: Trace ID to retrieve (can be templated)
    :param signet_conn_id: Airflow connection ID for Signet Protocol
    :param export_chain: Whether to export signed chain bundle
    :param min_hops: Minimum number of hops to wait for
    :param max_wait_seconds: Maximum time to wait for chain
    """
    
    template_fields: Sequence[str] = ("trace_id",)
    
    ui_color = "#2ECC71"
    ui_fgcolor = "#FFFFFF"
    
    @apply_defaults
    def __init__(
        self,
        trace_id: str,
        signet_conn_id: str = "signet_default",
        export_chain: bool = True,
        min_hops: int = 1,
        max_wait_seconds: int = 300,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.trace_id = trace_id
        self.signet_conn_id = signet_conn_id
        self.export_chain = export_chain
        self.min_hops = min_hops
        self.max_wait_seconds = max_wait_seconds
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute chain retrieval and export."""
        hook = SignetHook(signet_conn_id=self.signet_conn_id)
        
        self.log.info(f"Retrieving chain for trace_id: {self.trace_id}")
        
        # Wait for minimum hops if specified
        if self.min_hops > 1:
            self.log.info(f"Waiting for {self.min_hops} hops...")
            chain = hook.wait_for_receipt(
                trace_id=self.trace_id,
                min_hops=self.min_hops,
                max_wait_seconds=self.max_wait_seconds
            )
            
            if not chain:
                raise ValueError(f"Chain did not reach {self.min_hops} hops within {self.max_wait_seconds} seconds")
        else:
            chain = hook.get_receipt_chain(self.trace_id)
        
        if not chain:
            raise ValueError(f"No chain found for trace_id: {self.trace_id}")
        
        self.log.info(f"Retrieved chain with {len(chain)} receipts")
        
        result = {"chain": chain}
        
        # Export signed bundle if requested
        if self.export_chain:
            self.log.info("Exporting signed chain bundle...")
            export_bundle = hook.export_chain(self.trace_id)
            
            if export_bundle:
                result["export"] = export_bundle
                self.log.info(f"Chain exported with signature")
                
                # Log signature info
                sig_headers = export_bundle.get("signature_headers", {})
                if sig_headers.get("X-ODIN-Response-CID"):
                    self.log.info(f"Bundle CID: {sig_headers['X-ODIN-Response-CID']}")
            else:
                self.log.warning("Chain export failed")
        
        # Store in XCom
        context['task_instance'].xcom_push(key='signet_chain', value=result)
        
        return result


class SignetBillingOperator(BaseOperator):
    """
    Operator for Signet billing operations.
    
    :param operation: Billing operation (dashboard, setup_products, sync_items)
    :param signet_conn_id: Airflow connection ID for Signet Protocol
    """
    
    ui_color = "#F39C12"
    ui_fgcolor = "#FFFFFF"
    
    @apply_defaults
    def __init__(
        self,
        operation: str = "dashboard",
        signet_conn_id: str = "signet_default",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.operation = operation
        self.signet_conn_id = signet_conn_id
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute billing operation."""
        hook = SignetHook(signet_conn_id=self.signet_conn_id)
        
        if self.operation == "dashboard":
            self.log.info("Retrieving billing dashboard...")
            result = hook.get_billing_dashboard()
            
            # Log key metrics
            if "metrics" in result:
                metrics = result["metrics"]
                self.log.info(f"VEx usage: {metrics.get('vex_usage', 0)}")
                self.log.info(f"FU usage: {metrics.get('fu_usage', 0)}")
            
            context['task_instance'].xcom_push(key='billing_dashboard', value=result)
            return result
        
        else:
            raise ValueError(f"Unknown billing operation: {self.operation}")
