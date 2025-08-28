from typing import Optional, Dict, Any, Tuple
import os, json
import openai

SYSTEM_PROMPT = """You repair JSON ONLY.
- Output ONLY a JSON object that validates against the provided JSON Schema.
- Do not invent fields or values. If something is missing, set it to null or omit it.
- No explanations. No prose. Output must be valid JSON.
"""

class FallbackResult:
    """Result of a fallback repair operation with token usage"""
    def __init__(self, repaired_text: Optional[str], fu_tokens: int, success: bool = True, error: Optional[str] = None):
        self.repaired_text = repaired_text
        self.fu_tokens = fu_tokens  # Fallback Units (tokens consumed)
        self.success = success
        self.error = error

class OpenAIProvider:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        key = api_key or os.getenv("SP_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("SP_OPENAI_API_KEY/OPENAI_API_KEY not set")
        openai.api_key = key
        self.model = model

    def repair(self, raw: str, schema: Dict[str, Any]) -> Optional[str]:
        """Legacy repair method - returns only the repaired text"""
        result = self.repair_with_tokens(raw, schema)
        return result.repaired_text if result.success else None

    def repair_with_tokens(self, raw: str, schema: Dict[str, Any]) -> FallbackResult:
        """
        Repair JSON with token counting for billing.
        Returns FallbackResult with token usage information.
        """
        schema_str = json.dumps(schema)
        try:
            resp = openai.ChatCompletion.create(
                model=self.model,
                temperature=0,
                max_tokens=800,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Schema:\\n{schema_str}\\n---\\nBroken JSON:\\n{raw}"}
                ]
            )
            
            # Extract token usage
            usage = resp.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            
            # Extract repaired content
            txt = resp.choices[0].message["content"].strip()
            if txt.startswith("```"):
                parts = txt.split("```")
                if len(parts) >= 2:
                    txt = parts[1].strip()
                    if txt.startswith("json"):
                        txt = txt[4:].strip()
            
            return FallbackResult(
                repaired_text=txt,
                fu_tokens=total_tokens,
                success=True
            )
            
        except Exception as e:
            return FallbackResult(
                repaired_text=None,
                fu_tokens=0,
                success=False,
                error=str(e)[:200]
            )

    def estimate_tokens(self, text: str) -> int:
        """
        Rough estimation of token count for rate limiting.
        OpenAI typically uses ~4 characters per token for English text.
        """
        return max(1, len(text) // 4)

    def check_tenant_fu_quota(self, tenant_config: Dict[str, Any], estimated_tokens: int) -> Tuple[bool, str]:
        """
        Check if tenant has sufficient FU quota for the estimated token usage.
        Returns (allowed, reason)
        """
        if not tenant_config.get("fallback_enabled", False):
            return False, "FALLBACK_DISABLED"
        
        # Check if tenant has FU limits configured
        fu_limit = tenant_config.get("fu_monthly_limit")
        if fu_limit is None:
            return True, "ok"  # No limit configured
        
        # In a real implementation, you'd check current month usage from storage
        # For now, we'll assume quota is available
        fu_used_this_month = tenant_config.get("fu_used_this_month", 0)
        
        if fu_used_this_month + estimated_tokens > fu_limit:
            return False, f"FU_QUOTA_EXCEEDED: {fu_used_this_month + estimated_tokens}/{fu_limit}"
        
        return True, "ok"
