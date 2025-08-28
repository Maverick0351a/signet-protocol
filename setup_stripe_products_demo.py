#!/usr/bin/env python3
"""
Stripe Products Setup Demo for Signet Protocol
Creates a demo configuration showing what would be created for enterprise billing.
"""

import json
from typing import Dict, Any

def generate_demo_stripe_config() -> Dict[str, Any]:
    """Generate demo Stripe configuration for Signet Protocol."""
    
    print("🚀 Generating Stripe Products Configuration for Signet Protocol Enterprise Billing...\n")
    
    # Demo product and price IDs (what would be created)
    demo_config = {
        "products": {
            "vex": {
                "id": "prod_signet_vex_verified_exchange",
                "name": "Signet VEx (Verified Exchange)",
                "description": "Verified Exchange operations - cryptographic verification of AI interactions with hash-linked receipts and audit trails",
                "type": "service"
            },
            "fu": {
                "id": "prod_signet_fu_fallback_units",
                "name": "Signet FU (Fallback Units)", 
                "description": "Fallback Units for AI repair services - token-based usage when LLM assistance is required for JSON validation",
                "type": "service"
            },
            "starter": {
                "id": "prod_signet_starter_plan",
                "name": "Signet Protocol - Starter Plan",
                "description": "Starter plan with 10,000 VEx and 50,000 FU tokens monthly",
                "type": "service"
            },
            "professional": {
                "id": "prod_signet_professional_plan", 
                "name": "Signet Protocol - Professional Plan",
                "description": "Professional plan with 100,000 VEx and 500,000 FU tokens monthly",
                "type": "service"
            },
            "enterprise": {
                "id": "prod_signet_enterprise_plan",
                "name": "Signet Protocol - Enterprise Plan", 
                "description": "Enterprise plan with 1,000,000 VEx and 5,000,000 FU tokens monthly",
                "type": "service"
            }
        },
        "prices": {
            "vex_tier1": {
                "id": "price_signet_vex_tier1_005",
                "product": "prod_signet_vex_verified_exchange",
                "unit_amount": 500,  # $0.005
                "currency": "usd",
                "nickname": "VEx Tier 1 - $0.005 per exchange"
            },
            "vex_tier2": {
                "id": "price_signet_vex_tier2_008",
                "product": "prod_signet_vex_verified_exchange", 
                "unit_amount": 800,  # $0.008
                "currency": "usd",
                "nickname": "VEx Tier 2 - $0.008 per exchange"
            },
            "fu_tier1": {
                "id": "price_signet_fu_tier1_001",
                "product": "prod_signet_fu_fallback_units",
                "unit_amount": 100,  # $0.001
                "currency": "usd", 
                "nickname": "FU Tier 1 - $0.001 per token"
            },
            "fu_tier2": {
                "id": "price_signet_fu_tier2_0008",
                "product": "prod_signet_fu_fallback_units",
                "unit_amount": 80,  # $0.0008
                "currency": "usd",
                "nickname": "FU Tier 2 - $0.0008 per token"
            },
            "starter_monthly": {
                "id": "price_signet_starter_monthly_499",
                "product": "prod_signet_starter_plan",
                "unit_amount": 49900,  # $499/month
                "currency": "usd",
                "recurring": {"interval": "month"},
                "nickname": "Starter Plan - $499/month"
            },
            "pro_monthly": {
                "id": "price_signet_pro_monthly_1999", 
                "product": "prod_signet_professional_plan",
                "unit_amount": 199900,  # $1,999/month
                "currency": "usd",
                "recurring": {"interval": "month"},
                "nickname": "Professional Plan - $1,999/month"
            },
            "enterprise_monthly": {
                "id": "price_signet_enterprise_monthly_9999",
                "product": "prod_signet_enterprise_plan", 
                "unit_amount": 999900,  # $9,999/month
                "currency": "usd",
                "recurring": {"interval": "month"},
                "nickname": "Enterprise Plan - $9,999/month"
            }
        },
        "payment_links": {
            "starter": {
                "id": "plink_signet_starter",
                "url": "https://buy.stripe.com/signet-starter-plan",
                "price": "price_signet_starter_monthly_499"
            },
            "professional": {
                "id": "plink_signet_professional",
                "url": "https://buy.stripe.com/signet-professional-plan", 
                "price": "price_signet_pro_monthly_1999"
            },
            "enterprise": {
                "id": "plink_signet_enterprise",
                "url": "https://buy.stripe.com/signet-enterprise-plan",
                "price": "price_signet_enterprise_monthly_9999"
            }
        }
    }
    
    return demo_config

