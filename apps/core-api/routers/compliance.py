# Copyright 2025 ODIN Protocol Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

from fastapi import APIRouter, Depends, HTTPException, Query

from ..security.auth import get_api_key, get_tenant_config

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])


@router.get("/dashboard")
def compliance_dashboard(api_key: str = Depends(get_api_key)):
    """Get compliance dashboard overview."""
    tenant_config = get_tenant_config(api_key)

    return {
        "tenant": tenant_config.tenant,
        "compliance_status": "active",
        "last_audit": "2025-01-28T23:00:00Z",
        "reports_generated": {"annex_iv": 12, "pmm": 8, "risk_assessments": 5},
        "retention_policy": {
            "active": True,
            "retention_days": 2555,  # 7 years
            "auto_cleanup": True,
        },
        "ce_marking": {"status": "compliant", "last_review": "2025-01-15T00:00:00Z"},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@router.get("/annex4")
def annex4(
    trace_id: str | None = Query(default=None),
    period: str = Query(default="last_30d"),
    api_key: str = Depends(get_api_key),
):
    """Generate Annex IV compliance report."""
    try:
        tenant_config = get_tenant_config(api_key)

        # Mock Annex IV report generation
        report = {
            "report_type": "annex_iv",
            "tenant": tenant_config.tenant,
            "period": period,
            "trace_id": trace_id,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "compliance_summary": {
                "total_exchanges": 156,
                "compliant_exchanges": 156,
                "compliance_rate": 100.0,
                "risk_level": "low",
            },
            "technical_measures": {
                "encryption": "Ed25519 + AES-256",
                "integrity_verification": "SHA-256 + JCS",
                "access_controls": "API key + tenant isolation",
                "audit_logging": "comprehensive",
            },
            "organizational_measures": {
                "data_protection_officer": "appointed",
                "staff_training": "completed",
                "incident_response": "documented",
                "regular_audits": "quarterly",
            },
        }

        if trace_id:
            report["trace_analysis"] = {
                "trace_id": trace_id,
                "compliance_status": "compliant",
                "data_categories": ["transaction_data", "metadata"],
                "processing_lawfulness": "legitimate_interest",
                "retention_applied": True,
            }

        return report

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pmm")
def pmm(period: str = Query(default="last_30d"), api_key: str = Depends(get_api_key)):
    """Generate PMM (Privacy Management Measures) report."""
    try:
        tenant_config = get_tenant_config(api_key)

        # Mock PMM report generation
        return {
            "report_type": "pmm",
            "tenant": tenant_config.tenant,
            "period": period,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "privacy_measures": {
                "data_minimization": {
                    "status": "implemented",
                    "description": "Only necessary data collected and processed",
                },
                "purpose_limitation": {
                    "status": "implemented",
                    "description": "Data used only for specified exchange purposes",
                },
                "storage_limitation": {
                    "status": "implemented",
                    "description": "7-year retention policy with automated cleanup",
                },
                "accuracy": {
                    "status": "implemented",
                    "description": "Cryptographic integrity verification",
                },
                "security": {
                    "status": "implemented",
                    "description": "End-to-end encryption and access controls",
                },
                "accountability": {
                    "status": "implemented",
                    "description": "Comprehensive audit trails and compliance monitoring",
                },
            },
            "risk_assessment": {
                "overall_risk": "low",
                "technical_risks": "mitigated",
                "organizational_risks": "managed",
                "residual_risks": "acceptable",
            },
            "recommendations": [
                "Continue regular compliance monitoring",
                "Update privacy notices annually",
                "Conduct quarterly staff training",
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
