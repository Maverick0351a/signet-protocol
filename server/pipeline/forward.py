#!/usr/bin/env python3
"""
Signet Protocol Forward Manager

Handles secure forwarding of transformed payloads
to target URLs with comprehensive validation.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from urllib.parse import urlparse

import httpx


class ForwardManager:
    """Manages secure forwarding of payloads"""
    
    def __init__(self, timeout: int = 30, max_response_size: int = 50_000_000):
        self.timeout = timeout
        self.max_response_size = max_response_size
    
    async def forward(
        self,
        url: str,
        payload: Dict[str, Any],
        trace_id: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Forward payload to target URL"""
        try:
            # Parse URL for host extraction
            parsed = urlparse(url)
            host = parsed.netloc
            
            # Prepare headers
            forward_headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Signet-Protocol/1.0',
                'X-Signet-Trace-ID': trace_id
            }
            
            if headers:
                forward_headers.update(headers)
            
            # Make request with timeout and size limits
            async with httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=forward_headers
                )
                
                # Check response size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.max_response_size:
                    return {
                        'status_code': 413,
                        'host': host,
                        'error': 'Response too large'
                    }
                
                return {
                    'status_code': response.status_code,
                    'host': host,
                    'response_headers': dict(response.headers),
                    'response_size': len(response.content) if response.content else 0
                }
                
        except httpx.TimeoutException:
            return {
                'status_code': 408,
                'host': host,
                'error': 'Request timeout'
            }
        except httpx.RequestError as e:
            return {
                'status_code': 502,
                'host': host,
                'error': f'Request failed: {str(e)}'
            }
        except Exception as e:
            return {
                'status_code': 500,
                'host': host,
                'error': f'Forward error: {str(e)}'
            }