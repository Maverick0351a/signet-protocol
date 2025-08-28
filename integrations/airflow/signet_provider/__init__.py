"""
Signet Protocol Airflow Provider
Apache Airflow integration for verified AI-to-AI communications.
"""

__version__ = "1.0.0"

def get_provider_info():
    return {
        "package-name": "signet-airflow-provider",
        "name": "Signet Protocol Provider",
        "description": "Apache Airflow provider for Signet Protocol verified exchanges",
        "versions": [__version__],
        "operators": [
            "signet_provider.operators.SignetExchangeOperator",
        ],
        "hooks": [
            "signet_provider.hooks.SignetHook",
        ],
        "sensors": [
            "signet_provider.sensors.SignetReceiptSensor",
        ],
    }
