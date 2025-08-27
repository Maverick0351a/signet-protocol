import pytest
from unittest.mock import patch, MagicMock
from server.pipeline.providers.openai_provider import OpenAIProvider, FallbackResult

class TestFallbackMetering:
    """Test fallback token counting and billing integration"""
    
    def setup_method(self):
        """Setup test environment"""
        self.provider = OpenAIProvider(api_key="test-key")
    
    @patch('openai.ChatCompletion.create')
    def test_successful_repair_with_tokens(self, mock_create):
        """Test successful repair returns token count"""
        # Mock OpenAI response with usage data - create a proper mock object
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = {"content": '{"repaired": "json"}'}
        mock_response.get.return_value = {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70
        }
        mock_create.return_value = mock_response
        
        schema = {"type": "object"}
        result = self.provider.repair_with_tokens('{"broken": "json"}', schema)
        
        assert result.success
        assert result.repaired_text == '{"repaired": "json"}'
        assert result.fu_tokens == 70
        assert result.error is None
    
    @patch('openai.ChatCompletion.create')
    def test_repair_failure_handling(self, mock_create):
        """Test repair failure returns appropriate result"""
        # Mock OpenAI API failure
        mock_create.side_effect = Exception("API Error")
        
        schema = {"type": "object"}
        result = self.provider.repair_with_tokens('{"broken": json}', schema)
        
        assert not result.success
        assert result.repaired_text is None
        assert result.fu_tokens == 0
        assert "API Error" in result.error
    
    @patch('openai.ChatCompletion.create')
    def test_code_block_extraction(self, mock_create):
        """Test extraction of JSON from code blocks"""
        # Mock response with code block
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = {"content": '```json\n{"extracted": "json"}\n```'}
        mock_response.get.return_value = {"total_tokens": 45}
        mock_create.return_value = mock_response
        
        schema = {"type": "object"}
        result = self.provider.repair_with_tokens('{"broken": "json"}', schema)
        
        assert result.success
        assert result.repaired_text == '{"extracted": "json"}'
        assert result.fu_tokens == 45
    
    def test_token_estimation(self):
        """Test token count estimation"""
        # Test various text lengths
        short_text = "hello"
        medium_text = "This is a medium length text for testing token estimation."
        long_text = "This is a much longer text that should result in a higher token count estimate. " * 10
        
        short_tokens = self.provider.estimate_tokens(short_text)
        medium_tokens = self.provider.estimate_tokens(medium_text)
        long_tokens = self.provider.estimate_tokens(long_text)
        
        assert short_tokens >= 1
        assert medium_tokens > short_tokens
        assert long_tokens > medium_tokens
        
        # Rough validation of 4 chars per token rule
        assert short_tokens == max(1, len(short_text) // 4)
    
    def test_tenant_fu_quota_disabled(self):
        """Test FU quota check when fallback is disabled"""
        tenant_config = {"fallback_enabled": False}
        
        allowed, reason = self.provider.check_tenant_fu_quota(tenant_config, 100)
        
        assert not allowed
        assert reason == "FALLBACK_DISABLED"
    
    def test_tenant_fu_quota_no_limit(self):
        """Test FU quota check with no limit configured"""
        tenant_config = {"fallback_enabled": True}
        
        allowed, reason = self.provider.check_tenant_fu_quota(tenant_config, 100)
        
        assert allowed
        assert reason == "ok"
    
    def test_tenant_fu_quota_within_limit(self):
        """Test FU quota check within monthly limit"""
        tenant_config = {
            "fallback_enabled": True,
            "fu_monthly_limit": 1000,
            "fu_used_this_month": 500
        }
        
        allowed, reason = self.provider.check_tenant_fu_quota(tenant_config, 200)
        
        assert allowed
        assert reason == "ok"
    
    def test_tenant_fu_quota_exceeded(self):
        """Test FU quota check when limit would be exceeded"""
        tenant_config = {
            "fallback_enabled": True,
            "fu_monthly_limit": 1000,
            "fu_used_this_month": 900
        }
        
        allowed, reason = self.provider.check_tenant_fu_quota(tenant_config, 200)
        
        assert not allowed
        assert "FU_QUOTA_EXCEEDED" in reason
        assert "1100/1000" in reason
    
    @patch('openai.ChatCompletion.create')
    def test_legacy_repair_method_compatibility(self, mock_create):
        """Test that legacy repair method still works"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = {"content": '{"legacy": "works"}'}
        mock_response.get.return_value = {"total_tokens": 30}
        mock_create.return_value = mock_response
        
        schema = {"type": "object"}
        result = self.provider.repair('{"broken": "json"}', schema)
        
        # Legacy method should return just the text
        assert result == '{"legacy": "works"}'
    
    @patch('openai.ChatCompletion.create')
    def test_legacy_repair_failure(self, mock_create):
        """Test legacy repair method failure handling"""
        mock_create.side_effect = Exception("API Error")
        
        schema = {"type": "object"}
        result = self.provider.repair('{"broken": json}', schema)
        
        assert result is None

class TestFallbackIntegration:
    """Test integration of fallback metering with billing system"""
    
    def test_fallback_result_structure(self):
        """Test FallbackResult data structure"""
        result = FallbackResult(
            repaired_text='{"test": "data"}',
            fu_tokens=50,
            success=True
        )
        
        assert result.repaired_text == '{"test": "data"}'
        assert result.fu_tokens == 50
        assert result.success
        assert result.error is None
    
    def test_fallback_result_failure(self):
        """Test FallbackResult for failure cases"""
        result = FallbackResult(
            repaired_text=None,
            fu_tokens=0,
            success=False,
            error="Repair failed"
        )
        
        assert result.repaired_text is None
        assert result.fu_tokens == 0
        assert not result.success
        assert result.error == "Repair failed"
    
    @patch('server.pipeline.providers.openai_provider.OpenAIProvider.repair_with_tokens')
    def test_billing_integration_mock(self, mock_repair):
        """Test how fallback results integrate with billing"""
        # Mock successful repair with token usage
        mock_repair.return_value = FallbackResult(
            repaired_text='{"fixed": "json"}',
            fu_tokens=75,
            success=True
        )
        
        provider = OpenAIProvider(api_key="test-key")
        result = provider.repair_with_tokens('{"broken": json}', {"type": "object"})
        
        # Verify the result can be used for billing
        assert result.success
        assert result.fu_tokens > 0
        
        # This is how it would be used in the main exchange flow:
        # if result.success and result.fu_tokens > 0:
        #     billing_buffer.enqueue_fu(api_key, stripe_item, result.fu_tokens)

class TestQuotaEnforcement:
    """Test quota enforcement scenarios"""
    
    def test_quota_enforcement_workflow(self):
        """Test complete quota enforcement workflow"""
        provider = OpenAIProvider(api_key="test-key")
        
        # Scenario 1: Tenant with fallback disabled
        tenant_disabled = {"fallback_enabled": False}
        estimated_tokens = provider.estimate_tokens("some broken json")
        allowed, reason = provider.check_tenant_fu_quota(tenant_disabled, estimated_tokens)
        
        assert not allowed
        assert reason == "FALLBACK_DISABLED"
        
        # Scenario 2: Tenant approaching quota limit
        tenant_near_limit = {
            "fallback_enabled": True,
            "fu_monthly_limit": 1000,
            "fu_used_this_month": 950
        }
        
        large_request_tokens = provider.estimate_tokens("very long broken json " * 100)
        allowed, reason = provider.check_tenant_fu_quota(tenant_near_limit, large_request_tokens)
        
        # Should be blocked if estimated tokens would exceed limit
        if large_request_tokens > 50:  # 1000 - 950 = 50 remaining
            assert not allowed
            assert "FU_QUOTA_EXCEEDED" in reason
    
    def test_progressive_quota_consumption(self):
        """Test how quota consumption progresses through the month"""
        provider = OpenAIProvider(api_key="test-key")
        
        # Start of month
        tenant_config = {
            "fallback_enabled": True,
            "fu_monthly_limit": 1000,
            "fu_used_this_month": 0
        }
        
        # Multiple small requests should be allowed
        for i in range(10):
            allowed, reason = provider.check_tenant_fu_quota(tenant_config, 50)
            assert allowed
            # Simulate usage increment (in real system, this would be tracked in storage)
            tenant_config["fu_used_this_month"] += 50
        
        # Now at 500 tokens used, large request should still be allowed
        allowed, reason = provider.check_tenant_fu_quota(tenant_config, 400)
        assert allowed
        
        # But request that would exceed limit should be blocked
        allowed, reason = provider.check_tenant_fu_quota(tenant_config, 600)
        assert not allowed

if __name__ == "__main__":
    pytest.main([__file__])
