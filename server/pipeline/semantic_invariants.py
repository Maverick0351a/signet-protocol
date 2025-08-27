"""
Signet Protocol - Semantic Invariants System
Prevents LLM fallback from corrupting critical business logic.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

@dataclass
class InvariantViolation:
    """Represents a semantic invariant violation."""
    rule_name: str
    field: str
    expected: Any
    actual: Any
    message: str

class SemanticInvariants:
    """
    Validates that LLM-repaired JSON maintains semantic correctness.
    
    Prevents dangerous transformations like:
    - Amount changes (100.00 -> 10.00)
    - Currency changes (USD -> EUR)
    - ID modifications (INV-123 -> INV-124)
    - Critical field removal
    """
    
    def __init__(self):
        self.rules = {
            'amount_precision': self._check_amount_precision,
            'currency_unchanged': self._check_currency_unchanged,
            'ids_unchanged': self._check_ids_unchanged,
            'required_fields': self._check_required_fields,
            'numeric_ranges': self._check_numeric_ranges,
            'date_formats': self._check_date_formats,
            'enum_values': self._check_enum_values
        }
    
    def validate(
        self,
        original_data: Dict[str, Any],
        repaired_data: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[InvariantViolation]]:
        """
        Validate that repaired data maintains semantic invariants.
        
        Args:
            original_data: Original (possibly malformed) data
            repaired_data: LLM-repaired data
            schema: JSON schema for additional validation
            
        Returns:
            (is_valid, list_of_violations)
        """
        violations = []
        
        # Extract original values for comparison
        original_values = self._extract_values(original_data)
        repaired_values = self._extract_values(repaired_data)
        
        # Run all invariant checks
        for rule_name, rule_func in self.rules.items():
            try:
                rule_violations = rule_func(original_values, repaired_values, schema)
                violations.extend(rule_violations)
            except Exception as e:
                # Log rule execution error but don't fail validation
                print(f"Warning: Invariant rule '{rule_name}' failed: {str(e)}")
        
        return len(violations) == 0, violations
    
    def _extract_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key-value pairs from nested data structure."""
        values = {}
        
        def extract_recursive(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    values[full_key] = value
                    if isinstance(value, (dict, list)):
                        extract_recursive(value, full_key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    full_key = f"{prefix}[{i}]"
                    values[full_key] = item
                    if isinstance(item, (dict, list)):
                        extract_recursive(item, full_key)
        
        extract_recursive(data)
        return values
    
    def _check_amount_precision(
        self,
        original: Dict[str, Any],
        repaired: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> List[InvariantViolation]:
        """Ensure monetary amounts maintain precision and scale."""
        violations = []
        
        # Find amount fields
        amount_fields = [k for k in original.keys() if 'amount' in k.lower()]
        
        for field in amount_fields:
            if field in original and field in repaired:
                orig_val = original[field]
                repair_val = repaired[field]
                
                try:
                    # Convert to Decimal for precise comparison
                    orig_decimal = self._to_decimal(orig_val)
                    repair_decimal = self._to_decimal(repair_val)
                    
                    if orig_decimal is not None and repair_decimal is not None:
                        # Check if amounts are significantly different (>1% change)
                        if abs(orig_decimal - repair_decimal) > abs(orig_decimal * Decimal('0.01')):
                            violations.append(InvariantViolation(
                                rule_name='amount_precision',
                                field=field,
                                expected=str(orig_decimal),
                                actual=str(repair_decimal),
                                message=f"Amount changed significantly: {orig_decimal} -> {repair_decimal}"
                            ))
                        
                        # Check for precision loss
                        orig_places = abs(orig_decimal.as_tuple().exponent)
                        repair_places = abs(repair_decimal.as_tuple().exponent)
                        
                        if repair_places < orig_places:
                            violations.append(InvariantViolation(
                                rule_name='amount_precision',
                                field=field,
                                expected=f"{orig_places} decimal places",
                                actual=f"{repair_places} decimal places",
                                message=f"Precision loss in amount field: {field}"
                            ))
                
                except Exception:
                    # If conversion fails, flag as potential issue
                    violations.append(InvariantViolation(
                        rule_name='amount_precision',
                        field=field,
                        expected=str(orig_val),
                        actual=str(repair_val),
                        message=f"Amount format changed: {orig_val} -> {repair_val}"
                    ))
        
        return violations
    
    def _check_currency_unchanged(
        self,
        original: Dict[str, Any],
        repaired: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> List[InvariantViolation]:
        """Ensure currency codes remain unchanged."""
        violations = []
        
        currency_fields = [k for k in original.keys() if 'currency' in k.lower() or 'curr' in k.lower()]
        
        for field in currency_fields:
            if field in original and field in repaired:
                orig_val = str(original[field]).upper()
                repair_val = str(repaired[field]).upper()
                
                if orig_val != repair_val:
                    violations.append(InvariantViolation(
                        rule_name='currency_unchanged',
                        field=field,
                        expected=orig_val,
                        actual=repair_val,
                        message=f"Currency code changed: {orig_val} -> {repair_val}"
                    ))
        
        return violations
    
    def _check_ids_unchanged(
        self,
        original: Dict[str, Any],
        repaired: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> List[InvariantViolation]:
        """Ensure ID fields remain unchanged."""
        violations = []
        
        # Find ID fields
        id_patterns = ['id', 'uuid', 'reference', 'number', 'code']
        id_fields = []
        
        for key in original.keys():
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in id_patterns):
                id_fields.append(key)
        
        for field in id_fields:
            if field in original and field in repaired:
                orig_val = str(original[field]).strip()
                repair_val = str(repaired[field]).strip()
                
                if orig_val != repair_val:
                    violations.append(InvariantViolation(
                        rule_name='ids_unchanged',
                        field=field,
                        expected=orig_val,
                        actual=repair_val,
                        message=f"ID field changed: {orig_val} -> {repair_val}"
                    ))
        
        return violations
    
    def _check_required_fields(
        self,
        original: Dict[str, Any],
        repaired: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> List[InvariantViolation]:
        """Ensure critical fields are not removed."""
        violations = []
        
        # Define critical fields that should never be removed
        critical_fields = [
            'amount', 'currency', 'invoice_id', 'customer_name',
            'id', 'uuid', 'reference', 'total', 'subtotal'
        ]
        
        # Check for removed critical fields
        for field in original.keys():
            field_lower = field.lower()
            if any(critical in field_lower for critical in critical_fields):
                if field not in repaired:
                    violations.append(InvariantViolation(
                        rule_name='required_fields',
                        field=field,
                        expected='present',
                        actual='missing',
                        message=f"Critical field removed: {field}"
                    ))
        
        return violations
    
    def _check_numeric_ranges(
        self,
        original: Dict[str, Any],
        repaired: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> List[InvariantViolation]:
        """Ensure numeric values stay within reasonable ranges."""
        violations = []
        
        for field in original.keys():
            if field in repaired:
                orig_val = original[field]
                repair_val = repaired[field]
                
                # Check numeric fields
                if isinstance(orig_val, (int, float)) and isinstance(repair_val, (int, float)):
                    # Ensure values don't change by orders of magnitude
                    if orig_val != 0 and repair_val != 0:
                        ratio = abs(repair_val / orig_val)
                        if ratio > 10 or ratio < 0.1:
                            violations.append(InvariantViolation(
                                rule_name='numeric_ranges',
                                field=field,
                                expected=f"~{orig_val}",
                                actual=str(repair_val),
                                message=f"Numeric value changed by order of magnitude: {orig_val} -> {repair_val}"
                            ))
        
        return violations
    
    def _check_date_formats(
        self,
        original: Dict[str, Any],
        repaired: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> List[InvariantViolation]:
        """Ensure date fields maintain valid formats."""
        violations = []
        
        date_fields = [k for k in original.keys() if 'date' in k.lower() or 'time' in k.lower()]
        
        for field in date_fields:
            if field in original and field in repaired:
                orig_val = str(original[field])
                repair_val = str(repaired[field])
                
                # Check if date format is preserved
                if self._is_date_like(orig_val) and not self._is_date_like(repair_val):
                    violations.append(InvariantViolation(
                        rule_name='date_formats',
                        field=field,
                        expected='valid date format',
                        actual=repair_val,
                        message=f"Date format corrupted: {orig_val} -> {repair_val}"
                    ))
        
        return violations
    
    def _check_enum_values(
        self,
        original: Dict[str, Any],
        repaired: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> List[InvariantViolation]:
        """Ensure enum values remain valid."""
        violations = []
        
        # Define known enum fields and their valid values
        enum_fields = {
            'status': ['pending', 'paid', 'cancelled', 'draft'],
            'type': ['invoice', 'credit_note', 'receipt'],
            'payment_method': ['cash', 'card', 'bank_transfer', 'check']
        }
        
        for field, valid_values in enum_fields.items():
            if field in original and field in repaired:
                orig_val = str(original[field]).lower()
                repair_val = str(repaired[field]).lower()
                
                # If original was valid, ensure repaired is also valid
                if orig_val in valid_values and repair_val not in valid_values:
                    violations.append(InvariantViolation(
                        rule_name='enum_values',
                        field=field,
                        expected=f"one of {valid_values}",
                        actual=repair_val,
                        message=f"Invalid enum value: {repair_val}"
                    ))
        
        return violations
    
    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        """Convert value to Decimal for precise arithmetic."""
        try:
            if isinstance(value, str):
                # Remove currency symbols and whitespace
                cleaned = re.sub(r'[^\d.-]', '', value)
                return Decimal(cleaned) if cleaned else None
            elif isinstance(value, (int, float)):
                return Decimal(str(value))
            else:
                return None
        except (InvalidOperation, ValueError):
            return None
    
    def _is_date_like(self, value: str) -> bool:
        """Check if string looks like a date."""
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO datetime
        ]
        
        return any(re.search(pattern, value) for pattern in date_patterns)


# Integration with fallback system
def validate_fallback_result(
    original_json: str,
    repaired_json: str,
    schema: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[str], List[InvariantViolation]]:
    """
    Validate that fallback repair maintains semantic invariants.
    
    Args:
        original_json: Original (possibly malformed) JSON string
        repaired_json: LLM-repaired JSON string
        schema: JSON schema for validation
        
    Returns:
        (is_valid, error_messages, violations)
    """
    try:
        # Parse JSON strings
        try:
            original_data = json.loads(original_json)
        except json.JSONDecodeError:
            # Try to extract partial data from malformed JSON
            original_data = _extract_partial_json(original_json)
        
        try:
            repaired_data = json.loads(repaired_json)
        except json.JSONDecodeError:
            return False, ["Repaired JSON is still malformed"], []
        
        # Run semantic validation
        invariants = SemanticInvariants()
        is_valid, violations = invariants.validate(original_data, repaired_data, schema)
        
        error_messages = [v.message for v in violations]
        
        return is_valid, error_messages, violations
        
    except Exception as e:
        return False, [f"Validation error: {str(e)}"], []


def _extract_partial_json(malformed_json: str) -> Dict[str, Any]:
    """Extract partial data from malformed JSON for comparison."""
    data = {}
    
    # Try to extract key-value pairs using regex
    patterns = [
        r'"([^"]+)"\s*:\s*"([^"]*)"',  # String values
        r'"([^"]+)"\s*:\s*(\d+\.?\d*)',  # Numeric values
        r'"([^"]+)"\s*:\s*(true|false|null)',  # Boolean/null values
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, malformed_json)
        for key, value in matches:
            try:
                # Try to parse numeric values
                if '.' in value:
                    data[key] = float(value)
                elif value.isdigit():
                    data[key] = int(value)
                elif value in ['true', 'false', 'null']:
                    data[key] = {'true': True, 'false': False, 'null': None}[value]
                else:
                    data[key] = value
            except ValueError:
                data[key] = value
    
    return data


# Example usage
if __name__ == "__main__":
    # Test semantic invariants
    original = '{"invoice_id": "INV-123", "amount": 1000.00, "currency": "USD"}'
    repaired = '{"invoice_id": "INV-123", "amount": 100.00, "currency": "USD"}'  # Amount changed!
    
    is_valid, errors, violations = validate_fallback_result(original, repaired)
    
    print(f"Valid: {is_valid}")
    if not is_valid:
        print("Violations:")
        for violation in violations:
            print(f"  - {violation.message}")
