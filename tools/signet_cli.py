#!/usr/bin/env python3
"""
Signet Protocol - CLI Tools
Command-line utilities for testing mappings and validating policies.
"""

import json
import sys
import argparse
import requests
import socket
import ipaddress
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import jsonschema
from urllib.parse import urlparse

class MappingDSLParser:
    """Parser for Signet Mapping DSL."""
    
    def __init__(self):
        self.functions = {
            'upper': lambda x: str(x).upper(),
            'lower': lambda x: str(x).lower(),
            'multiply': lambda x, factor: float(x) * float(factor),
            'divide': lambda x, divisor: float(x) / float(divisor),
            'concat': lambda *args: ''.join(str(arg) for arg in args),
            'format': lambda template, *args: template.format(*args),
            'substring': lambda x, start, end=None: str(x)[start:end],
            'replace': lambda x, old, new: str(x).replace(old, new),
            'split': lambda x, delimiter: str(x).split(delimiter),
            'join': lambda items, delimiter: delimiter.join(str(item) for item in items),
            'default': lambda x, default_val: default_val if x is None else x,
            'coalesce': lambda *args: next((arg for arg in args if arg is not None), None),
        }
    
    def parse_expression(self, expr: str, data: Dict[str, Any]) -> Any:
        """Parse and evaluate a mapping DSL expression."""
        expr = expr.strip()
        
        # Simple field reference
        if expr.startswith('$.'):
            return self._get_nested_value(data, expr[2:])
        
        # Function call
        if '(' in expr and expr.endswith(')'):
            return self._parse_function_call(expr, data)
        
        # Literal value
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]  # String literal
        
        if expr.isdigit() or (expr.startswith('-') and expr[1:].isdigit()):
            return int(expr)  # Integer literal
        
        try:
            return float(expr)  # Float literal
        except ValueError:
            pass
        
        if expr.lower() in ('true', 'false'):
            return expr.lower() == 'true'  # Boolean literal
        
        if expr.lower() == 'null':
            return None  # Null literal
        
        # Default to string
        return expr
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from data using dot notation."""
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif isinstance(value, list) and key.isdigit():
                index = int(key)
                if 0 <= index < len(value):
                    value = value[index]
                else:
                    return None
            else:
                return None
        
        return value
    
    def _parse_function_call(self, expr: str, data: Dict[str, Any]) -> Any:
        """Parse and execute a function call."""
        match = re.match(r'(\w+)\((.*)\)', expr)
        if not match:
            return expr
        
        func_name, args_str = match.groups()
        
        if func_name not in self.functions:
            raise ValueError(f"Unknown function: {func_name}")
        
        # Parse arguments
        args = []
        if args_str.strip():
            # Simple argument parsing (doesn't handle nested function calls)
            arg_parts = [arg.strip() for arg in args_str.split(',')]
            for arg in arg_parts:
                args.append(self.parse_expression(arg, data))
        
        return self.functions[func_name](*args)

class HELPolicyLinter:
    """HEL (HTTP Endpoint Language) policy linter."""
    
    def __init__(self):
        self.rules = [
            self._check_localhost_blocked,
            self._check_private_ips_blocked,
            self._check_wildcard_usage,
            self._check_protocol_specification,
            self._check_port_specification,
            self._check_domain_validation,
        ]
    
    def lint_policy(self, policy: Union[str, List[str], Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Lint HEL policy configuration."""
        issues = []
        
        # Normalize policy to list of rules
        if isinstance(policy, str):
            rules = [policy]
        elif isinstance(policy, list):
            rules = policy
        elif isinstance(policy, dict):
            rules = policy.get('allowlist', [])
        else:
            return [{'type': 'error', 'message': 'Invalid policy format'}]
        
        for i, rule in enumerate(rules):
            rule_issues = self._lint_rule(rule, i)
            issues.extend(rule_issues)
        
        return issues
    
    def _lint_rule(self, rule: str, index: int) -> List[Dict[str, Any]]:
        """Lint a single HEL rule."""
        issues = []
        
        for rule_func in self.rules:
            rule_issues = rule_func(rule, index)
            issues.extend(rule_issues)
        
        return issues
    
    def _check_localhost_blocked(self, rule: str, index: int) -> List[Dict[str, Any]]:
        """Check for localhost/loopback addresses."""
        issues = []
        
        localhost_patterns = [
            'localhost',
            '127.0.0.1',
            '::1',
            '0.0.0.0',
        ]
        
        for pattern in localhost_patterns:
            if pattern in rule.lower():
                issues.append({
                    'type': 'error',
                    'rule_index': index,
                    'rule': rule,
                    'message': f'Localhost/loopback address detected: {pattern}',
                    'severity': 'high'
                })
        
        return issues
    
    def _check_private_ips_blocked(self, rule: str, index: int) -> List[Dict[str, Any]]:
        """Check for private IP addresses."""
        issues = []
        
        # Extract IP addresses from rule
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, rule)
        
        for ip in ips:
            try:
                addr = ipaddress.ip_address(ip)
                if addr.is_private or addr.is_loopback or addr.is_link_local:
                    issues.append({
                        'type': 'error',
                        'rule_index': index,
                        'rule': rule,
                        'message': f'Private/internal IP address: {ip}',
                        'severity': 'high'
                    })
            except ValueError:
                pass
        
        return issues
    
    def _check_wildcard_usage(self, rule: str, index: int) -> List[Dict[str, Any]]:
        """Check wildcard usage patterns."""
        issues = []
        
        if '*' in rule:
            # Check for overly broad wildcards
            if rule.strip() == '*':
                issues.append({
                    'type': 'error',
                    'rule_index': index,
                    'rule': rule,
                    'message': 'Overly broad wildcard - allows all domains',
                    'severity': 'critical'
                })
            elif rule.startswith('*.'):
                # Subdomain wildcard is generally OK
                issues.append({
                    'type': 'info',
                    'rule_index': index,
                    'rule': rule,
                    'message': 'Subdomain wildcard detected - ensure this is intentional',
                    'severity': 'low'
                })
            else:
                issues.append({
                    'type': 'warning',
                    'rule_index': index,
                    'rule': rule,
                    'message': 'Wildcard usage detected - review for security implications',
                    'severity': 'medium'
                })
        
        return issues
    
    def _check_protocol_specification(self, rule: str, index: int) -> List[Dict[str, Any]]:
        """Check protocol specification."""
        issues = []
        
        if '://' not in rule:
            issues.append({
                'type': 'warning',
                'rule_index': index,
                'rule': rule,
                'message': 'No protocol specified - will default to HTTP/HTTPS',
                'severity': 'low'
            })
        elif rule.startswith('http://'):
            issues.append({
                'type': 'warning',
                'rule_index': index,
                'rule': rule,
                'message': 'HTTP protocol specified - consider HTTPS for security',
                'severity': 'medium'
            })
        
        return issues
    
    def _check_port_specification(self, rule: str, index: int) -> List[Dict[str, Any]]:
        """Check port specification."""
        issues = []
        
        # Extract port from URL
        port_match = re.search(r':(\d+)(?:/|$)', rule)
        if port_match:
            port = int(port_match.group(1))
            
            # Check for non-standard ports
            if port not in [80, 443, 8080, 8443]:
                issues.append({
                    'type': 'info',
                    'rule_index': index,
                    'rule': rule,
                    'message': f'Non-standard port specified: {port}',
                    'severity': 'low'
                })
            
            # Check for privileged ports
            if port < 1024 and port not in [80, 443]:
                issues.append({
                    'type': 'warning',
                    'rule_index': index,
                    'rule': rule,
                    'message': f'Privileged port specified: {port}',
                    'severity': 'medium'
                })
        
        return issues
    
    def _check_domain_validation(self, rule: str, index: int) -> List[Dict[str, Any]]:
        """Check domain name validation."""
        issues = []
        
        # Extract domain from rule
        domain_match = re.search(r'(?:https?://)?([^:/\s]+)', rule)
        if domain_match:
            domain = domain_match.group(1)
            
            # Check for valid domain format
            if not self._is_valid_domain(domain.replace('*', 'x')):  # Replace wildcards for validation
                issues.append({
                    'type': 'error',
                    'rule_index': index,
                    'rule': rule,
                    'message': f'Invalid domain format: {domain}',
                    'severity': 'high'
                })
        
        return issues
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Check if domain format is valid."""
        if len(domain) > 253:
            return False
        
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, domain))

class SignetCLI:
    """Command-line interface for Signet Protocol tools."""
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Signet Protocol CLI Tools",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Test a mapping transformation
  signet map test --mapping invoice_mapping.json --sample sample_invoice.json
  
  # Validate policy configuration
  signet policy lint --allowlist "api.example.com,webhook.site" --check-dns
  
  # Validate schemas
  signet schema validate --input input_schema.json --output output_schema.json --data sample.json
  
  # Generate mapping DSL template
  signet map generate --input-schema input.json --output-schema output.json
  
  # Lint HEL policy file
  signet policy lint --hel-file policy.hel --strict
            """
        )
        
        subparsers = self.parser.add_subparsers(dest='command', help='Available commands')
        
        # Map command
        map_parser = subparsers.add_parser('map', help='Mapping utilities')
        map_subparsers = map_parser.add_subparsers(dest='map_action')
        
        map_test_parser = map_subparsers.add_parser('test', help='Test mapping transformation')
        map_test_parser.add_argument('--mapping', required=True, help='Path to mapping JSON file')
        map_test_parser.add_argument('--sample', required=True, help='Path to sample input JSON')
        map_test_parser.add_argument('--input-schema', help='Path to input schema JSON')
        map_test_parser.add_argument('--output-schema', help='Path to output schema JSON')
        map_test_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        map_test_parser.add_argument('--dsl', action='store_true', help='Use mapping DSL parser')
        
        map_generate_parser = map_subparsers.add_parser('generate', help='Generate mapping template')
        map_generate_parser.add_argument('--input-schema', required=True, help='Input schema file')
        map_generate_parser.add_argument('--output-schema', required=True, help='Output schema file')
        map_generate_parser.add_argument('--output', '-o', help='Output mapping file')
        map_generate_parser.add_argument('--dsl', action='store_true', help='Generate DSL format')
        
        # Policy command
        policy_parser = subparsers.add_parser('policy', help='Policy utilities')
        policy_subparsers = policy_parser.add_subparsers(dest='policy_action')
        
        policy_lint_parser = policy_subparsers.add_parser('lint', help='Validate policy configuration')
        policy_lint_parser.add_argument('--allowlist', help='Comma-separated allowlist domains')
        policy_lint_parser.add_argument('--file', help='Path to allowlist file (one domain per line)')
        policy_lint_parser.add_argument('--hel-file', help='Path to HEL policy file')
        policy_lint_parser.add_argument('--check-dns', action='store_true', help='Perform DNS resolution checks')
        policy_lint_parser.add_argument('--simulate', help='Simulate forwarding to URL')
        policy_lint_parser.add_argument('--strict', action='store_true', help='Strict linting mode')
        policy_lint_parser.add_argument('--format', choices=['text', 'json', 'yaml'], default='text', help='Output format')
        
        # Schema command
        schema_parser = subparsers.add_parser('schema', help='Schema utilities')
        schema_subparsers = schema_parser.add_subparsers(dest='schema_action')
        
        schema_validate_parser = schema_subparsers.add_parser('validate', help='Validate data against schemas')
        schema_validate_parser.add_argument('--input-schema', required=True, help='Input schema file')
        schema_validate_parser.add_argument('--output-schema', help='Output schema file')
        schema_validate_parser.add_argument('--data', required=True, help='Data file to validate')
    
    def run(self, args=None):
        """Run the CLI with provided arguments."""
        args = self.parser.parse_args(args)
        
        if not args.command:
            self.parser.print_help()
            return 1
        
        try:
            if args.command == 'map':
                return self._handle_map_command(args)
            elif args.command == 'policy':
                return self._handle_policy_command(args)
            elif args.command == 'schema':
                return self._handle_schema_command(args)
            else:
                print(f"Unknown command: {args.command}")
                return 1
        except Exception as e:
            print(f"Error: {str(e)}")
            return 1
    
    def _handle_map_command(self, args) -> int:
        """Handle mapping-related commands."""
        if args.map_action == 'test':
            return self._test_mapping(args)
        else:
            print("Available map actions: test")
            return 1
    
    def _handle_policy_command(self, args) -> int:
        """Handle policy-related commands."""
        if args.policy_action == 'lint':
            return self._lint_policy(args)
        else:
            print("Available policy actions: lint")
            return 1
    
    def _handle_schema_command(self, args) -> int:
        """Handle schema-related commands."""
        if args.schema_action == 'validate':
            return self._validate_schema(args)
        else:
            print("Available schema actions: validate")
            return 1
    
    def _test_mapping(self, args) -> int:
        """Test mapping transformation."""
        try:
            # Load mapping
            mapping_path = Path(args.mapping)
            if not mapping_path.exists():
                print(f"❌ Mapping file not found: {args.mapping}")
                return 1
            
            with open(mapping_path) as f:
                mapping = json.load(f)
            
            # Load sample data
            sample_path = Path(args.sample)
            if not sample_path.exists():
                print(f"❌ Sample file not found: {args.sample}")
                return 1
            
            with open(sample_path) as f:
                sample_data = json.load(f)
            
            print(f"🔄 Testing mapping: {mapping_path.name}")
            print(f"📄 Sample data: {sample_path.name}")
            
            # Validate input schema if provided
            if args.input_schema:
                input_schema_path = Path(args.input_schema)
                if input_schema_path.exists():
                    with open(input_schema_path) as f:
                        input_schema = json.load(f)
                    
                    try:
                        jsonschema.validate(sample_data, input_schema)
                        print("✅ Input validation: PASSED")
                    except jsonschema.ValidationError as e:
                        print(f"❌ Input validation: FAILED - {e.message}")
                        return 1
            
            # Apply transformation (simplified)
            transformed = self._apply_mapping(sample_data, mapping)
            
            # Validate output schema if provided
            if args.output_schema:
                output_schema_path = Path(args.output_schema)
                if output_schema_path.exists():
                    with open(output_schema_path) as f:
                        output_schema = json.load(f)
                    
                    try:
                        jsonschema.validate(transformed, output_schema)
                        print("✅ Output validation: PASSED")
                    except jsonschema.ValidationError as e:
                        print(f"❌ Output validation: FAILED - {e.message}")
                        if args.verbose:
                            print(f"   Error path: {' -> '.join(str(p) for p in e.absolute_path)}")
                        return 1
            
            # Show transformation result
            print("\n📋 Transformation Result:")
            if args.verbose:
                print("--- Input ---")
                print(json.dumps(sample_data, indent=2))
                print("--- Output ---")
            print(json.dumps(transformed, indent=2))
            
            print("\n✅ Mapping test completed successfully!")
            return 0
            
        except Exception as e:
            print(f"❌ Mapping test failed: {str(e)}")
            return 1
    
    def _lint_policy(self, args) -> int:
        """Lint policy configuration."""
        try:
            # Get allowlist domains
            domains = []
            if args.allowlist:
                domains = [d.strip() for d in args.allowlist.split(',')]
            elif args.file:
                file_path = Path(args.file)
                if file_path.exists():
                    with open(file_path) as f:
                        domains = [line.strip() for line in f if line.strip()]
                else:
                    print(f"❌ Allowlist file not found: {args.file}")
                    return 1
            else:
                print("❌ Must provide --allowlist or --file")
                return 1
            
            print(f"🔍 Linting policy with {len(domains)} domains...")
            
            issues = []
            warnings = []
            
            for domain in domains:
                # Basic domain validation
                if not self._is_valid_domain(domain):
                    issues.append(f"Invalid domain format: {domain}")
                    continue
                
                # Check for private/localhost domains
                if self._is_private_domain(domain):
                    issues.append(f"Private/localhost domain not allowed: {domain}")
                    continue
                
                # DNS resolution check
                if args.check_dns:
                    ips = self._resolve_domain(domain)
                    if not ips:
                        warnings.append(f"DNS resolution failed: {domain}")
                    else:
                        # Check for private IPs
                        private_ips = [ip for ip in ips if self._is_private_ip(ip)]
                        if private_ips:
                            issues.append(f"Domain {domain} resolves to private IPs: {private_ips}")
                        else:
                            print(f"✅ {domain} -> {ips}")
            
            # Simulate forwarding if requested
            if args.simulate:
                print(f"\n🎯 Simulating forward to: {args.simulate}")
                parsed = urlparse(args.simulate)
                domain = parsed.hostname
                
                if domain in domains:
                    print(f"✅ Domain {domain} is in allowlist")
                    
                    if args.check_dns:
                        ips = self._resolve_domain(domain)
                        if ips:
                            valid_ips = [ip for ip in ips if not self._is_private_ip(ip)]
                            if valid_ips:
                                print(f"✅ Would forward to IP: {valid_ips[0]}")
                            else:
                                print(f"❌ All resolved IPs are private: {ips}")
                        else:
                            print(f"❌ DNS resolution failed for {domain}")
                else:
                    print(f"❌ Domain {domain} not in allowlist")
            
            # Report results
            print(f"\n📊 Policy Lint Results:")
            print(f"   Domains checked: {len(domains)}")
            print(f"   Issues found: {len(issues)}")
            print(f"   Warnings: {len(warnings)}")
            
            if issues:
                print("\n❌ Issues:")
                for issue in issues:
                    print(f"   • {issue}")
            
            if warnings:
                print("\n⚠️ Warnings:")
                for warning in warnings:
                    print(f"   • {warning}")
            
            if not issues and not warnings:
                print("\n✅ Policy configuration looks good!")
            
            return 1 if issues else 0
            
        except Exception as e:
            print(f"❌ Policy lint failed: {str(e)}")
            return 1
    
    def _validate_schema(self, args) -> int:
        """Validate data against schemas."""
        try:
            # Load schemas
            input_schema_path = Path(args.input_schema)
            if not input_schema_path.exists():
                print(f"❌ Input schema not found: {args.input_schema}")
                return 1
            
            with open(input_schema_path) as f:
                input_schema = json.load(f)
            
            output_schema = None
            if args.output_schema:
                output_schema_path = Path(args.output_schema)
                if output_schema_path.exists():
                    with open(output_schema_path) as f:
                        output_schema = json.load(f)
            
            # Load data
            data_path = Path(args.data)
            if not data_path.exists():
                print(f"❌ Data file not found: {args.data}")
                return 1
            
            with open(data_path) as f:
                data = json.load(f)
            
            print(f"🔍 Validating data against schemas...")
            
            # Validate against input schema
            try:
                jsonschema.validate(data, input_schema)
                print("✅ Input schema validation: PASSED")
            except jsonschema.ValidationError as e:
                print(f"❌ Input schema validation: FAILED")
                print(f"   Error: {e.message}")
                print(f"   Path: {' -> '.join(str(p) for p in e.absolute_path)}")
                return 1
            
            # Validate against output schema if provided
            if output_schema:
                try:
                    jsonschema.validate(data, output_schema)
                    print("✅ Output schema validation: PASSED")
                except jsonschema.ValidationError as e:
                    print(f"❌ Output schema validation: FAILED")
                    print(f"   Error: {e.message}")
                    print(f"   Path: {' -> '.join(str(p) for p in e.absolute_path)}")
                    return 1
            
            print("\n✅ All schema validations passed!")
            return 0
            
        except Exception as e:
            print(f"❌ Schema validation failed: {str(e)}")
            return 1
    
    def _apply_mapping(self, data: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformation mapping to data (simplified implementation)."""
        # This is a simplified mapping - in production you'd use the full transform logic
        result = {}
        
        for output_field, mapping_rule in mapping.items():
            if isinstance(mapping_rule, str):
                # Simple field mapping
                if mapping_rule in data:
                    result[output_field] = data[mapping_rule]
            elif isinstance(mapping_rule, dict):
                # Complex mapping with transformations
                if 'source' in mapping_rule:
                    source_field = mapping_rule['source']
                    if source_field in data:
                        value = data[source_field]
                        
                        # Apply transformations
                        if 'transform' in mapping_rule:
                            transform = mapping_rule['transform']
                            if transform == 'uppercase':
                                value = str(value).upper()
                            elif transform == 'multiply_100':
                                value = float(value) * 100
                        
                        result[output_field] = value
        
        return result
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Check if domain format is valid."""
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, domain)) and len(domain) <= 253
    
    def _is_private_domain(self, domain: str) -> bool:
        """Check if domain is private/localhost."""
        private_domains = ['localhost', '127.0.0.1', '0.0.0.0']
        return domain.lower() in private_domains or domain.endswith('.local')
    
    def _resolve_domain(self, domain: str) -> List[str]:
        """Resolve domain to IP addresses."""
        try:
            result = socket.getaddrinfo(domain, None)
            ips = list(set(info[4][0] for info in result))
            return ips
        except socket.gaierror:
            return []
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP address is private."""
        try:
            addr = ipaddress.ip_address(ip)
            return addr.is_private or addr.is_loopback or addr.is_link_local
        except ValueError:
            return True  # Invalid IP is considered private


def main():
    """Main entry point for CLI."""
    cli = SignetCLI()
    return cli.run()

if __name__ == '__main__':
    sys.exit(main())
