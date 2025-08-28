#!/usr/bin/env python3
"""
Signet Protocol - Enhanced CLI with Receipt Verification
Command-line tool for verifying receipts, chains, and export bundles.
"""

import json
import sys
import argparse
import requests
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import glob

# Add SDK to path
sys.path.append(str(Path(__file__).parent.parent / 'sdk' / 'python'))
from signet_verify import verify_receipt, verify_chain, verify_export_bundle

class SignetVerifyCLI:
    """Enhanced CLI for Signet Protocol verification."""
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Signet Protocol Verification CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Verify a single receipt
  signet-verify receipt receipt.json
  
  # Verify a receipt chain
  signet-verify chain chain.json
  
  # Verify export bundle with JWKS
  signet-verify export bundle.json --jwks https://server/.well-known/jwks.json
  
  # Verify all test vectors
  signet-verify test-vectors test-vectors/ --jwks https://server/.well-known/jwks.json
  
  # CI mode (exit code 0 = success, 1 = failure)
  signet-verify test-vectors test-vectors/ --ci
            """
        )
        
        subparsers = self.parser.add_subparsers(dest='command', help='Available commands')
        
        # Receipt verification
        receipt_parser = subparsers.add_parser('receipt', help='Verify a single receipt')
        receipt_parser.add_argument('file', help='Path to receipt JSON file')
        receipt_parser.add_argument('--previous', help='Path to previous receipt JSON file')
        receipt_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        # Chain verification
        chain_parser = subparsers.add_parser('chain', help='Verify a receipt chain')
        chain_parser.add_argument('file', help='Path to chain JSON file')
        chain_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        # Export bundle verification
        export_parser = subparsers.add_parser('export', help='Verify an export bundle')
        export_parser.add_argument('file', help='Path to export bundle JSON file')
        export_parser.add_argument('--jwks', help='JWKS URL for signature verification')
        export_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        # Test vectors verification
        vectors_parser = subparsers.add_parser('test-vectors', help='Verify all test vectors')
        vectors_parser.add_argument('directory', help='Path to test vectors directory')
        vectors_parser.add_argument('--jwks', help='JWKS URL for signature verification')
        vectors_parser.add_argument('--ci', action='store_true', help='CI mode (exit codes)')
        vectors_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        # Server verification
        server_parser = subparsers.add_parser('server', help='Verify server health and JWKS')
        server_parser.add_argument('url', help='Server URL (e.g., http://localhost:8088)')
        server_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    def run(self, args=None):
        """Run the CLI with provided arguments."""
        args = self.parser.parse_args(args)
        
        if not args.command:
            self.parser.print_help()
            return 1
        
        try:
            if args.command == 'receipt':
                return self._verify_receipt(args)
            elif args.command == 'chain':
                return self._verify_chain(args)
            elif args.command == 'export':
                return self._verify_export(args)
            elif args.command == 'test-vectors':
                return self._verify_test_vectors(args)
            elif args.command == 'server':
                return self._verify_server(args)
            else:
                print(f"Unknown command: {args.command}")
                return 1
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return 1
    
    def _verify_receipt(self, args) -> int:
        """Verify a single receipt."""
        try:
            # Load receipt
            with open(args.file) as f:
                receipt = json.load(f)
            
            # Load previous receipt if provided
            previous_receipt = None
            if args.previous:
                with open(args.previous) as f:
                    previous_receipt = json.load(f)
            
            print(f"🔍 Verifying receipt: {args.file}")
            
            # Verify
            valid, reason = verify_receipt(receipt, previous_receipt)
            
            if valid:
                print("✅ Receipt verification: PASSED")
                if args.verbose:
                    print(f"   Trace ID: {receipt.get('trace_id')}")
                    print(f"   Hop: {receipt.get('hop')}")
                    print(f"   Receipt Hash: {receipt.get('receipt_hash', 'N/A')[:20]}...")
                return 0
            else:
                print(f"❌ Receipt verification: FAILED - {reason}")
                return 1
                
        except Exception as e:
            print(f"❌ Receipt verification failed: {str(e)}")
            return 1
    
    def _verify_chain(self, args) -> int:
        """Verify a receipt chain."""
        try:
            # Load chain
            with open(args.file) as f:
                chain = json.load(f)
            
            print(f"🔗 Verifying chain: {args.file}")
            print(f"   Chain length: {len(chain)} receipts")
            
            # Verify
            valid, reason = verify_chain(chain)
            
            if valid:
                print("✅ Chain verification: PASSED")
                if args.verbose:
                    for i, receipt in enumerate(chain):
                        print(f"   Receipt {i+1}: {receipt.get('trace_id')} hop {receipt.get('hop')}")
                return 0
            else:
                print(f"❌ Chain verification: FAILED - {reason}")
                return 1
                
        except Exception as e:
            print(f"❌ Chain verification failed: {str(e)}")
            return 1
    
    def _verify_export(self, args) -> int:
        """Verify an export bundle."""
        try:
            # Load export bundle
            with open(args.file) as f:
                bundle = json.load(f)
            
            print(f"📦 Verifying export bundle: {args.file}")
            
            # Verify
            valid, reason = verify_export_bundle(bundle, args.jwks)
            
            if valid:
                print("✅ Export bundle verification: PASSED")
                if args.verbose:
                    print(f"   Trace ID: {bundle.get('trace_id')}")
                    print(f"   Chain length: {len(bundle.get('chain', []))}")
                    print(f"   Bundle CID: {bundle.get('bundle_cid', 'N/A')[:20]}...")
                    if bundle.get('signature'):
                        print(f"   Signature: {bundle.get('signature', 'N/A')[:20]}...")
                return 0
            else:
                print(f"❌ Export bundle verification: FAILED - {reason}")
                return 1
                
        except Exception as e:
            print(f"❌ Export bundle verification failed: {str(e)}")
            return 1
    
    def _verify_test_vectors(self, args) -> int:
        """Verify all test vectors in a directory."""
        try:
            test_dir = Path(args.directory)
            if not test_dir.exists():
                print(f"❌ Test vectors directory not found: {args.directory}")
                return 1
            
            print(f"🧪 Verifying test vectors in: {args.directory}")
            
            total_tests = 0
            passed_tests = 0
            failed_tests = []
            
            # Verify receipts
            receipts_dir = test_dir / 'receipts'
            if receipts_dir.exists():
                for receipt_file in receipts_dir.glob('*.json'):
                    total_tests += 1
                    try:
                        with open(receipt_file) as f:
                            receipt = json.load(f)
                        
                        valid, reason = verify_receipt(receipt)
                        if valid:
                            passed_tests += 1
                            if args.verbose:
                                print(f"   ✅ {receipt_file.name}")
                        else:
                            failed_tests.append(f"{receipt_file.name}: {reason}")
                            if args.verbose:
                                print(f"   ❌ {receipt_file.name}: {reason}")
                    except Exception as e:
                        failed_tests.append(f"{receipt_file.name}: {str(e)}")
                        if args.verbose:
                            print(f"   ❌ {receipt_file.name}: {str(e)}")
            
            # Verify chains
            chains_dir = test_dir / 'chains'
            if chains_dir.exists():
                for chain_file in chains_dir.glob('*.json'):
                    total_tests += 1
                    try:
                        with open(chain_file) as f:
                            chain = json.load(f)
                        
                        valid, reason = verify_chain(chain)
                        if valid:
                            passed_tests += 1
                            if args.verbose:
                                print(f"   ✅ {chain_file.name}")
                        else:
                            failed_tests.append(f"{chain_file.name}: {reason}")
                            if args.verbose:
                                print(f"   ❌ {chain_file.name}: {reason}")
                    except Exception as e:
                        failed_tests.append(f"{chain_file.name}: {str(e)}")
                        if args.verbose:
                            print(f"   ❌ {chain_file.name}: {str(e)}")
            
            # Verify exports
            exports_dir = test_dir / 'exports'
            if exports_dir.exists():
                for export_file in exports_dir.glob('*.json'):
                    total_tests += 1
                    try:
                        with open(export_file) as f:
                            bundle = json.load(f)
                        
                        valid, reason = verify_export_bundle(bundle, args.jwks)
                        if valid:
                            passed_tests += 1
                            if args.verbose:
                                print(f"   ✅ {export_file.name}")
                        else:
                            failed_tests.append(f"{export_file.name}: {reason}")
                            if args.verbose:
                                print(f"   ❌ {export_file.name}: {reason}")
                    except Exception as e:
                        failed_tests.append(f"{export_file.name}: {str(e)}")
                        if args.verbose:
                            print(f"   ❌ {export_file.name}: {str(e)}")
            
            # Report results
            print(f"\n📊 Test Results:")
            print(f"   Total tests: {total_tests}")
            print(f"   Passed: {passed_tests}")
            print(f"   Failed: {len(failed_tests)}")
            
            if failed_tests:
                print(f"\n❌ Failed tests:")
                for failure in failed_tests:
                    print(f"   • {failure}")
            
            if len(failed_tests) == 0:
                print(f"\n✅ All test vectors passed!")
                return 0
            else:
                if args.ci:
                    return 1
                return 0
                
        except Exception as e:
            print(f"❌ Test vectors verification failed: {str(e)}")
            return 1
    
    def _verify_server(self, args) -> int:
        """Verify server health and JWKS."""
        try:
            server_url = args.url.rstrip('/')
            print(f"🌐 Verifying server: {server_url}")
            
            # Check health endpoint
            try:
                response = requests.get(f"{server_url}/healthz", timeout=10)
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"   ✅ Health check: OK")
                    if args.verbose:
                        print(f"      Storage: {health_data.get('storage', 'unknown')}")
                        print(f"      Timestamp: {health_data.get('ts', 'unknown')}")
                else:
                    print(f"   ❌ Health check: HTTP {response.status_code}")
                    return 1
            except Exception as e:
                print(f"   ❌ Health check failed: {str(e)}")
                return 1
            
            # Check JWKS endpoint
            try:
                response = requests.get(f"{server_url}/.well-known/jwks.json", timeout=10)
                if response.status_code == 200:
                    jwks_data = response.json()
                    keys = jwks_data.get('keys', [])
                    print(f"   ✅ JWKS endpoint: {len(keys)} keys available")
                    if args.verbose:
                        for i, key in enumerate(keys):
                            print(f"      Key {i+1}: {key.get('kid', 'unknown')} ({key.get('kty', 'unknown')})")
                else:
                    print(f"   ❌ JWKS endpoint: HTTP {response.status_code}")
                    return 1
            except Exception as e:
                print(f"   ❌ JWKS check failed: {str(e)}")
                return 1
            
            # Check metrics endpoint
            try:
                response = requests.get(f"{server_url}/metrics", timeout=10)
                if response.status_code == 200:
                    print(f"   ✅ Metrics endpoint: Available")
                else:
                    print(f"   ⚠️  Metrics endpoint: HTTP {response.status_code}")
            except Exception as e:
                print(f"   ⚠️  Metrics endpoint: {str(e)}")
            
            print(f"\n✅ Server verification completed!")
            return 0
            
        except Exception as e:
            print(f"❌ Server verification failed: {str(e)}")
            return 1


def main():
    """Main entry point for CLI."""
    cli = SignetVerifyCLI()
    return cli.run()

if __name__ == '__main__':
    sys.exit(main())
