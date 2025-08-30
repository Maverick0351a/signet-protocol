from typing import Any


class FallbackProvider:
    def repair(self, raw: str, schema: dict[str, Any]) -> str | None:
        raise NotImplementedError


class NullProvider(FallbackProvider):
    def repair(self, raw: str, schema: dict[str, Any]) -> str | None:
        return None
