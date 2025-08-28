"""
Signet Protocol Datadog Integration
Metrics and log pipeline with trace_id correlation.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datadog import initialize, statsd, api
from datadog.api.logs import Logs
import logging
import os


class SignetDatadogIntegration:
    """
    Datadog integration for Signet Protocol monitoring and observability.
    
    Features:
    - Custom metrics for VEx and FU usage
    - Log pipeline with trace_id correlation
    - Receipt chain monitoring
    - Billing alerts and dashboards
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        app_key: Optional[str] = None,
        service_name: str = "signet-protocol",
        environment: str = "production",
        version: Optional[str] = None,
    ):
        """
        Initialize Datadog integration.
        
        Args:
            api_key: Datadog API key (or set DD_API_KEY env var)
            app_key: Datadog application key (or set DD_APP_KEY env var)
            service_name: Service name for tagging
            environment: Environment name (prod, staging, dev)
            version: Application version
        """
        self.api_key = api_key or os.getenv('DD_API_KEY')
        self.app_key = app_key or os.getenv('DD_APP_KEY')
        self.service_name = service_name
        self.environment = environment
        self.version = version
        
        if not self.api_key:
            raise ValueError("Datadog API key is required")
        
        # Initialize Datadog
        initialize(
            api_key=self.api_key,
            app_key=self.app_key,
            statsd_host=os.getenv('DD_AGENT_HOST', 'localhost'),
            statsd_port=int(os.getenv('DD_DOGSTATSD_PORT', '8125')),
        )
        
        # Setup logging
        self.logger = logging.getLogger('signet.datadog')
        
        # Common tags
        self.base_tags = [
            f'service:{self.service_name}',
            f'env:{self.environment}',
        ]
        
        if self.version:
            self.base_tags.append(f'version:{self.version}')
    
    def record_exchange_metrics(
        self,
        trace_id: str,
        tenant: str,
        vex_count: int = 1,
        fu_tokens: int = 0,
        latency_ms: Optional[float] = None,
        success: bool = True,
        policy_allowed: bool = True,
        fallback_used: bool = False,
    ) -> None:
        """
        Record exchange metrics to Datadog.
        
        Args:
            trace_id: Exchange trace ID
            tenant: Tenant identifier
            vex_count: Number of verified exchanges
            fu_tokens: Fallback units consumed
            latency_ms: Exchange latency in milliseconds
            success: Whether exchange was successful
            policy_allowed: Whether policy allowed the exchange
            fallback_used: Whether fallback processing was used
        """
        tags = self.base_tags + [
            f'tenant:{tenant}',
            f'trace_id:{trace_id}',
            f'success:{success}',
            f'policy_allowed:{policy_allowed}',
            f'fallback_used:{fallback_used}',
        ]
        
        # VEx usage
        if vex_count > 0:
            statsd.increment(
                'signet.exchange.vex.count',
                value=vex_count,
                tags=tags
            )
        
        # FU usage
        if fu_tokens > 0:
            statsd.increment(
                'signet.exchange.fu.tokens',
                value=fu_tokens,
                tags=tags
            )
        
        # Latency
        if latency_ms is not None:
            statsd.histogram(
                'signet.exchange.latency',
                value=latency_ms,
                tags=tags
            )
        
        # Success/failure rate
        statsd.increment(
            'signet.exchange.total',
            tags=tags
        )
        
        if not success:
            statsd.increment(
                'signet.exchange.errors',
                tags=tags
            )
        
        if not policy_allowed:
            statsd.increment(
                'signet.policy.denied',
                tags=tags
            )
    
    def record_receipt_metrics(
        self,
        trace_id: str,
        hop: int,
        receipt_hash: str,
        chain_length: int,
        tenant: str,
    ) -> None:
        """
        Record receipt chain metrics.
        
        Args:
            trace_id: Trace ID
            hop: Hop number in chain
            receipt_hash: Receipt hash
            chain_length: Current chain length
            tenant: Tenant identifier
        """
        tags = self.base_tags + [
            f'tenant:{tenant}',
            f'trace_id:{trace_id}',
        ]
        
        # Chain metrics
        statsd.gauge(
            'signet.chain.length',
            value=chain_length,
            tags=tags
        )
        
        statsd.histogram(
            'signet.chain.hop',
            value=hop,
            tags=tags
        )
        
        # Receipt creation
        statsd.increment(
            'signet.receipt.created',
            tags=tags + [f'receipt_hash:{receipt_hash[:16]}']
        )
    
    def record_billing_metrics(
        self,
        tenant: str,
        vex_usage: int,
        fu_usage: int,
        vex_limit: int,
        fu_limit: int,
        cost_usd: float,
    ) -> None:
        """
        Record billing and usage metrics.
        
        Args:
            tenant: Tenant identifier
            vex_usage: Current VEx usage
            fu_usage: Current FU usage
            vex_limit: VEx monthly limit
            fu_limit: FU monthly limit
            cost_usd: Current cost in USD
        """
        tags = self.base_tags + [f'tenant:{tenant}']
        
        # Usage metrics
        statsd.gauge('signet.billing.vex.usage', value=vex_usage, tags=tags)
        statsd.gauge('signet.billing.fu.usage', value=fu_usage, tags=tags)
        statsd.gauge('signet.billing.vex.limit', value=vex_limit, tags=tags)
        statsd.gauge('signet.billing.fu.limit', value=fu_limit, tags=tags)
        statsd.gauge('signet.billing.cost_usd', value=cost_usd, tags=tags)
        
        # Usage percentage
        vex_pct = (vex_usage / vex_limit * 100) if vex_limit > 0 else 0
        fu_pct = (fu_usage / fu_limit * 100) if fu_limit > 0 else 0
        
        statsd.gauge('signet.billing.vex.usage_pct', value=vex_pct, tags=tags)
        statsd.gauge('signet.billing.fu.usage_pct', value=fu_pct, tags=tags)
        
        # Alert on high usage
        if vex_pct > 80:
            statsd.increment('signet.billing.vex.high_usage_alert', tags=tags)
        
        if fu_pct > 80:
            statsd.increment('signet.billing.fu.high_usage_alert', tags=tags)
    
    def log_exchange_event(
        self,
        trace_id: str,
        tenant: str,
        event_type: str,
        payload_type: str,
        target_type: str,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log exchange events with structured data.
        
        Args:
            trace_id: Exchange trace ID
            tenant: Tenant identifier
            event_type: Type of event (exchange_created, receipt_generated, etc.)
            payload_type: Source payload type
            target_type: Target payload type
            success: Whether event was successful
            error_message: Error message if failed
            metadata: Additional metadata
        """
        log_data = {
            'timestamp': time.time(),
            'service': self.service_name,
            'environment': self.environment,
            'trace_id': trace_id,
            'tenant': tenant,
            'event_type': event_type,
            'payload_type': payload_type,
            'target_type': target_type,
            'success': success,
        }
        
        if self.version:
            log_data['version'] = self.version
        
        if error_message:
            log_data['error_message'] = error_message
        
        if metadata:
            log_data['metadata'] = metadata
        
        # Log level based on success
        level = 'INFO' if success else 'ERROR'
        log_data['level'] = level
        
        # Send to Datadog Logs
        try:
            if self.app_key:  # Only if we have app key for API access
                api.Logs.send(
                    logs=[{
                        'message': f"Signet {event_type}: {trace_id}",
                        'ddtags': ','.join(self.base_tags + [
                            f'tenant:{tenant}',
                            f'trace_id:{trace_id}',
                            f'event_type:{event_type}',
                        ]),
                        'ddsource': 'signet-protocol',
                        'service': self.service_name,
                        'hostname': os.getenv('HOSTNAME', 'unknown'),
                        **log_data
                    }]
                )
        except Exception as e:
            self.logger.error(f"Failed to send log to Datadog: {e}")
        
        # Also log locally
        if success:
            self.logger.info(f"Exchange event: {event_type} for {trace_id}", extra=log_data)
        else:
            self.logger.error(f"Exchange event failed: {event_type} for {trace_id}", extra=log_data)
    
    def log_receipt_chain_event(
        self,
        trace_id: str,
        event_type: str,
        chain_length: int,
        tenant: str,
        receipt_hashes: Optional[List[str]] = None,
        export_cid: Optional[str] = None,
    ) -> None:
        """
        Log receipt chain events.
        
        Args:
            trace_id: Trace ID
            event_type: Event type (chain_created, chain_exported, etc.)
            chain_length: Length of the chain
            tenant: Tenant identifier
            receipt_hashes: List of receipt hashes in chain
            export_cid: Export bundle CID if applicable
        """
        log_data = {
            'timestamp': time.time(),
            'service': self.service_name,
            'environment': self.environment,
            'trace_id': trace_id,
            'tenant': tenant,
            'event_type': event_type,
            'chain_length': chain_length,
        }
        
        if receipt_hashes:
            log_data['receipt_hashes'] = receipt_hashes
        
        if export_cid:
            log_data['export_cid'] = export_cid
        
        self.logger.info(f"Receipt chain event: {event_type} for {trace_id}", extra=log_data)
    
    def create_dashboard(self) -> Optional[str]:
        """
        Create a Datadog dashboard for Signet Protocol monitoring.
        
        Returns:
            Dashboard URL if successful
        """
        if not self.app_key:
            self.logger.warning("App key required to create dashboards")
            return None
        
        dashboard_config = {
            'title': 'Signet Protocol Monitoring',
            'description': 'Comprehensive monitoring for Signet Protocol verified exchanges',
            'widgets': [
                {
                    'definition': {
                        'type': 'timeseries',
                        'requests': [
                            {
                                'q': f'sum:signet.exchange.vex.count{{service:{self.service_name}}}',
                                'display_type': 'line',
                                'style': {'palette': 'dog_classic', 'line_type': 'solid', 'line_width': 'normal'}
                            }
                        ],
                        'title': 'VEx Usage Over Time',
                        'yaxis': {'scale': 'linear', 'min': 'auto', 'max': 'auto'},
                        'show_legend': True
                    },
                    'layout': {'x': 0, 'y': 0, 'width': 4, 'height': 3}
                },
                {
                    'definition': {
                        'type': 'timeseries',
                        'requests': [
                            {
                                'q': f'sum:signet.exchange.fu.tokens{{service:{self.service_name}}}',
                                'display_type': 'line',
                                'style': {'palette': 'warm', 'line_type': 'solid', 'line_width': 'normal'}
                            }
                        ],
                        'title': 'FU Token Usage',
                        'yaxis': {'scale': 'linear', 'min': 'auto', 'max': 'auto'},
                        'show_legend': True
                    },
                    'layout': {'x': 4, 'y': 0, 'width': 4, 'height': 3}
                },
                {
                    'definition': {
                        'type': 'query_value',
                        'requests': [
                            {
                                'q': f'avg:signet.exchange.latency{{service:{self.service_name}}}',
                                'aggregator': 'avg'
                            }
                        ],
                        'title': 'Average Exchange Latency (ms)',
                        'precision': 2
                    },
                    'layout': {'x': 8, 'y': 0, 'width': 4, 'height': 3}
                },
                {
                    'definition': {
                        'type': 'toplist',
                        'requests': [
                            {
                                'q': f'top(sum:signet.exchange.vex.count{{service:{self.service_name}}} by {{tenant}}, 10, "sum", "desc")',
                            }
                        ],
                        'title': 'Top Tenants by VEx Usage'
                    },
                    'layout': {'x': 0, 'y': 3, 'width': 6, 'height': 3}
                },
                {
                    'definition': {
                        'type': 'heatmap',
                        'requests': [
                            {
                                'q': f'avg:signet.chain.length{{service:{self.service_name}}} by {{tenant}}',
                            }
                        ],
                        'title': 'Receipt Chain Lengths by Tenant'
                    },
                    'layout': {'x': 6, 'y': 3, 'width': 6, 'height': 3}
                }
            ],
            'layout_type': 'ordered',
            'is_read_only': False,
            'notify_list': [],
            'template_variables': [
                {
                    'name': 'tenant',
                    'prefix': 'tenant',
                    'default': '*'
                }
            ]
        }
        
        try:
            response = api.Dashboard.create(**dashboard_config)
            dashboard_id = response['id']
            dashboard_url = f"https://app.datadoghq.com/dashboard/{dashboard_id}"
            self.logger.info(f"Created Datadog dashboard: {dashboard_url}")
            return dashboard_url
        except Exception as e:
            self.logger.error(f"Failed to create dashboard: {e}")
            return None
    
    def create_monitors(self) -> List[str]:
        """
        Create Datadog monitors for Signet Protocol alerts.
        
        Returns:
            List of monitor IDs created
        """
        if not self.app_key:
            self.logger.warning("App key required to create monitors")
            return []
        
        monitors = []
        
        # High error rate monitor
        error_rate_monitor = {
            'type': 'metric alert',
            'query': f'avg(last_5m):( sum:signet.exchange.errors{{service:{self.service_name}}} / sum:signet.exchange.total{{service:{self.service_name}}} ) * 100 > 5',
            'name': 'Signet Protocol - High Error Rate',
            'message': 'Signet Protocol error rate is above 5% @slack-alerts',
            'tags': [f'service:{self.service_name}', f'env:{self.environment}'],
            'options': {
                'thresholds': {'critical': 5, 'warning': 2},
                'notify_audit': False,
                'require_full_window': True,
                'notify_no_data': False,
                'renotify_interval': 60,
                'evaluation_delay': 60
            }
        }
        
        # High latency monitor
        latency_monitor = {
            'type': 'metric alert',
            'query': f'avg(last_10m):avg:signet.exchange.latency{{service:{self.service_name}}} > 5000',
            'name': 'Signet Protocol - High Latency',
            'message': 'Signet Protocol exchange latency is above 5 seconds @slack-alerts',
            'tags': [f'service:{self.service_name}', f'env:{self.environment}'],
            'options': {
                'thresholds': {'critical': 5000, 'warning': 2000},
                'notify_audit': False,
                'require_full_window': True,
                'notify_no_data': False,
                'renotify_interval': 60,
                'evaluation_delay': 60
            }
        }
        
        # Quota usage monitor
        quota_monitor = {
            'type': 'metric alert',
            'query': f'avg(last_15m):avg:signet.billing.vex.usage_pct{{service:{self.service_name}}} by {{tenant}} > 90',
            'name': 'Signet Protocol - VEx Quota Nearly Exceeded',
            'message': 'Tenant {{tenant.name}} VEx usage is above 90% @slack-billing',
            'tags': [f'service:{self.service_name}', f'env:{self.environment}'],
            'options': {
                'thresholds': {'critical': 90, 'warning': 80},
                'notify_audit': False,
                'require_full_window': True,
                'notify_no_data': False,
                'renotify_interval': 240,
                'evaluation_delay': 60
            }
        }
        
        monitor_configs = [error_rate_monitor, latency_monitor, quota_monitor]
        
        for config in monitor_configs:
            try:
                response = api.Monitor.create(**config)
                monitor_id = response['id']
                monitors.append(monitor_id)
                self.logger.info(f"Created monitor: {config['name']} (ID: {monitor_id})")
            except Exception as e:
                self.logger.error(f"Failed to create monitor {config['name']}: {e}")
        
        return monitors


# Convenience functions for easy integration
def initialize_signet_datadog(
    api_key: Optional[str] = None,
    app_key: Optional[str] = None,
    service_name: str = "signet-protocol",
    environment: str = "production",
    create_dashboard: bool = False,
    create_monitors: bool = False,
) -> SignetDatadogIntegration:
    """
    Initialize Signet Protocol Datadog integration with optional setup.
    
    Args:
        api_key: Datadog API key
        app_key: Datadog application key
        service_name: Service name for tagging
        environment: Environment name
        create_dashboard: Whether to create monitoring dashboard
        create_monitors: Whether to create alert monitors
        
    Returns:
        Configured SignetDatadogIntegration instance
    """
    integration = SignetDatadogIntegration(
        api_key=api_key,
        app_key=app_key,
        service_name=service_name,
        environment=environment,
    )
    
    if create_dashboard:
        integration.create_dashboard()
    
    if create_monitors:
        integration.create_monitors()
    
    return integration


# Example usage
if __name__ == "__main__":
    # Initialize integration
    dd = initialize_signet_datadog(
        service_name="signet-protocol-dev",
        environment="development",
        create_dashboard=True,
        create_monitors=True,
    )
    
    # Example metrics
    dd.record_exchange_metrics(
        trace_id="example-trace-123",
        tenant="acme-corp",
        vex_count=1,
        fu_tokens=0,
        latency_ms=150.5,
        success=True,
        policy_allowed=True,
        fallback_used=False,
    )
    
    # Example log
    dd.log_exchange_event(
        trace_id="example-trace-123",
        tenant="acme-corp",
        event_type="exchange_created",
        payload_type="openai.tooluse.invoice.v1",
        target_type="invoice.iso20022.v1",
        success=True,
        metadata={"amount": 1000, "currency": "USD"},
    )
    
    print("Datadog integration example completed!")
