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
from pathlib import Path
from typing import Dict, Any, List, Optional
import jsonschema
from urllib.parse import urlparse

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
        
        # Policy command
        policy_parser = subparsers.add_parser('policy', help='Policy utilities')
        policy_subparsers = policy_parser.add_subparsers(dest='policy_action')
        
        policy_lint_parser = policy_subparsers.add_parser('lint', help='Validate policy configuration')
        policy_lint_parser.add_argument('--allowlist', help='Comma-separated allowlist domains')
        policy_lint_parser.add_argument('--file', help='Path to allowlist file (one domain per line)')
        policy_lint_parser.add_argument('--check-dns', action='store_true', help='Perform DNS resolution checks')
        policy_lint_parser.add_argument('--simulate', help='Simulate forwarding to URL')
        
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
