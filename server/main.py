#!/usr/bin/env python3
"""
Signet Protocol Server - Trust Fabric for AI-to-AI Communications

Main FastAPI application entry point providing:
- Verified Exchanges (VEx) with cryptographic receipts
- HEL egress control and policy enforcement
- Enterprise billing and metering
- Comprehensive monitoring and health checks
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel

from .settings import get_settings
from .pipeline.receipts import ReceiptManager
from .pipeline.billing import BillingManager
from .pipeline.policy import PolicyEngine
from .pipeline.forward import ForwardManager
from .pipeline.storage import get_storage
from .utils.crypto import SigningManager

# Metrics
REQUEST_COUNT = Counter('signet_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('signet_request_duration_seconds', 'Request duration')
EXCHANGE_COUNT = Counter('signet_exchanges_total', 'Total exchanges', ['tenant', 'api_key'])
DENIED_COUNT = Counter('signet_denied_total', 'Denied requests', ['reason', 'tenant'])

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExchangeRequest(BaseModel):
    """Request model for verified exchanges"""
    payload_type: str
    target_type: str
    payload: Dict[str, Any]
    forward_url: str
    idempotency_key: str = None


class HealthResponse(BaseModel):
    """Health check response model"""
    ok: bool
    storage: str
    ts: str
    version: str = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Signet Protocol Server")
    
    # Initialize components
    settings = get_settings()
    storage = get_storage(settings.database_url)
    
    # Store in app state
    app.state.settings = settings
    app.state.storage = storage
    app.state.receipt_manager = ReceiptManager(storage)
    app.state.billing_manager = BillingManager(storage)
    app.state.policy_engine = PolicyEngine(settings)
    app.state.forward_manager = ForwardManager()
    app.state.signing_manager = SigningManager(settings.private_key)
    
    logger.info("Signet Protocol Server started successfully")
    yield
    
    logger.info("Shutting down Signet Protocol Server")


# Create FastAPI app
app = FastAPI(
    title="Signet Protocol",
    description="Trust Fabric for AI-to-AI Communications",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect metrics"""
    start_time = time.time()
    
    response = await call_next(request)
    
    # Record metrics
    duration = time.time() - start_time
    REQUEST_DURATION.observe(duration)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    return response


async def get_api_key(x_signet_api_key: str = Header(..., alias="X-SIGNET-API-Key")):
    """Dependency to extract and validate API key"""
    if not x_signet_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    return x_signet_api_key


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        storage_type = "sqlite" if "sqlite" in str(app.state.storage) else "postgresql"
        return HealthResponse(
            ok=True,
            storage=storage_type,
            ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/.well-known/jwks.json")
async def jwks():
    """JSON Web Key Set for signature verification"""
    public_key = app.state.signing_manager.get_public_key_jwk()
    return {"keys": [public_key]}


@app.post("/v1/exchange")
async def verified_exchange(
    request: ExchangeRequest,
    api_key: str = Depends(get_api_key),
    x_signet_idempotency_key: str = Header(None, alias="X-SIGNET-Idempotency-Key")
):
    """Main verified exchange endpoint"""
    try:
        # Use idempotency key from header or request body
        idempotency_key = x_signet_idempotency_key or request.idempotency_key
        
        # Policy check
        policy_result = await app.state.policy_engine.check_policy(
            request.forward_url, api_key
        )
        if not policy_result.allowed:
            DENIED_COUNT.labels(reason=policy_result.reason, tenant=api_key).inc()
            raise HTTPException(status_code=403, detail=policy_result.reason)
        
        # Check billing limits
        billing_check = await app.state.billing_manager.check_limits(api_key)
        if not billing_check.allowed:
            DENIED_COUNT.labels(reason="billing_limit", tenant=api_key).inc()
            raise HTTPException(status_code=429, detail="Billing limit exceeded")
        
        # Process exchange
        result = await app.state.receipt_manager.process_exchange(
            payload_type=request.payload_type,
            target_type=request.target_type,
            payload=request.payload,
            forward_url=request.forward_url,
            api_key=api_key,
            idempotency_key=idempotency_key
        )
        
        # Record metrics
        EXCHANGE_COUNT.labels(tenant=api_key, api_key=api_key).inc()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exchange failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/v1/receipts/{receipt_id}")
async def get_receipt(
    receipt_id: str,
    api_key: str = Depends(get_api_key)
):
    """Retrieve a specific receipt"""
    try:
        receipt = await app.state.receipt_manager.get_receipt(receipt_id, api_key)
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        return receipt
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get receipt: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/v1/export/{tenant_id}")
async def export_audit_trail(
    tenant_id: str,
    api_key: str = Depends(get_api_key)
):
    """Export signed audit trail bundle"""
    try:
        # Verify tenant access
        if tenant_id != api_key:  # Simplified tenant check
            raise HTTPException(status_code=403, detail="Access denied")
        
        bundle = await app.state.receipt_manager.export_audit_trail(tenant_id)
        return bundle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export audit trail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)