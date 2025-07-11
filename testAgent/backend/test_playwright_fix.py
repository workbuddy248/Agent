#!/usr/bin/env python3
"""
Test script to verify Playwright generator fix
File: test_playwright_fix.py
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_playwright_generator():
    """Test the PlaywrightGeneratorService with the new method"""
    print("Testing PlaywrightGeneratorService...")
    print("=" * 50)
    
    try:
        from services.playwright_generator import PlaywrightGeneratorService
        
        # Create service
        playwright_generator = PlaywrightGeneratorService()
        await playwright_generator.initialize()
        print("✓ PlaywrightGeneratorService initialized")
        
        # Test data
        workflow_name = "login_flow"
        tdd_template = '''test_valid_login
Given: User with a valid username admin1 and password password123
When: The user navigates to https://172.27.248.237:443/ login page
When: The user enters credentials and clicks login button
Then: The system should land into the home page on successful login
Then: The system should check the title element be present in the home page'''
        
        cluster_config = {
            "url": "https://172.27.248.237:443/",
            "username": "admin1",
            "password": "password123"
        }
        
        # Test the new method
        print(f"Generating Playwright test for: {workflow_name}")
        playwright_code = await playwright_generator.generate_playwright_test(
            workflow_name=workflow_name,
            tdd_template=tdd_template,
            cluster_config=cluster_config
        )
        
        print("✓ generate_playwright_test method works!")
        print(f"Generated code length: {len(playwright_code)} characters")
        
        # Show first few lines of generated code
        lines = playwright_code.split('\n')[:10]
        print("\nFirst 10 lines of generated code:")
        for i, line in enumerate(lines, 1):
            print(f"  {i:2d}: {line}")
        
        # Test connection method
        connection_result = await playwright_generator.test_connection()
        print(f"\n✓ test_connection works: {connection_result['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ PlaywrightGeneratorService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_playwright_generator())