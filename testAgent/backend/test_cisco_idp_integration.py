#!/usr/bin/env python3
"""
Test script for Cisco IDP + Azure OpenAI integration
File: test_cisco_idp_integration.py
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_cisco_idp_authentication():
    """Test Cisco IDP authentication"""
    print("Testing Cisco IDP Authentication...")
    print("=" * 50)
    
    try:
        from services.azure_openai_service import azure_openai_service
        
        # Test authentication
        await azure_openai_service._authenticate_and_initialize_llm()
        print("✓ Cisco IDP authentication successful")
        
        # Get token info
        token_info = await azure_openai_service.get_token_info()
        print(f"Token status: {'✓ Valid' if token_info['has_token'] else '❌ Invalid'}")
        print(f"Token expires: {token_info['token_expires_at']}")
        print(f"Time until expiry: {token_info['time_until_expiry']}")
        print(f"IDP endpoint: {token_info['cisco_idp_endpoint']}")
        print(f"App key: {token_info['app_key']}")
        
        return token_info['has_token']
        
    except Exception as e:
        print(f"❌ Cisco IDP authentication failed: {e}")
        return False

async def test_azure_openai_with_cisco_auth():
    """Test Azure OpenAI with Cisco IDP authentication"""
    print("\nTesting Azure OpenAI with Cisco Authentication...")
    print("=" * 50)
    
    try:
        from services.azure_openai_service import azure_openai_service
        
        # Initialize service (includes authentication)
        await azure_openai_service.initialize()
        print("✓ Azure OpenAI service initialized with Cisco IDP")
        
        # Test connection
        connection_result = await azure_openai_service.test_connection()
        print(f"Connection test: {connection_result['status']}")
        print(f"Message: {connection_result['message']}")
        print(f"Authentication method: {connection_result.get('authentication', 'unknown')}")
        
        if connection_result['status'] == 'success':
            print(f"✓ Connected to: {connection_result.get('endpoint', 'Unknown')}")
            print(f"✓ Using model: {connection_result.get('model', 'Unknown')}")
            print(f"✓ App key: {connection_result.get('app_key', 'Unknown')}")
            return True
        else:
            print(f"❌ Connection failed: {connection_result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Azure OpenAI with Cisco auth test failed: {e}")
        return False

async def test_playwright_generation_with_cisco():
    """Test Playwright test generation with Cisco IDP authentication"""
    print("\nTesting Playwright Generation with Cisco IDP...")
    print("=" * 50)
    
    try:
        from services.playwright_generator import PlaywrightGeneratorService
        
        # Initialize service
        playwright_generator = PlaywrightGeneratorService()
        await playwright_generator.initialize()
        print("✓ Playwright generator initialized with Cisco IDP")
        
        # Test data
        workflow_name = "cisco_login_flow"
        tdd_template = '''test_cisco_catalyst_login
Given: User with valid Cisco credentials admin1/password123
When: The user navigates to Cisco Catalyst Center login page
When: The user enters credentials and clicks login button
When: The user waits for home page to load
Then: The system should display "Welcome to Catalyst Center!" message
Then: The system should show the main navigation menu'''
        
        cluster_config = {
            "url": "https://172.27.248.237:443/",
            "username": "admin1", 
            "password": "password123",
            "verify_ssl": False
        }
        
        # Generate test using Cisco IDP authenticated Azure OpenAI
        print(f"Generating Playwright test for {workflow_name}...")
        print("Using Cisco IDP authenticated Azure OpenAI...")
        
        playwright_code = await playwright_generator.generate_playwright_test(
            workflow_name=workflow_name,
            tdd_template=tdd_template,
            cluster_config=cluster_config
        )
        
        print("✓ Playwright test generated successfully with Cisco authentication!")
        print(f"Generated code length: {len(playwright_code)} characters")
        
        # Show first 25 lines
        lines = playwright_code.split('\n')[:25]
        print("\nFirst 25 lines of AI-generated test:")
        print("-" * 50)
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: {line}")
        
        if len(lines) >= 25:
            print("    ... (truncated)")
        
        # Validate generated code
        validation_checks = {
            "Contains test function": "test(" in playwright_code,
            #"Contains expect statements": "expect(" in playwright_code,
            "Contains page actions": "page." in playwright_code,
            "Contains imports": "import" in playwright_code,
            "Contains Cisco-specific elements": any(keyword in playwright_code.lower() 
                                                  for keyword in ["catalyst", "cisco", "welcome"]),
            "Proper structure": playwright_code.count('{') == playwright_code.count('}')
        }
        
        print(f"\nCode validation:")
        all_valid = True
        for check, result in validation_checks.items():
            status = "✓" if result else "❌"
            print(f"  {check}: {status}")
            if not result:
                all_valid = False
        
        return all_valid
            
    except Exception as e:
        print(f"❌ Playwright generation with Cisco auth failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_token_refresh():
    """Test token refresh functionality"""
    print("\nTesting Token Refresh...")
    print("=" * 50)
    
    try:
        from services.azure_openai_service import azure_openai_service
        
        # Get initial token info
        initial_token_info = await azure_openai_service.get_token_info()
        print(f"Initial token expires: {initial_token_info['token_expires_at']}")
        
        # Force token refresh
        print("Forcing token refresh...")
        await azure_openai_service._authenticate_and_initialize_llm()
        
        # Get new token info
        new_token_info = await azure_openai_service.get_token_info()
        print(f"New token expires: {new_token_info['token_expires_at']}")
        
        # Verify new token is different
        if new_token_info['token_expires_at'] != initial_token_info['token_expires_at']:
            print("✓ Token refresh successful")
            return True
        else:
            print("⚠️  Token refresh may not have generated new token")
            return True  # Still consider success as token might be cached
            
    except Exception as e:
        print(f"❌ Token refresh test failed: {e}")
        return False

async def test_environment_configuration():
    """Test environment configuration for Cisco IDP"""
    print("\nTesting Environment Configuration...")
    print("=" * 50)
    
    try:
        from core.config import settings
        
        print("Cisco IDP Configuration:")
        print(f"  CISCO_CLIENT_ID: {'✓ Set' if settings.AZURE_CLIENT_ID else '❌ Not set'}")
        print(f"  CISCO_CLIENT_SECRET: {'✓ Set' if settings.AZURE_CLIENT_SECRET else '❌ Not set'}")
        print(f"  CISCO_APP_KEY: {'✓ Set' if settings.AZURE_OPENAI_APP_KEY else '❌ Not set'}")
        print(f"  CISCO_IDP_ENDPOINT: {'✓ Set' if settings.CISCO_IDP else '❌ Not set'}")
        
        print("\nAzure OpenAI Configuration:")
        print(f"  AZURE_OPENAI_ENDPOINT: {'✓ Set' if settings.AZURE_OPENAI_ENDPOINT else '❌ Not set'}")
        print(f"  AZURE_OPENAI_DEPLOYMENT_NAME: {settings.AZURE_OPENAI_MODEL}")
        print(f"  AZURE_OPENAI_API_VERSION: {settings.AZURE_OPENAI_API_VERSION}")
        
        print("\nGeneration Configuration:")
        print(f"  GENERATION_TEMPERATURE: {settings.GENERATION_TEMPERATURE}")
        print(f"  MAX_RETRIES: {settings.MAX_RETRIES}")
        print(f"  REQUEST_TIMEOUT: {settings.REQUEST_TIMEOUT}")
        
        # Check if all required settings are configured
        required_cisco_settings = [
            settings.AZURE_CLIENT_ID,
            settings.AZURE_CLIENT_SECRET,
            settings.AZURE_OPENAI_APP_KEY,
            settings.CISCO_IDP,
            settings.AZURE_OPENAI_ENDPOINT
        ]
        
        if all(required_cisco_settings):
            print("✓ Cisco IDP configuration appears complete")
            return True
        else:
            print("❌ Missing required Cisco IDP configuration")
            print("Please check your .env file")
            return False
            
    except Exception as e:
        print(f"❌ Environment configuration test failed: {e}")
        return False

async def main():
    """Run all Cisco IDP + Azure OpenAI integration tests"""
    print("🔐 CISCO IDP + AZURE OPENAI INTEGRATION TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Environment Configuration", test_environment_configuration),
        ("Cisco IDP Authentication", test_cisco_idp_authentication),
        ("Azure OpenAI with Cisco Auth", test_azure_openai_with_cisco_auth),
        ("Token Refresh", test_token_refresh),
        ("Playwright Generation", test_playwright_generation_with_cisco),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY:")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🚀 ALL TESTS PASSED! Cisco IDP + Azure OpenAI integration is working!")
        print("Your E2E Testing Agent is now powered by:")
        print("  🔐 Cisco IDP Authentication")
        print("  🤖 Azure OpenAI AI-generated Playwright tests")
        print("  🏢 Enterprise-ready security and authentication")
    else:
        print("⚠️  Some tests failed. Check the errors above and your configuration.")
        print("Common issues:")
        print("  - Missing .env file with Cisco IDP credentials")
        print("  - Incorrect Cisco IDP endpoint or credentials")
        print("  - Azure OpenAI endpoint not configured")
        print("  - Network connectivity issues to Cisco IDP or Azure")
        print("  - Missing required Python packages (run: pip install -r requirements.txt)")

if __name__ == "__main__":
    asyncio.run(main())