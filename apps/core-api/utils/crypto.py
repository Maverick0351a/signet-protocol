import base64
import time
from typing import Any

from nacl.encoding import RawEncoder
from nacl.signing import SigningKey

from .jcs import canonicalize, sha256_hexdigest


def b64url_decode_nopad(s: str) -> bytes:
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def load_signing_key(seed_b64url: str | None) -> SigningKey | None:
    if not seed_b64url:
        return None
    seed = b64url_decode_nopad(seed_b64url)
    if len(seed) != 32:
        raise ValueError("SP_PRIVATE_KEY_B64 must be a 32-byte Ed25519 seed (base64url)")
    return SigningKey(seed, encoder=RawEncoder)


def make_jwk_from_signing_key(kid: str, sk: SigningKey) -> dict[str, Any]:
    vk = sk.verify_key
    x = b64url_encode(bytes(vk))
    return {"kty": "OKP", "crv": "Ed25519", "x": x, "kid": kid, "use": "sig", "alg": "EdDSA"}


def sign_export_bundle(sk: SigningKey, kid: str, bundle: dict[str, Any]) -> dict[str, str]:
    canon = canonicalize(bundle).encode("utf-8")
    bundle_cid = "sha256:" + sha256_hexdigest(canon)
    exported_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = f"{bundle_cid}|{bundle.get('trace_id')}|{exported_at}".encode()
    sig = sk.sign(payload).signature
    return {
        "bundle_cid": bundle_cid,
        "exported_at": exported_at,
        "signature": b64url_encode(sig),
        "kid": kid,
    }