def generate_reserved_config_update(demo_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate updated reserved.json configuration."""
    
    # Enhanced reserved capacity configuration
    reserved_config = {
        "acme_corp": {
            "vex_reserved": 100000,
            "fu_reserved": 500000,
            "vex_overage_tiers": [
                {
                    "threshold": 50000,
                    "price_per_unit": 0.005,
                    "stripe_item": demo_config["prices"]["vex_tier1"]["id"]
                },
                {
                    "threshold": 100000,
                    "price_per_unit": 0.008,
                    "stripe_item": demo_config["prices"]["vex_tier2"]["id"]
                }
            ],
            "fu_overage_tiers": [
                {
                    "threshold": 250000,
                    "price_per_unit": 0.001,
                    "stripe_item": demo_config["prices"]["fu_tier1"]["id"]
                },
                {
                    "threshold": 500000,
                    "price_per_unit": 0.0008,
                    "stripe_item": demo_config["prices"]["fu_tier2"]["id"]
                }
            ]
        },
        "startup_customer": {
            "vex_reserved": 10000,
            "fu_reserved": 50000,
            "subscription_plan": demo_config["prices"]["starter_monthly"]["id"],
            "vex_overage_tiers": [
                {
                    "threshold": 5000,
                    "price_per_unit": 0.005,
                    "stripe_item": demo_config["prices"]["vex_tier1"]["id"]
                }
            ],
            "fu_overage_tiers": [
                {
                    "threshold": 25000,
                    "price_per_unit": 0.001,
                    "stripe_item": demo_config["prices"]["fu_tier1"]["id"]
                }
            ]
        },
        "enterprise_customer": {
            "vex_reserved": 1000000,
            "fu_reserved": 5000000,
            "subscription_plan": demo_config["prices"]["enterprise_monthly"]["id"],
            "vex_overage_tiers": [
                {
                    "threshold": 500000,
                    "price_per_unit": 0.005,
                    "stripe_item": demo_config["prices"]["vex_tier1"]["id"]
                },
                {
                    "threshold": 1000000,
                    "price_per_unit": 0.008,
                    "stripe_item": demo_config["prices"]["vex_tier2"]["id"]
                }
            ],
            "fu_overage_tiers": [
                {
                    "threshold": 2500000,
                    "price_per_unit": 0.001,
                    "stripe_item": demo_config["prices"]["fu_tier1"]["id"]
                },
                {
                    "threshold": 5000000,
                    "price_per_unit": 0.0008,
                    "stripe_item": demo_config["prices"]["fu_tier2"]["id"]
                }
            ]
        }
    }
    
    return reserved_config

def generate_api_keys_config(demo_config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate API keys configuration with Stripe items."""
    
    api_keys_config = {
        "demo_starter_key": {
            "tenant": "startup_customer",
            "allowlist": ["api.example.com", "webhook.site"],
            "fallback_enabled": True,
            "fu_monthly_limit": 50000,
            "stripe_item_vex": demo_config["prices"]["vex_tier1"]["id"],
            "stripe_item_fu": demo_config["prices"]["fu_tier1"]["id"]
        },
        "demo_pro_key": {
            "tenant": "acme_corp",
            "allowlist": ["api.acme.com", "webhooks.acme.com"],
            "fallback_enabled": True,
            "fu_monthly_limit": 500000,
            "stripe_item_vex": demo_config["prices"]["vex_tier1"]["id"],
            "stripe_item_fu": demo_config["prices"]["fu_tier1"]["id"]
        },
        "demo_enterprise_key": {
            "tenant": "enterprise_customer",
            "allowlist": ["*.enterprise.com", "api.partners.com"],
            "fallback_enabled": True,
            "fu_monthly_limit": 5000000,
            "stripe_item_vex": demo_config["prices"]["vex_tier1"]["id"],
            "stripe_item_fu": demo_config["prices"]["fu_tier1"]["id"]
        }
    }
    
    return api_keys_config

def main():
    """Generate complete Stripe configuration for Signet Protocol."""
    
    print("🎯 Signet Protocol - Enterprise Billing Configuration Generator")
    print("=" * 60)
    
    # Generate demo configuration
    demo_config = generate_demo_stripe_config()
    
    print("📦 Products to be created:")
    for product_key, product in demo_config["products"].items():
        print(f"  ✅ {product['name']}")
        print(f"     ID: {product['id']}")
        print(f"     Description: {product['description']}")
        print()
    
    print("💰 Pricing tiers to be created:")
    for price_key, price in demo_config["prices"].items():
        amount = price["unit_amount"] / 100
        recurring = " (monthly)" if price.get("recurring") else ""
        print(f"  ✅ {price['nickname']}")
        print(f"     ID: {price['id']}")
        print(f"     Amount: ${amount:.4f}{recurring}")
        print()
    
    print("🔗 Payment links to be created:")
    for link_key, link in demo_config["payment_links"].items():
        print(f"  ✅ {link_key.title()} Plan: {link['url']}")
    
    print("\n" + "=" * 60)
    
    # Generate configuration files
    reserved_config = generate_reserved_config_update(demo_config)
    api_keys_config = generate_api_keys_config(demo_config)
    
    # Save configurations
    with open("stripe_products_config.json", "w") as f:
        json.dump(demo_config, f, indent=2)
    
    with open("reserved_enterprise.json", "w") as f:
        json.dump(reserved_config, f, indent=2)
    
    with open("api_keys_enterprise.json", "w") as f:
        json.dump(api_keys_config, f, indent=2)
    
    print("📋 Configuration Files Generated:")
    print("  📄 stripe_products_config.json - Complete Stripe product/price definitions")
    print("  📄 reserved_enterprise.json - Enhanced reserved capacity configuration")
    print("  📄 api_keys_enterprise.json - API keys with Stripe item mappings")
    
    print("\n💡 Next Steps to Create Real Stripe Products:")
    print("1. Review the generated configurations")
    print("2. Run: python setup_stripe_products.py (with real Stripe key)")
    print("3. Update your .env file with the actual Stripe product/price IDs")
    print("4. Configure webhooks for subscription events")
    print("5. Test the billing integration")
    
    print("\n🎉 Enterprise billing configuration ready for Signet Protocol!")
    
    return demo_config

if __name__ == "__main__":
    main()
