"""Signet LangChain integration (packaged).

This is the packaged version moved under signet_langchain.* to allow PyPI distribution.
Original development file kept at adapters/langchain/signet_callback.py for backwards imports.
"""

from __future__ import annotations

# Re-export everything from the original module to keep logic centralized.
# The authoritative implementation currently lives at the repository root path:
# adapters/langchain/signet_callback.py

from pathlib import Path
import importlib.util
import sys

_ORIG_PATH = Path(__file__).resolve().parents[3] / "adapters" / "langchain" / "signet_callback.py"

if _ORIG_PATH.exists():
    spec = importlib.util.spec_from_file_location("_signet_callback_impl", _ORIG_PATH)
    _mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec and spec.loader
    spec.loader.exec_module(_mod)  # type: ignore
    # Re-export selected public symbols
    SignetCallbackHandler = getattr(_mod, "SignetCallbackHandler")
    SignetRunnable = getattr(_mod, "SignetRunnable")
    enable_signet_verification = getattr(_mod, "enable_signet_verification")
else:
    raise FileNotFoundError(f"Original Signet callback implementation not found at {_ORIG_PATH}")

__all__ = [
    "SignetCallbackHandler",
    "SignetRunnable",
    "enable_signet_verification",
]
