#!/usr/bin/env python3
"""
Integration test for Stripe MCP server with Signet Protocol billing system
"""

import asyncio
import json
import requests
from datetime import datetime

class SignetMCPIntegrationTest:
    def __init__(self, base_url="http://localhost:8000", api_key="test_api_key"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "X-SIGNET-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def test_health_check(self):
        """Test basic server health"""
        print("🔍 Testing server health...")
        try:
            response = requests.get(f"{self.base_url}/healthz")
            if response.status_code == 200:
                print("✅ Server is healthy")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_setup_stripe_products(self):
        """Test MCP-based Stripe product setup"""
        print("🔍 Testing Stripe product setup via MCP...")
        try:
            response = requests.post(
                f"{self.base_url}/v1/billing/setup-products",
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Stripe products setup successful")
                print(f"   Result: {result.get('message', 'Success')}")
                return True
            else:
                print(f"❌ Product setup failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Product setup error: {e}")
            return False
    
    def test_create_payment_link(self):
        """Test payment link creation for tenant"""
        print("🔍 Testing payment link creation...")
        try:
            response = requests.post(
                f"{self.base_url}/v1/billing/create-payment-link/acme?plan_type=monthly",
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Payment link created successfully")
                if result.get("success"):
                    print(f"   Tenant: {result.get('tenant')}")
                    print(f"   Plan: {result.get('plan_type')}")
                return True
            else:
                print(f"❌ Payment link creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Payment link error: {e}")
            return False
    
    def test_billing_dashboard(self):
        """Test billing dashboard data retrieval"""
        print("🔍 Testing billing dashboard...")
        try:
            response = requests.get(
                f"{self.base_url}/v1/billing/dashboard",
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Billing dashboard data retrieved")
                if result.get("success"):
                    print(f"   MCP Enabled: {result.get('mcp_metrics', {}).get('mcp_enabled')}")
                    print(f"   Products Created: {result.get('mcp_metrics', {}).get('products_created', 0)}")
                return True
            else:
                print(f"❌ Dashboard retrieval failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
            return False
    
    def test_sync_stripe_items(self):
        """Test Stripe items synchronization"""
        print("🔍 Testing Stripe items sync...")
        try:
            response = requests.post(
                f"{self.base_url}/v1/billing/sync-stripe-items",
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Stripe items sync successful")
                if result.get("success"):
                    sync_results = result.get("results", {})
                    print(f"   Tenants Synced: {sync_results.get('tenants_synced', 0)}")
                    print(f"   Products Found: {sync_results.get('products_found', 0)}")
                return True
            else:
                print(f"❌ Stripe sync failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Stripe sync error: {e}")
            return False
    
    def test_exchange_with_billing(self):
        """Test a complete exchange with billing integration"""
        print("🔍 Testing exchange with MCP billing...")
        try:
            # Sample exchange payload
            exchange_payload = {
                "trace_id": f"test-{datetime.now().isoformat()}",
                "payload_type": "openai.tooluse.invoice.v1",
                "target_type": "invoice.iso20022.v1",
                "payload": {
                    "tool_calls": [{
                        "function": {
                            "name": "create_invoice",
                            "arguments": '{"amount": 100.00, "currency": "USD", "description": "Test invoice"}'
                        }
                    }]
                }
            }
            
            headers = {
                **self.headers,
                "X-SIGNET-Idempotency-Key": f"test-{datetime.now().timestamp()}"
            }
            
            response = requests.post(
                f"{self.base_url}/v1/exchange",
                headers=headers,
                json=exchange_payload
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Exchange with billing successful")
                print(f"   Trace ID: {result.get('trace_id')}")
                print(f"   Receipt Hash: {result.get('receipt', {}).get('receipt_hash', 'N/A')}")
                return True
            else:
                print(f"❌ Exchange failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Exchange error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Signet Protocol + Stripe MCP Integration Tests\n")
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Stripe Product Setup", self.test_setup_stripe_products),
            ("Payment Link Creation", self.test_create_payment_link),
            ("Billing Dashboard", self.test_billing_dashboard),
            ("Stripe Items Sync", self.test_sync_stripe_items),
            ("Exchange with Billing", self.test_exchange_with_billing)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            try:
                success = test_func()
                results.append((test_name, success))
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        
        passed = 0
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
            if success:
                passed += 1
        
        print(f"\n🎯 Results: {passed}/{len(results)} tests passed")
        
        if passed == len(results):
            print("🎉 All tests passed! Stripe MCP integration is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        return passed == len(results)

def main():
    """Main test runner"""
    print("🔧 Signet Protocol + Stripe MCP Integration Test Suite")
    print("="*60)
    
    # Configuration
    base_url = "http://localhost:8000"  # Adjust if needed
    api_key = "test_api_key"  # Should match your server configuration
    
    print(f"🌐 Testing against: {base_url}")
    print(f"🔑 Using API key: {api_key}")
    print()
    
    # Run tests
    tester = SignetMCPIntegrationTest(base_url, api_key)
    success = tester.run_all_tests()
    
    if success:
        print("\n✨ Integration test completed successfully!")
        print("The Stripe MCP server is properly integrated with Signet Protocol.")
    else:
        print("\n🔧 Integration test completed with issues.")
        print("Please check the server configuration and MCP setup.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
