#!/usr/bin/env python3
"""
Signet Protocol Receipt Management

Handles creation, validation, and storage of cryptographic receipts
for verified exchanges in the Trust Fabric.
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ..utils.crypto import SigningManager, compute_content_hash, generate_trace_id
from ..utils.jcs import canonicalize, compute_canonical_hash
from .storage import StorageBackend
from .forward import ForwardManager
from .transform import TransformManager


class Receipt:
    """Cryptographic receipt for verified exchanges"""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
    
    @property
    def receipt_id(self) -> str:
        return self.data.get('receipt_id')
    
    @property
    def trace_id(self) -> str:
        return self.data.get('trace_id')
    
    @property
    def timestamp(self) -> str:
        return self.data.get('ts')
    
    @property
    def content_hash(self) -> str:
        return self.data.get('cid')
    
    @property
    def receipt_hash(self) -> str:
        return self.data.get('receipt_hash')
    
    @property
    def signature(self) -> str:
        return self.data.get('signature')
    
    def to_dict(self) -> Dict[str, Any]:
        return self.data.copy()


class ReceiptManager:
    """Manages receipt creation and verification"""
    
    def __init__(self, storage: StorageBackend, signing_manager: Optional[SigningManager] = None):
        self.storage = storage
        self.signing_manager = signing_manager or SigningManager()
        self.transform_manager = TransformManager()
        self.forward_manager = ForwardManager()
    
    async def process_exchange(
        self,
        payload_type: str,
        target_type: str,
        payload: Dict[str, Any],
        forward_url: str,
        api_key: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a verified exchange and create receipt"""
        
        # Generate IDs
        trace_id = generate_trace_id()
        receipt_id = f"receipt-{uuid.uuid4().hex[:16]}"
        
        # Check idempotency
        if idempotency_key:
            existing = await self.storage.get_by_idempotency_key(idempotency_key, api_key)
            if existing:
                return existing
        
        # Transform payload
        transformed_payload = await self.transform_manager.transform(
            payload, payload_type, target_type
        )
        
        # Compute content hash
        content_hash = compute_content_hash(transformed_payload)
        
        # Create receipt data
        receipt_data = {
            'receipt_id': receipt_id,
            'trace_id': trace_id,
            'ts': datetime.now(timezone.utc).isoformat(),
            'payload_type': payload_type,
            'target_type': target_type,
            'cid': content_hash,
            'hop': 1,
            'api_key': api_key
        }
        
        # Compute receipt hash
        receipt_hash = compute_canonical_hash(receipt_data)
        receipt_data['receipt_hash'] = receipt_hash
        
        # Sign receipt
        signature = self.signing_manager.sign_data(receipt_data)
        receipt_data['signature'] = signature
        
        # Store receipt
        await self.storage.store_receipt(receipt_data, idempotency_key)
        
        # Forward to target URL
        forward_result = await self.forward_manager.forward(
            forward_url, transformed_payload, trace_id
        )
        
        # Create response
        response = {
            'trace_id': trace_id,
            'normalized': transformed_payload,
            'receipt': {
                'ts': receipt_data['ts'],
                'cid': content_hash,
                'receipt_hash': receipt_hash,
                'hop': 1
            },
            'forwarded': {
                'status_code': forward_result.get('status_code'),
                'host': forward_result.get('host')
            }
        }
        
        return response
    
    async def get_receipt(self, receipt_id: str, api_key: str) -> Optional[Receipt]:
        """Retrieve a receipt by ID"""
        data = await self.storage.get_receipt(receipt_id, api_key)
        if data:
            return Receipt(data)
        return None
    
    async def verify_receipt(self, receipt_data: Dict[str, Any]) -> bool:
        """Verify a receipt's signature and integrity"""
        try:
            # Extract signature
            signature = receipt_data.pop('signature', None)
            if not signature:
                return False
            
            # Verify signature
            return self.signing_manager.verify_signature(receipt_data, signature)
        except Exception:
            return False
    
    async def export_audit_trail(self, tenant_id: str) -> Dict[str, Any]:
        """Export signed audit trail bundle for tenant"""
        receipts = await self.storage.get_receipts_for_tenant(tenant_id)
        
        # Create audit bundle
        bundle = {
            'tenant_id': tenant_id,
            'export_ts': datetime.now(timezone.utc).isoformat(),
            'receipt_count': len(receipts),
            'receipts': receipts
        }
        
        # Sign the bundle
        bundle_signature = self.signing_manager.sign_data(bundle)
        bundle['bundle_signature'] = bundle_signature
        
        return bundle
    
    async def list_receipts(
        self,
        api_key: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Receipt]:
        """List receipts for an API key"""
        data_list = await self.storage.list_receipts(api_key, limit, offset)
        return [Receipt(data) for data in data_list]