from typing import Optional, Dict, Any

class FallbackProvider:
    def repair(self, raw: str, schema: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

class NullProvider(FallbackProvider):
    def repair(self, raw: str, schema: Dict[str, Any]) -> Optional[str]:
        return None
