#!/usr/bin/env python3
"""
Test script to simulate the complete workflow execution path
File: test_full_workflow.py
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_complete_workflow():
    """Test the complete workflow that main.py executes"""
    print("Testing complete workflow execution...")
    print("=" * 60)
    
    try:
        # Import all required services
        from services.instruction_parser import InstructionParserService
        from services.workflow_manager import WorkflowManagerService
        from services.template_manager import TemplateManagerService
        from services.playwright_generator import PlaywrightGeneratorService
        from services.session_manager import SessionManagerService
        
        print("✓ All services imported successfully")
        
        # Initialize services
        instruction_parser = InstructionParserService()
        workflow_manager = WorkflowManagerService()
        template_manager = TemplateManagerService()
        playwright_generator = PlaywrightGeneratorService()
        session_manager = SessionManagerService()
        
        await instruction_parser.initialize()
        await workflow_manager.initialize()
        await template_manager.initialize()
        await playwright_generator.initialize()
        
        print("✓ All services initialized successfully")
        
        # Test data similar to what UI sends
        instruction = "test login to the cluster"
        cluster_url = "https://172.27.248.237:443/"
        username = "admin1"
        password = "password123"
        
        print(f"\nTesting with instruction: '{instruction}'")
        
        # Step 1: Parse instruction (simulating parse_test_instructions)
        print("\n1. Parsing instruction...")
        parsed_result = await instruction_parser.parse_instruction(
            instruction=instruction,
            cluster_url=cluster_url,
            username=username,
            password=password
        )
        print(f"   ✓ Workflows: {parsed_result.workflows}")
        print(f"   ✓ Parameters: {len(parsed_result.parameters)}")
        
        # Step 2: Resolve workflow chain
        print("\n2. Resolving workflow chain...")
        session_id = "test-session-123"
        execution_plan = await workflow_manager.resolve_workflow_chain(
            primary_workflows=parsed_result.workflows,
            parameters=parsed_result.parameters,
            session_id=session_id
        )
        print(f"   ✓ Execution chain: {execution_plan.execution_chain}")
        print(f"   ✓ Requires clarification: {execution_plan.requires_clarification}")
        
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
        print(f"   ✓ Session created: {session.session_id}")
        
        # Step 4: Load templates (simulating execute_test_workflow)
        print("\n4. Loading templates...")
        templates = {}
        for workflow_name in session.workflows:
            print(f"   Loading template for: {workflow_name}")
            template_content = await template_manager.load_tdd_template(workflow_name)
            templates[workflow_name] = template_content
            print(f"   ✓ Template loaded: {len(template_content)} characters")
        
        # Step 5: Customize templates
        print("\n5. Customizing templates...")
        customized_templates = {}
        for workflow_name, template_content in templates.items():
            customized_template = await template_manager.customize_template(
                template_content, session.parameters
            )
            customized_templates[workflow_name] = customized_template
            print(f"   ✓ Template customized for: {workflow_name}")
        
        # Step 6: Generate Playwright tests (this was failing before)
        print("\n6. Generating Playwright tests...")
        playwright_tests = {}
        for workflow_name, customized_template in customized_templates.items():
            print(f"   Generating test for: {workflow_name}")
            playwright_code = await playwright_generator.generate_playwright_test(
                workflow_name=workflow_name,
                tdd_template=customized_template,
                cluster_config=session.cluster_config
            )
            playwright_tests[workflow_name] = playwright_code
            print(f"   ✓ Generated {len(playwright_code)} characters of test code")
        
        print("\n🎉 Complete workflow test PASSED!")
        print(f"   Generated {len(playwright_tests)} Playwright test(s)")
        
        # Show a sample of the generated code
        if playwright_tests:
            first_test = list(playwright_tests.values())[0]
            lines = first_test.split('\n')[:8]
            print(f"\nSample generated test code:")
            for line in lines:
                print(f"   {line}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete workflow test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_complete_workflow())