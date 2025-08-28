"""
Signet Protocol Receipt Sensor
Airflow sensor for monitoring receipt chains.
"""

from typing import Any, Dict, Optional, Sequence
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.context import Context
from airflow.utils.decorators import apply_defaults
from ..hooks.signet_hook import SignetHook


class SignetReceiptSensor(BaseSensorOperator):
    """
    Sensor that waits for a Signet receipt chain to reach a certain condition.
    
    :param trace_id: Trace ID to monitor (can be templated)
    :param min_hops: Minimum number of hops to wait for
    :param signet_conn_id: Airflow connection ID for Signet Protocol
    :param check_export: Whether to check if chain can be exported
    """
    
    template_fields: Sequence[str] = ("trace_id",)
    
    @apply_defaults
    def __init__(
        self,
        trace_id: str,
        min_hops: int = 1,
        signet_conn_id: str = "signet_default",
        check_export: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.trace_id = trace_id
        self.min_hops = min_hops
        self.signet_conn_id = signet_conn_id
        self.check_export = check_export
    
    def poke(self, context: Context) -> bool:
        """Check if the receipt chain meets the condition."""
        hook = SignetHook(signet_conn_id=self.signet_conn_id)
        
        self.log.info(f"Checking receipt chain for trace_id: {self.trace_id}")
        
        # Get the current chain
        chain = hook.get_receipt_chain(self.trace_id)
        
        if not chain:
            self.log.info(f"No chain found for trace_id: {self.trace_id}")
            return False
        
        current_hops = len(chain)
        self.log.info(f"Current chain has {current_hops} hops (need {self.min_hops})")
        
        # Check hop count
        if current_hops < self.min_hops:
            return False
        
        # Check export capability if requested
        if self.check_export:
            export_bundle = hook.export_chain(self.trace_id)
            if not export_bundle:
                self.log.info("Chain cannot be exported yet")
                return False
            
            self.log.info("Chain is exportable")
        
        self.log.info(f"Receipt chain condition met!")
        
        # Store chain in XCom for downstream tasks
        context['task_instance'].xcom_push(key='signet_chain', value=chain)
        
        return True


class SignetBillingSensor(BaseSensorOperator):
    """
    Sensor that monitors billing thresholds.
    
    :param threshold_type: Type of threshold (vex_usage, fu_usage, cost)
    :param threshold_value: Threshold value to monitor
    :param operator: Comparison operator (gt, gte, lt, lte, eq)
    :param signet_conn_id: Airflow connection ID for Signet Protocol
    """
    
    @apply_defaults
    def __init__(
        self,
        threshold_type: str,
        threshold_value: float,
        operator: str = "gte",
        signet_conn_id: str = "signet_default",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.threshold_type = threshold_type
        self.threshold_value = threshold_value
        self.operator = operator
        self.signet_conn_id = signet_conn_id
    
    def poke(self, context: Context) -> bool:
        """Check if billing threshold is met."""
        hook = SignetHook(signet_conn_id=self.signet_conn_id)
        
        self.log.info(f"Checking billing threshold: {self.threshold_type} {self.operator} {self.threshold_value}")
        
        # Get billing dashboard
        dashboard = hook.get_billing_dashboard()
        metrics = dashboard.get("metrics", {})
        
        # Get current value
        current_value = metrics.get(self.threshold_type, 0)
        self.log.info(f"Current {self.threshold_type}: {current_value}")
        
        # Compare with threshold
        if self.operator == "gt":
            result = current_value > self.threshold_value
        elif self.operator == "gte":
            result = current_value >= self.threshold_value
        elif self.operator == "lt":
            result = current_value < self.threshold_value
        elif self.operator == "lte":
            result = current_value <= self.threshold_value
        elif self.operator == "eq":
            result = current_value == self.threshold_value
        else:
            raise ValueError(f"Unknown operator: {self.operator}")
        
        if result:
            self.log.info(f"Billing threshold met: {current_value} {self.operator} {self.threshold_value}")
            
            # Store metrics in XCom
            context['task_instance'].xcom_push(key='billing_metrics', value=metrics)
        
        return result
