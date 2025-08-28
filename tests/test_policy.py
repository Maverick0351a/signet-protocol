import pytest
import socket
from unittest.mock import patch, MagicMock
from server.pipeline.net import resolve_public_ips
from server.pipeline.forward import safe_forward, select_public_ip

class TestIPValidation:
    """Test IP validation and SSRF protection"""
    
    def test_localhost_blocked(self):
        """Test that localhost IPs are blocked"""
        success, reason = resolve_public_ips("localhost")
        assert not success
        assert "LOOPBACK" in reason
    
    def test_private_ips_blocked(self):
        """Test that private IPs are blocked"""
        success, reason = resolve_public_ips("192.168.1.1")
        assert not success
        assert "PRIVATE" in reason
    
    def test_link_local_blocked(self):
        """Test that link-local IPs are blocked"""
        success, reason = resolve_public_ips("169.254.1.1")
        assert not success
        # Link-local IPs are categorized as private in our implementation
        assert "PRIVATE" in reason or "LINKLOCAL" in reason
    
    @patch('socket.getaddrinfo')
    def test_public_ip_allowed(self, mock_getaddrinfo):
        """Test that public IPs are allowed"""
        # Mock DNS resolution to return a public IP
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 80))
        ]
        
        success, reason = resolve_public_ips("example.com")
        assert success
        assert reason == "ok"
    
    @patch('socket.getaddrinfo')
    def test_mixed_ips_blocked(self, mock_getaddrinfo):
        """Test that domains resolving to mixed public/private IPs are blocked"""
        # Mock DNS resolution to return both public and private IPs
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.1', 80))
        ]
        
        success, reason = resolve_public_ips("mixed-example.com")
        assert not success
        assert "PRIVATE" in reason
    
    def test_idn_domain_handling(self):
        """Test International Domain Name handling"""
        # Test with IDN domain (should be encoded properly)
        success, reason = resolve_public_ips("xn--nxasmq6b")  # IDN for 中国
        # This will likely fail resolution, but should not crash
        assert not success
        assert "RESOLUTION_FAILED" in reason or "NO_RESOLUTION" in reason

class TestForwardingSecurity:
    """Test secure forwarding with IP pinning"""
    
    @patch('server.pipeline.forward.select_public_ip')
    @patch('requests.Session')
    def test_https_ip_pinning(self, mock_session_class, mock_select_ip):
        """Test HTTPS requests use IP pinning"""
        # Mock IP selection
        mock_select_ip.return_value = (True, "ok", "8.8.8.8")
        
        # Mock session and response
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content.return_value = [b'test response']
        mock_session.post.return_value = mock_response
        
        result = safe_forward("https://example.com/api", {"test": "data"})
        
        assert result["status_code"] == 200
        assert result["pinned_ip"] == "8.8.8.8"
        assert "response_size" in result
        mock_select_ip.assert_called_once_with("example.com")
    
    @patch('server.pipeline.forward.select_public_ip')
    def test_ip_validation_failure_blocks_request(self, mock_select_ip):
        """Test that IP validation failure blocks the request"""
        # Mock IP validation failure
        mock_select_ip.return_value = (False, "HEL_RESOLVED_PRIVATE", None)
        
        result = safe_forward("https://192.168.1.1/api", {"test": "data"})
        
        assert result["status_code"] == 403
        assert "IP validation failed" in result["error"]
    
    @patch('server.pipeline.forward.select_public_ip')
    @patch('requests.Session')
    def test_response_size_limit(self, mock_session_class, mock_select_ip):
        """Test response size limiting"""
        # Mock IP selection
        mock_select_ip.return_value = (True, "ok", "8.8.8.8")
        
        # Mock session and large response
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(2 * 1024 * 1024)}  # 2MB
        mock_session.post.return_value = mock_response
        
        result = safe_forward("https://example.com/api", {"test": "data"})
        
        assert result["status_code"] == 413
        assert "too large" in result["error"]
    
    @patch('server.pipeline.forward.select_public_ip')
    @patch('requests.Session')
    def test_streaming_size_limit(self, mock_session_class, mock_select_ip):
        """Test streaming response size limiting"""
        # Mock IP selection
        mock_select_ip.return_value = (True, "ok", "8.8.8.8")
        
        # Mock session and response that exceeds limit during streaming
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        # Return chunks that exceed 1MB total
        large_chunk = b'x' * (512 * 1024)  # 512KB chunks
        mock_response.iter_content.return_value = [large_chunk, large_chunk, large_chunk]  # 1.5MB total
        mock_session.post.return_value = mock_response
        
        result = safe_forward("https://example.com/api", {"test": "data"})
        
        assert result["status_code"] == 413
        assert "exceeds" in result["error"]
    
    def test_invalid_url_handling(self):
        """Test handling of invalid URLs"""
        result = safe_forward("not-a-url", {"test": "data"})
        assert result["status_code"] == 599
        assert "Invalid URL" in result["error"]
    
    @patch('server.pipeline.forward.select_public_ip')
    def test_http_still_validates_ips(self, mock_select_ip):
        """Test that HTTP requests still validate IPs (no pinning but validation)"""
        # Mock IP validation failure for HTTP
        mock_select_ip.return_value = (False, "HEL_RESOLVED_PRIVATE", None)
        
        result = safe_forward("http://192.168.1.1/api", {"test": "data"})
        
        assert result["status_code"] == 403
        assert "IP validation failed" in result["error"]

class TestIPSelection:
    """Test IP selection logic"""
    
    @patch('socket.getaddrinfo')
    @patch('server.pipeline.net.resolve_public_ips')
    def test_select_first_public_ip(self, mock_resolve, mock_getaddrinfo):
        """Test selection of first public IP"""
        # Mock validation success
        mock_resolve.return_value = (True, "ok")
        
        # Mock multiple public IPs
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('1.1.1.1', 80))
        ]
        
        success, reason, selected_ip = select_public_ip("example.com")
        
        assert success
        assert reason == "ok"
        assert selected_ip == "8.8.8.8"  # Should select first IP
    
    @patch('server.pipeline.net.resolve_public_ips')
    def test_validation_failure_propagated(self, mock_resolve):
        """Test that validation failures are propagated"""
        # Mock validation failure
        mock_resolve.return_value = (False, "HEL_RESOLVED_PRIVATE")
        
        success, reason, selected_ip = select_public_ip("192.168.1.1")
        
        assert not success
        assert reason == "HEL_RESOLVED_PRIVATE"
        assert selected_ip is None

if __name__ == "__main__":
    pytest.main([__file__])
