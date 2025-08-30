from typing import Any

from ..utils.jcs import canonicalize


def make_receipt(
    trace_id: str,
    hop: int,
    tenant: str,
    cid: str,
    policy: dict[str, Any],
    prev_receipt_hash: str | None,
) -> dict[str, Any]:
    base = {
        "trace_id": trace_id,
        "hop": hop,
        "ts": __utcnow(),
        "tenant": tenant,
        "cid": cid,
        "canon": "jcs",
        "algo": "sha256",
        "prev_receipt_hash": prev_receipt_hash,
        "policy": policy,
    }
    canon = canonicalize(base).encode("utf-8")
    rhash = "sha256:" + __sha256_hex(canon)
    base["receipt_hash"] = rhash
    return base


def __sha256_hex(b: bytes) -> str:
    import hashlib

    return hashlib.sha256(b).hexdigest()


def __utcnow():
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
