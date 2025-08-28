# Signet Protocol Airflow Provider

Apache Airflow provider for Signet Protocol verified exchanges.

## Installation

```bash
pip install signet-airflow-provider
```

## Configuration

1. Create a Signet connection in Airflow:
   - Connection ID: `signet_default`
   - Connection Type: `signet`
   - Host: `http://localhost:8088` (your Signet Protocol server)
   - Login: `your-tenant-id`
   - Password: `your-api-key`

## Usage

### Basic Exchange

```python
from datetime import datetime, timedelta
from airflow import DAG
from signet_provider.operators import SignetExchangeOperator

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'signet_invoice_processing',
    default_args=default_args,
    description='Process invoices through Signet Protocol',
    schedule_interval=timedelta(hours=1),
    catchup=False,
)

# Create verified exchange
create_exchange = SignetExchangeOperator(
    task_id='create_verified_exchange',
    payload={
        "tool_calls": [{
            "type": "function",
            "function": {
                "name": "create_invoice",
                "arguments": '{"amount": 1000, "currency": "USD", "customer": "Acme Corp"}'
            }
        }]
    },
    forward_url="https://your-webhook.com/receive",
    dag=dag,
)
```

### Chain Monitoring

```python
from signet_provider.operators import SignetChainOperator
from signet_provider.sensors import SignetReceiptSensor

# Wait for chain to reach 3 hops
wait_for_chain = SignetReceiptSensor(
    task_id='wait_for_chain_completion',
    trace_id="{{ task_instance.xcom_pull(task_ids='create_verified_exchange', key='signet_trace_id') }}",
    min_hops=3,
    timeout=300,
    poke_interval=30,
    dag=dag,
)

# Export the complete chain
export_chain = SignetChainOperator(
    task_id='export_receipt_chain',
    trace_id="{{ task_instance.xcom_pull(task_ids='create_verified_exchange', key='signet_trace_id') }}",
    export_chain=True,
    dag=dag,
)

create_exchange >> wait_for_chain >> export_chain
```

### Billing Monitoring

```python
from signet_provider.operators import SignetBillingOperator
from signet_provider.sensors import SignetBillingSensor

# Monitor VEx usage
billing_alert = SignetBillingSensor(
    task_id='check_vex_usage',
    threshold_type='vex_usage',
    threshold_value=1000,
    operator='gte',
    timeout=3600,
    poke_interval=300,
    dag=dag,
)

# Get billing dashboard
get_billing = SignetBillingOperator(
    task_id='get_billing_dashboard',
    operation='dashboard',
    dag=dag,
)

billing_alert >> get_billing
```

## Operators

### SignetExchangeOperator

Creates a verified exchange through Signet Protocol.

**Parameters:**
- `payload`: Data payload to exchange
- `payload_type`: Source payload type (default: `openai.tooluse.invoice.v1`)
- `target_type`: Target payload type (default: `invoice.iso20022.v1`)
- `forward_url`: Optional URL to forward normalized data
- `trace_id`: Optional trace ID for chaining
- `signet_conn_id`: Airflow connection ID

### SignetChainOperator

Retrieves and exports Signet receipt chains.

**Parameters:**
- `trace_id`: Trace ID to retrieve
- `export_chain`: Whether to export signed chain bundle
- `min_hops`: Minimum number of hops to wait for

### SignetBillingOperator

Performs billing operations.

**Parameters:**
- `operation`: Billing operation (`dashboard`)
- `signet_conn_id`: Airflow connection ID

## Sensors

### SignetReceiptSensor

Waits for receipt chains to meet conditions.

**Parameters:**
- `trace_id`: Trace ID to monitor
- `min_hops`: Minimum number of hops
- `check_export`: Whether to check exportability

### SignetBillingSensor

Monitors billing thresholds.

**Parameters:**
- `threshold_type`: Type of threshold (`vex_usage`, `fu_usage`)
- `threshold_value`: Threshold value
- `operator`: Comparison operator (`gt`, `gte`, `lt`, `lte`, `eq`)

## XCom Keys

The operators store data in XCom with these keys:

- `signet_receipt`: Receipt information
- `signet_normalized`: Normalized payload data
- `signet_trace_id`: Trace ID for chaining
- `signet_chain`: Complete receipt chain
- `billing_dashboard`: Billing dashboard data
- `billing_metrics`: Billing metrics

## Examples

See the `examples/` directory for complete DAG examples:

- `invoice_processing_dag.py`: Basic invoice processing workflow
- `multi_hop_chain_dag.py`: Multi-hop receipt chain processing
- `billing_monitoring_dag.py`: Billing threshold monitoring
