import os, json, time, uuid, pathlib
from typing import Optional, Dict, Any
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .settings import load_settings, create_storage_from_settings
from .pipeline.sanitize import sanitize_payload
from .pipeline.repair import repair_json_string
from .pipeline.fallback import NullProvider
from .pipeline.providers.openai_provider import OpenAIProvider
from .pipeline.transform import transform
from .pipeline.policy import hel_allow_forward
from .pipeline.forward import safe_forward
from .pipeline.storage import StorageConflict
from .pipeline.receipts import make_receipt
from .pipeline.metrics import exchanges_total, denied_total, forward_total, repair_attempts_total, fallback_used_total, latency_hist
from .utils.jcs import cid_for_json, canonicalize
from .utils.crypto import load_signing_key, make_jwk_from_signing_key, sign_export_bundle
from fastjsonschema import compile as compile_schema

app = FastAPI(title="Signet Protocol", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SET = load_settings()
STORE = create_storage_from_settings(SET)

# Signing
SK = load_signing_key(SET.private_key_b64) if SET.private_key_b64 else None
KID = SET.kid

# Fallback provider (optional)
if SET.openai_api_key:
    try:
        FALLBACK = OpenAIProvider(api_key=SET.openai_api_key)
    except Exception:
        FALLBACK = NullProvider()
else:
    FALLBACK = NullProvider()

# Load schemas & mapping (invoice demo)
base = pathlib.Path(__file__).parent
with open(base / "schemas" / "types" / "openai.tooluse.invoice.v1.schema.json") as f:
    SCHEMA_FROM = json.load(f)
with open(base / "schemas" / "types" / "invoice.iso20022.v1.schema.json") as f:
    SCHEMA_TO = json.load(f)
with open(base / "schemas" / "maps" / "openai.tooluse.invoice.v1__invoice.iso20022.v1.json") as f:
    MAP_INV = json.load(f)

validate_from = compile_schema(SCHEMA_FROM)
validate_to = compile_schema(SCHEMA_TO)

def utcnow():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

@app.get("/healthz")
def healthz():
    return {"ok": True, "storage": "sqlite", "ts": utcnow()}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/.well-known/jwks.json")
def jwks():
    keys = []
    if SK and KID:
        keys.append(make_jwk_from_signing_key(KID, SK))
    return {"keys": keys}

@app.get("/v1/receipts/chain/{trace_id}")
def get_chain(trace_id: str):
    return STORE.get_chain(trace_id)

@app.get("/v1/receipts/export/{trace_id}")
def export_chain(trace_id: str, response: Response):
    chain = STORE.get_chain(trace_id)
    if not chain:
        raise HTTPException(status_code=404, detail="trace not found")
    bundle = {"trace_id": trace_id, "chain": chain, "exported_at": utcnow()}
    if SK and KID:
        signed = sign_export_bundle(SK, KID, bundle)
        response.headers["X-ODIN-Response-CID"] = signed["bundle_cid"]
        response.headers["X-ODIN-Signature"] = signed["signature"]
        response.headers["X-ODIN-KID"] = signed["kid"]
    return bundle

@app.post("/v1/exchange")
def exchange(
    req: Request,
    body: Dict[str, Any],
    x_odin_api_key: Optional[str] = Header(None, alias="X-ODIN-API-Key"),
    x_signet_api_key: Optional[str] = Header(None, alias="X-SIGNET-API-Key"),
    x_odin_idempotency_key: Optional[str] = Header(None, alias="X-ODIN-Idempotency-Key"),
    x_signet_idempotency_key: Optional[str] = Header(None, alias="X-SIGNET-Idempotency-Key"),
):
    t0 = time.time()
    # Auth (accept either header)
    api_key = x_odin_api_key or x_signet_api_key
    idem_key = x_odin_idempotency_key or x_signet_idempotency_key
    if not api_key:
        raise HTTPException(status_code=401, detail="missing api key header")
    if not idem_key:
        raise HTTPException(status_code=400, detail="missing idempotency header")

    tenant_cfg = SET.api_keys.get(api_key)
    if not tenant_cfg:
        raise HTTPException(status_code=401, detail="invalid api key")

    # Idempotency
    cached = STORE.get_idempotent(api_key, idem_key)
    if cached:
        return JSONResponse(cached, headers={"X-SIGNET-Idempotency-Hit": "1"})

    # Sanitize
    body = sanitize_payload(body)

    # Basic fields
    trace_id = body.get("trace_id") or str(uuid.uuid4())
    payload_type = body.get("payload_type")
    target_type = body.get("target_type")
    payload = body.get("payload")
    forward_url = body.get("forward_url")

    if not (payload_type and target_type and payload):
        raise HTTPException(status_code=422, detail="missing payload_type/target_type/payload")

    # Validate input schema (invoice demo map)
    if payload_type != "openai.tooluse.invoice.v1" or target_type != "invoice.iso20022.v1":
        raise HTTPException(status_code=422, detail="unsupported mapping in MVP")
    try:
        validate_from(payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"input schema invalid: {str(e)[:200]}")

    # Parse embedded arguments JSON with heuristics, fallback optional
    fu_tokens_used = 0
    fallback_used = False
    semantic_violations = []
    
    try:
        args_str = payload["tool_calls"][0]["function"]["arguments"]
        repair_attempts_total.inc()
        args_obj = None
        try:
            args_obj = repair_json_string(args_str)
        except Exception:
            args_obj = None
        
        if args_obj is None and tenant_cfg.fallback_enabled:
            try:
                fb = OpenAIProvider(SET.openai_api_key)
                
                # Check FU quota before attempting repair
                estimated_tokens = fb.estimate_tokens(args_str)
                quota_allowed, quota_reason = fb.check_tenant_fu_quota(tenant_cfg.dict(), estimated_tokens)
                
                if not quota_allowed:
                    raise HTTPException(status_code=429, detail=f"Fallback quota exceeded: {quota_reason}")
                
                # Perform repair with token tracking
                repair_result = fb.repair_with_tokens(args_str, {"type":"object"})
                if repair_result.success and repair_result.repaired_text:
                    # Validate semantic invariants
                    from .pipeline.semantic_invariants import validate_fallback_result
                    
                    is_valid, error_messages, violations = validate_fallback_result(
                        args_str, 
                        repair_result.repaired_text,
                        {"type": "object"}
                    )
                    
                    if not is_valid:
                        # Semantic invariants failed - deny the exchange
                        semantic_violations = [v.message for v in violations]
                        raise HTTPException(
                            status_code=422, 
                            detail=f"Fallback repair violated semantic invariants: {'; '.join(error_messages[:3])}"
                        )
                    
                    fallback_used_total.inc()
                    fu_tokens_used = repair_result.fu_tokens
                    fallback_used = True
                    args_obj = json.loads(repair_result.repaired_text)
                elif repair_result.error:
                    print(f"Fallback repair failed: {repair_result.error}")
            except HTTPException:
                raise  # Re-raise quota errors
            except Exception as e:
                print(f"Fallback provider error: {str(e)[:200]}")
                args_obj = None
        
        if args_obj is None:
            raise ValueError("could not parse function.arguments")
        payload["tool_calls"][0]["function"]["arguments"] = args_obj
    except HTTPException:
        raise  # Re-raise HTTP exceptions (like quota errors)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"arguments parse/repair failed: {str(e)[:200]}")

    # Transform
    normalized = transform(payload, MAP_INV)

    # Validate target schema
    try:
        validate_to(normalized)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"normalized schema invalid: {str(e)[:200]}")

    # Policy
    tenant_allow = tenant_cfg.allowlist or []
    policy = hel_allow_forward(tenant_allow, SET.hel_allowlist, forward_url)
    if not policy.allowed:
        denied_total.labels(reason=str(policy.get("reason"))).inc()
        raise HTTPException(status_code=403, detail=policy.get("reason"))

    # Optional forward
    forwarded = None
    if forward_url:
        forwarded = safe_forward(forward_url, normalized)
        if forwarded.get("status_code", 599) < 600:
            forward_total.labels(host=forwarded.get("host","")).inc()

    # Receipts
    cid = cid_for_json(normalized)
    head = STORE.get_head(trace_id)
    prev_hash = head["last_receipt_hash"] if head else None
    receipt = make_receipt(trace_id, hop=(head["last_hop"]+1 if head else 1), tenant=tenant_cfg.tenant, cid=cid, policy=dict(policy), prev_receipt_hash=prev_hash)
    
    # Add fallback usage and semantic violation info to receipt
    if fallback_used:
        receipt["fallback_used"] = True
        receipt["fu_tokens"] = fu_tokens_used
    if semantic_violations:
        receipt["semantic_violations"] = semantic_violations

    try:
        hop = STORE.append_receipt(receipt, expected_prev=prev_hash)
    except StorageConflict:
        raise HTTPException(status_code=409, detail="chain conflict")

    # Usage & billing (VEx = 1; FU tokens counted)
    STORE.record_usage(api_key, tenant_cfg.tenant, trace_id, hop, True, 1, fu_tokens_used, receipt["ts"])
    from .pipeline.billing import BillingBuffer
    BB = BillingBuffer(STORE, SET.stripe_api_key, SET.reserved_config_path)
    
    # Bill for VEx (Verified Exchange)
    if tenant_cfg.stripe_item_vex:
        BB.enqueue_vex(api_key, tenant_cfg.stripe_item_vex, units=1, tenant=tenant_cfg.tenant)
    
    # Bill for FU (Fallback Units) if used
    if fu_tokens_used > 0 and tenant_cfg.stripe_item_fu:
        BB.enqueue_fu(api_key, tenant_cfg.stripe_item_fu, fu_tokens_used, tenant=tenant_cfg.tenant)

    resp = {
        "trace_id": trace_id,
        "normalized": normalized,
        "policy": {"engine":"HEL","allowed": True, "reason": "ok"},
        "receipt": {
            "ts": receipt["ts"],
            "cid": cid,
            "receipt_hash": receipt["receipt_hash"],
            "prev_receipt_hash": prev_hash if prev_hash else None,
            "hop": hop
        }
    }
    if forward_url:
        resp["forwarded"] = forwarded

    # Cache idempotent
    STORE.cache_idempotent(api_key, idem_key, resp)

    exchanges_total.inc()
    latency_hist.labels(phase="total").observe(time.time() - t0)
    headers = {"X-SIGNET-Trace": trace_id, "X-ODIN-Trace": trace_id}
    return JSONResponse(resp, headers=headers)
