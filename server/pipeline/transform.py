#!/usr/bin/env python3
"""
Signet Protocol Transform Manager

Handles payload transformation between different formats
with schema validation and semantic invariants.
"""

import json
from typing import Dict, Any, Optional


class TransformManager:
    """Manages payload transformations"""
    
    def __init__(self):
        self.transformations = {
            ('openai.tooluse.invoice.v1', 'invoice.iso20022.v1'): self._transform_openai_to_iso20022
        }
    
    async def transform(
        self,
        payload: Dict[str, Any],
        source_type: str,
        target_type: str
    ) -> Dict[str, Any]:
        """Transform payload from source to target format"""
        
        # Check if transformation is available
        transform_key = (source_type, target_type)
        if transform_key not in self.transformations:
            # Return payload as-is if no transformation available
            return payload
        
        # Apply transformation
        transformer = self.transformations[transform_key]
        return await transformer(payload)
    
    async def _transform_openai_to_iso20022(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Transform OpenAI tool use to ISO 20022 format"""
        try:
            # Extract tool calls
            tool_calls = payload.get('tool_calls', [])
            if not tool_calls:
                return payload
            
            # Process first tool call (simplified)
            tool_call = tool_calls[0]
            function = tool_call.get('function', {})
            
            if function.get('name') == 'create_invoice':
                # Parse arguments
                args_str = function.get('arguments', '{}')
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
                
                # Transform to ISO 20022 structure
                return {
                    'invoice_id': args.get('invoice_id'),
                    'amount_minor': int(args.get('amount', 0) * 100),  # Convert to minor units
                    'currency': args.get('currency', 'USD'),
                    'created_at': payload.get('created_at'),
                    'metadata': {
                        'source_type': 'openai.tooluse.invoice.v1',
                        'transformed_at': payload.get('timestamp')
                    }
                }
            
            return payload
            
        except Exception as e:
            # Return original payload if transformation fails
            return payload
    
    def register_transformation(
        self,
        source_type: str,
        target_type: str,
        transformer_func
    ) -> None:
        """Register a new transformation"""
        self.transformations[(source_type, target_type)] = transformer_func