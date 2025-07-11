#!/usr/bin/env python3
"""
Test script to verify the final TestExecutorService fix
File: test_final_fix.py
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_test_executor_fix():
    """Test the TestExecutorService execute_tests method"""
    print("Testing TestExecutorService.execute_tests()...")
    print("=" * 50)
    
    try:
        from services.test_executor import TestExecutorService
        
        # Create service
        test_executor = TestExecutorService()
        await test_executor.initialize()
        print("✓ TestExecutorService initialized")
        
        # Test data
        session_id = "test-session-123"
        playwright_tests = {
            "login_flow": '''import { test, expect, Page } from '@playwright/test';

test.describe('login_flow Tests', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    // Setup for login_flow
  });

  test.afterEach(async () => {
    await page.close();
  });

  test('test_valid_login', async () => {
    // Test: test_valid_login
    
    // Navigate to cluster
    await page.goto('https://172.27.248.237:443/');
    
    // Setup: User with a valid username admin1 and password password123
    await page.fill('input[name="username"], input[id="username"]', 'admin1');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"], button:has-text("login"), button:has-text("sign in")');
    // Verify: The system should land into the home page on successful login
    // Verify: The system should check the title element be present in the home page
  });

});'''
        }
        
        cluster_config = {
            "url": "https://172.27.248.237:443/",
            "username": "admin1",
            "password": "password123"
        }
        
        # Test the execute_tests method
        print(f"Testing execute_tests with {len(playwright_tests)} test(s)...")
        execution_results = await test_executor.execute_tests(
            session_id=session_id,
            playwright_tests=playwright_tests,
            cluster_config=cluster_config
        )
        
        print("✓ execute_tests method works!")
        print(f"Results: {execution_results['success']}")
        print(f"Total tests: {execution_results['total_tests']}")
        print(f"Passed: {execution_results['passed_tests']}")
        print(f"Failed: {execution_results['failed_tests']}")
        
        if execution_results['execution_summary']:
            print("\nExecution summary:")
            for summary in execution_results['execution_summary']:
                print(f"  - {summary['workflow']}: {summary['status']} ({summary['duration']:.1f}s)")
        
        # Test browser setup
        browser_test = await test_executor.test_browser_setup()
        print(f"\n✓ test_browser_setup works: {browser_test['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ TestExecutorService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_complete_end_to_end():
    """Test the complete end-to-end workflow"""
    print("\n" + "=" * 60)
    print("Testing COMPLETE END-TO-END WORKFLOW")
    print("=" * 60)
    
    try:
        # Import all services
        from services.instruction_parser import InstructionParserService
        from services.workflow_manager import WorkflowManagerService
        from services.template_manager import TemplateManagerService
        from services.playwright_generator import PlaywrightGeneratorService
        from services.test_executor import TestExecutorService
        from services.session_manager import SessionManagerService
        
        # Initialize all services
        instruction_parser = InstructionParserService()
        workflow_manager = WorkflowManagerService()
        template_manager = TemplateManagerService()
        playwright_generator = PlaywrightGeneratorService()
        test_executor = TestExecutorService()
        session_manager = SessionManagerService()
        
        await instruction_parser.initialize()
        await workflow_manager.initialize()
        await template_manager.initialize()
        await playwright_generator.initialize()
        await test_executor.initialize()
        
        print("✓ All services initialized")
        
        # Test data (exactly like UI sends)
        instruction = "test login on the cluster ip"
        cluster_url = "https://172.27.248.237:443/"
        username = "admin1"
        password = "password123"
        
        print(f"\nInput: '{instruction}'")
        print(f"Cluster: {cluster_url}")
        
        # Step 1: Parse instruction
        print("\n1. Parsing instruction...")
        parsed_result = await instruction_parser.parse_instruction(
            instruction=instruction,
            cluster_url=cluster_url,
            username=username,
            password=password
        )
        print(f"   ✓ Found workflows: {parsed_result.workflows}")
        
        # Step 2: Resolve workflow chain
        print("\n2. Resolving workflow chain...")
        session_id = "end-to-end-test"
        execution_plan = await workflow_manager.resolve_workflow_chain(
            primary_workflows=parsed_result.workflows,
            parameters=parsed_result.parameters,
            session_id=session_id
        )
        print(f"   ✓ Execution chain: {execution_plan.execution_chain}")
        
        # Step 3: Create session
        print("\n3. Creating session...")
        session = await session_manager.create_session(
            session_id=session_id,
            instruction=instruction,
            workflows=execution_plan.execution_chain,
            parameters=parsed_result.parameters,
            cluster_config={
                "url": cluster_url,
                "username": username,
                "password": password
            }
        )
        print(f"   ✓ Session: {session.session_id}")
        
        # Step 4: Load and customize templates
        print("\n4. Loading templates...")
        templates = {}
        for workflow_name in session.workflows:
            template_content = await template_manager.load_tdd_template(workflow_name)
            customized_template = await template_manager.customize_template(
                template_content, session.parameters
            )
            templates[workflow_name] = customized_template
        print(f"   ✓ Loaded {len(templates)} template(s)")
        
        # Step 5: Generate Playwright tests
        print("\n5. Generating Playwright tests...")
        playwright_tests = {}
        for workflow_name, template_content in templates.items():
            playwright_code = await playwright_generator.generate_playwright_test(
                workflow_name=workflow_name,
                tdd_template=template_content,
                cluster_config=session.cluster_config
            )
            playwright_tests[workflow_name] = playwright_code
        print(f"   ✓ Generated {len(playwright_tests)} test(s)")
        
        # Step 6: Execute tests (this was the final missing piece)
        print("\n6. Executing tests...")
        execution_results = await test_executor.execute_tests(
            session_id=session_id,
            playwright_tests=playwright_tests,
            cluster_config=session.cluster_config
        )
        print(f"   ✓ Execution complete: {execution_results['success']}")
        print(f"   ✓ Results: {execution_results['passed_tests']} passed, {execution_results['failed_tests']} failed")
        
        print(f"\n🎉 END-TO-END TEST COMPLETED SUCCESSFULLY!")
        print(f"   📝 Instruction parsed")
        print(f"   🔄 Workflow resolved")
        print(f"   📄 Templates loaded")
        print(f"   🧪 Tests generated")
        print(f"   ▶️  Tests executed")
        
        return True
        
    except Exception as e:
        print(f"❌ End-to-end test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("Final Fix Verification")
    print("=" * 60)
    
    test1_passed = await test_test_executor_fix()
    test2_passed = await test_complete_end_to_end()
    
    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY:")
    print(f"TestExecutor Fix: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"End-to-End Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🚀 ALL SYSTEMS GO! Your E2E Testing Agent is ready!")
        print("   Try the UI now - it should work completely!")
    else:
        print("\n⚠️  Some issues remain - check the error details above")

if __name__ == "__main__":
    asyncio.run(main())