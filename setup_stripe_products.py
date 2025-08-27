#!/usr/bin/env python3
"""
Stripe Products Setup for Signet Protocol
Creates enterprise billing products and payment links based on the product strategy.
"""

import os
import json
import requests
from typing import Dict, Any, Optional

class StripeProductSetup:
    """Setup Stripe products and pricing for Signet Protocol enterprise billing."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stripe.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    
    def create_product(self, name: str, description: str, product_type: str = "service") -> Optional[Dict[str, Any]]:
        """Create a Stripe product."""
        data = {
            "name": name,
            "description": description,
            "type": product_type
        }
        
        response = requests.post(
            f"{self.base_url}/products",
            headers=self.headers,
            data=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to create product '{name}': {response.text}")
            return None
    
    def create_price(self, product_id: str, unit_amount: int, currency: str = "usd", 
                    nickname: str = None, recurring: bool = False) -> Optional[Dict[str, Any]]:
        """Create a Stripe price for a product."""
        data = {
            "product": product_id,
            "unit_amount": unit_amount,
            "currency": currency
        }
        
        if nickname:
            data["nickname"] = nickname
        
        if recurring:
            data["recurring[interval]"] = "month"
        
        response = requests.post(
            f"{self.base_url}/prices",
            headers=self.headers,
            data=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to create price: {response.text}")
            return None
    
    def create_payment_link(self, price_id: str, quantity: int = 1) -> Optional[Dict[str, Any]]:
        """Create a payment link for a price."""
        data = {
            f"line_items[0][price]": price_id,
            f"line_items[0][quantity]": quantity
        }
        
        response = requests.post(
            f"{self.base_url}/payment_links",
            headers=self.headers,
            data=data
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to create payment link: {response.text}")
            return None
    
    def setup_signet_products(self) -> Dict[str, Any]:
        """Set up all Signet Protocol products and pricing."""
        print("🚀 Setting up Stripe products for Signet Protocol Enterprise Billing...\n")
        
        results = {
            "products": {},
            "prices": {},
            "payment_links": {},
            "errors": []
        }
        
        try:
            # 1. Create VEx (Verified Exchange) Product
            print("📦 Creating VEx (Verified Exchange) Product...")
            vex_product = self.create_product(
                name="Signet VEx (Verified Exchange)",
                description="Verified Exchange operations - cryptographic verification of AI interactions with hash-linked receipts and audit trails"
            )
            
            if vex_product:
                results["products"]["vex"] = vex_product
                print(f"✅ VEx Product created: {vex_product['id']}")
                
                # VEx Pricing Tiers
                print("💰 Creating VEx pricing tiers...")
                
                # Tier 1: $0.005 per VEx (up to 50,000)
                vex_tier1 = self.create_price(
                    product_id=vex_product["id"],
                    unit_amount=500,  # $0.005 in cents
                    nickname="VEx Tier 1 - $0.005 per exchange"
                )
                if vex_tier1:
                    results["prices"]["vex_tier1"] = vex_tier1
                    print(f"✅ VEx Tier 1 pricing: {vex_tier1['id']}")
                
                # Tier 2: $0.008 per VEx (50,000+)
                vex_tier2 = self.create_price(
                    product_id=vex_product["id"],
                    unit_amount=800,  # $0.008 in cents
                    nickname="VEx Tier 2 - $0.008 per exchange"
                )
                if vex_tier2:
                    results["prices"]["vex_tier2"] = vex_tier2
                    print(f"✅ VEx Tier 2 pricing: {vex_tier2['id']}")
            
            # 2. Create FU (Fallback Units) Product
            print("\n📦 Creating FU (Fallback Units) Product...")
            fu_product = self.create_product(
                name="Signet FU (Fallback Units)",
                description="Fallback Units for AI repair services - token-based usage when LLM assistance is required for JSON validation"
            )
            
            if fu_product:
                results["products"]["fu"] = fu_product
                print(f"✅ FU Product created: {fu_product['id']}")
                
                # FU Pricing Tiers
                print("💰 Creating FU pricing tiers...")
                
                # Tier 1: $0.001 per token (up to 250,000)
                fu_tier1 = self.create_price(
                    product_id=fu_product["id"],
                    unit_amount=100,  # $0.001 in cents
                    nickname="FU Tier 1 - $0.001 per token"
                )
                if fu_tier1:
                    results["prices"]["fu_tier1"] = fu_tier1
                    print(f"✅ FU Tier 1 pricing: {fu_tier1['id']}")
                
                # Tier 2: $0.0008 per token (250,000+)
                fu_tier2 = self.create_price(
                    product_id=fu_product["id"],
                    unit_amount=80,  # $0.0008 in cents
                    nickname="FU Tier 2 - $0.0008 per token"
                )
                if fu_tier2:
                    results["prices"]["fu_tier2"] = fu_tier2
                    print(f"✅ FU Tier 2 pricing: {fu_tier2['id']}")
            
            # 3. Create Enterprise Subscription Plans
            print("\n📦 Creating Enterprise Subscription Plans...")
            
            # Starter Plan
            starter_product = self.create_product(
                name="Signet Protocol - Starter Plan",
                description="Starter plan with 10,000 VEx and 50,000 FU tokens monthly"
            )
            
            if starter_product:
                results["products"]["starter"] = starter_product
                starter_price = self.create_price(
                    product_id=starter_product["id"],
                    unit_amount=49900,  # $499/month
                    nickname="Starter Plan - $499/month",
                    recurring=True
                )
                if starter_price:
                    results["prices"]["starter_monthly"] = starter_price
                    print(f"✅ Starter Plan: {starter_price['id']}")
            
            # Professional Plan
            pro_product = self.create_product(
                name="Signet Protocol - Professional Plan",
                description="Professional plan with 100,000 VEx and 500,000 FU tokens monthly"
            )
            
            if pro_product:
                results["products"]["professional"] = pro_product
                pro_price = self.create_price(
                    product_id=pro_product["id"],
                    unit_amount=199900,  # $1,999/month
                    nickname="Professional Plan - $1,999/month",
                    recurring=True
                )
                if pro_price:
                    results["prices"]["pro_monthly"] = pro_price
                    print(f"✅ Professional Plan: {pro_price['id']}")
            
            # Enterprise Plan
            enterprise_product = self.create_product(
                name="Signet Protocol - Enterprise Plan",
                description="Enterprise plan with 1,000,000 VEx and 5,000,000 FU tokens monthly"
            )
            
            if enterprise_product:
                results["products"]["enterprise"] = enterprise_product
                enterprise_price = self.create_price(
                    product_id=enterprise_product["id"],
                    unit_amount=999900,  # $9,999/month
                    nickname="Enterprise Plan - $9,999/month",
                    recurring=True
                )
                if enterprise_price:
                    results["prices"]["enterprise_monthly"] = enterprise_price
                    print(f"✅ Enterprise Plan: {enterprise_price['id']}")
            
            # 4. Create Payment Links for Subscription Plans
            print("\n🔗 Creating payment links...")
            
            for plan_name, price_key in [
                ("starter", "starter_monthly"),
                ("professional", "pro_monthly"),
                ("enterprise", "enterprise_monthly")
            ]:
                if price_key in results["prices"]:
                    payment_link = self.create_payment_link(results["prices"][price_key]["id"])
                    if payment_link:
                        results["payment_links"][plan_name] = payment_link
                        print(f"✅ {plan_name.title()} payment link: {payment_link['url']}")
            
            print("\n🎉 Stripe products and pricing setup completed successfully!")
            
            # Generate configuration update
            self.generate_config_update(results)
            
            return results
            
        except Exception as e:
            error_msg = f"Setup failed: {str(e)}"
            results["errors"].append(error_msg)
            print(f"❌ {error_msg}")
            return results
    
    def generate_config_update(self, results: Dict[str, Any]):
        """Generate configuration updates for reserved.json and settings."""
        print("\n📋 Configuration Updates:")
        print("=" * 50)
        
        # Update for reserved.json
        if "prices" in results:
            print("\n🔧 Add these Stripe item IDs to your reserved.json:")
            print("```json")
            config_update = {
                "stripe_items": {
                    "vex_tier1": results["prices"].get("vex_tier1", {}).get("id", "price_xxx"),
                    "vex_tier2": results["prices"].get("vex_tier2", {}).get("id", "price_xxx"),
                    "fu_tier1": results["prices"].get("fu_tier1", {}).get("id", "price_xxx"),
                    "fu_tier2": results["prices"].get("fu_tier2", {}).get("id", "price_xxx")
                },
                "subscription_plans": {
                    "starter": results["prices"].get("starter_monthly", {}).get("id", "price_xxx"),
                    "professional": results["prices"].get("pro_monthly", {}).get("id", "price_xxx"),
                    "enterprise": results["prices"].get("enterprise_monthly", {}).get("id", "price_xxx")
                }
            }
            print(json.dumps(config_update, indent=2))
            print("```")
        
        # Payment links for sales
        if "payment_links" in results:
            print("\n🔗 Payment Links for Sales:")
            for plan, link_data in results["payment_links"].items():
                print(f"- {plan.title()} Plan: {link_data['url']}")
        
        print("\n💡 Next Steps:")
        print("1. Update your reserved.json with the new Stripe item IDs")
        print("2. Configure tenant API keys with appropriate stripe_item references")
        print("3. Test the billing integration with the Signet Protocol server")
        print("4. Set up webhooks for subscription events")
        print("5. Configure your Stripe dashboard with proper tax settings")


def main():
    """Main setup function."""
    # Get Stripe API key from environment or prompt
    api_key = os.getenv("STRIPE_SECRET_KEY")
    
    if not api_key:
        print("❌ STRIPE_SECRET_KEY environment variable not set")
        print("Please set your Stripe secret key:")
        print("export STRIPE_SECRET_KEY=sk_live_...")
        return 1
    
    if not api_key.startswith(("sk_live_", "sk_test_")):
        print("❌ Invalid Stripe API key format")
        return 1
    
    # Determine if using test or live mode
    mode = "LIVE" if api_key.startswith("sk_live_") else "TEST"
    print(f"🔑 Using Stripe {mode} mode")
    
    if mode == "LIVE":
        confirm = input("⚠️  You are using LIVE mode. This will create real products. Continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Setup cancelled.")
            return 0
    
    # Run setup
    setup = StripeProductSetup(api_key)
    results = setup.setup_signet_products()
    
    # Save results
    with open("stripe_setup_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to stripe_setup_results.json")
    
    if results.get("errors"):
        print(f"\n⚠️  Setup completed with {len(results['errors'])} errors")
        return 1
    else:
        print("\n✅ Setup completed successfully!")
        return 0


if __name__ == "__main__":
    exit(main())
