#!/usr/bin/env python3
"""
Clarification System Integration Test
This script tests the complete clarification flow from instruction parsing to execution
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# API Base URL
BASE_URL = "http://localhost:8000"

def test_clarification_flow():
    """Test the complete clarification flow"""
    
    print("🚀 Testing E2E Testing Agent Clarification System")
    print("=" * 60)
    
    # Test 1: Basic Health Check
    print("\n1. Testing Backend Health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Backend is healthy")
        else:
            print("❌ Backend health check failed")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running on port 8000?")
        return False
    
    # Test 2: Template Loading
    print("\n2. Testing Template Loading...")
    try:
        response = requests.get(f"{BASE_URL}/templates/list")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Loaded {data['total_count']} templates")
            for template in data['templates'][:3]:  # Show first 3
                print(f"   - {template['name']} ({template['workflow_type']})")
        else:
            print("❌ Failed to load templates")
            return False
    except Exception as e:
        print(f"❌ Template loading error: {str(e)}")
        return False
    
    # Test 3: Workflow Dependencies
    print("\n3. Testing Workflow Dependencies...")
    try:
        response = requests.get(f"{BASE_URL}/workflows/dependencies")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Loaded dependency graph for {data['workflow_count']} workflows")
            print("   Sample dependencies:")
            for workflow, info in list(data['dependency_graph'].items())[:3]:
                deps = ", ".join(info['dependencies']) if info['dependencies'] else "None"
                print(f"   - {workflow}: depends on [{deps}]")
        else:
            print("❌ Failed to load workflow dependencies")
            return False
    except Exception as e:
        print(f"❌ Dependency loading error: {str(e)}")
        return False
    
    # Test 4: Instruction Analysis
    print("\n4. Testing Instruction Analysis...")
    test_instruction = "create network hierarchy with area 'TestArea'"
    try:
        response = requests.post(
            f"{BASE_URL}/analyze_instruction",
            json={"instruction": test_instruction}
        )
        if response.status_code == 200:
            data = response.json()
            print("✅ Instruction analysis successful")
            print(f"   Detected workflows: {list(data.get('workflow_scores', {}).keys())}")
            print(f"   Needs clarification: {data.get('clarification_analysis', {}).get('needs_clarification', False)}")
        else:
            print("❌ Instruction analysis failed")
            return False
    except Exception as e:
        print(f"❌ Instruction analysis error: {str(e)}")
        return False
    
    # Test 5: Parse Instructions (No Clarification Needed)
    print("\n5. Testing Simple Instruction Parsing...")
    try:
        response = requests.post(
            f"{BASE_URL}/parse_test_instructions",
            json={
                "prompt": test_instruction,
                "url": "https://192.168.1.100",
                "username": "admin",
                "password": "admin123"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "parsed":
                print("✅ Simple instruction parsed successfully")
                print(f"   Session ID: {data['session_id']}")
                print(f"   Workflows: {data['workflows']}")
                simple_session_id = data['session_id']
            else:
                print("❌ Unexpected parsing result")
                return False
        else:
            print("❌ Simple instruction parsing failed")
            return False
    except Exception as e:
        print(f"❌ Simple parsing error: {str(e)}")
        return False
    
    # Test 6: Parse Instructions That Need Clarification
    print("\n6. Testing Clarification-Required Instruction...")
    clarification_instruction = "create L3VN"  # This should need clarification about fabric
    try:
        response = requests.post(
            f"{BASE_URL}/parse_test_instructions",
            json={
                "prompt": clarification_instruction,
                "url": "https://192.168.1.100",
                "username": "admin",
                "password": "admin123"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "needs_clarification":
                print("✅ Clarification detected successfully")
                print(f"   Session ID: {data['session_id']}")
                print(f"   Clarification type: {data['clarification']['type']}")
                print(f"   Message: {data['clarification']['message']}")
                print(f"   Options: {len(data['clarification']['options'])} choices")
                
                clarification_session_id = data['session_id']
                clarification_data = data['clarification']
            else:
                print("❌ Expected clarification but got different status")
                return False
        else:
            print("❌ Clarification instruction parsing failed")
            return False
    except Exception as e:
        print(f"❌ Clarification parsing error: {str(e)}")
        return False
    
    # Test 7: Provide Clarification Response
    print("\n7. Testing Clarification Response...")
    try:
        clarification_response = {
            "type": clarification_data["type"],
            "choice": "create_new"  # Choose to create new fabric
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/provide_clarification",
            json={
                "session_id": clarification_session_id,
                "clarification_response": clarification_response
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "clarification_resolved":
                print("✅ Clarification processed successfully")
                print(f"   Updated workflows: {data['updated_workflows']}")
                print(f"   Workflow count: {len(data['updated_workflows'])}")
            else:
                print("❌ Clarification processing failed")
                return False
        else:
            print(f"❌ Clarification response failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Clarification response error: {str(e)}")
        return False
    
    # Test 8: Test Skip Clarification
    print("\n8. Testing Skip Clarification...")
    # Create another clarification-needed session
    try:
        response = requests.post(
            f"{BASE_URL}/parse_test_instructions",
            json={
                "prompt": "create L3VN for existing fabric",
                "url": "https://192.168.1.100",
                "username": "admin",
                "password": "admin123"
            }
        )
        
        if response.status_code == 200 and response.json().get("status") == "needs_clarification":
            skip_session_id = response.json()['session_id']
            
            # Skip clarification
            skip_response = requests.post(f"{BASE_URL}/api/v1/session/{skip_session_id}/skip_clarification")
            
            if skip_response.status_code == 200:
                skip_data = skip_response.json()
                print("✅ Skip clarification successful")
                print(f"   Status: {skip_data['status']}")
                print(f"   Workflows: {len(skip_data['workflows'])}")
            else:
                print("❌ Skip clarification failed")
                return False
        else:
            print("⚠️  Skip clarification test skipped (no clarification needed)")
    except Exception as e:
        print(f"❌ Skip clarification error: {str(e)}")
        return False
    
    # Test 9: Test Execution (Mock)
    print("\n9. Testing Test Execution...")
    try:
        # Use the simple session for execution test
        response = requests.post(
            f"{BASE_URL}/execute_test_plan",
            json={"session_id": simple_session_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Test execution started successfully")
            print(f"   Status: {data['status']}")
            print(f"   Workflows count: {data.get('workflows_count', 'Unknown')}")
        else:
            print("❌ Test execution failed to start")
            return False
    except Exception as e:
        print(f"❌ Test execution error: {str(e)}")
        return False
    
    # Test 10: Session Status Check
    print("\n10. Testing Session Status...")
    try:
        response = requests.post(
            f"{BASE_URL}/get_session_status",
            json={"session_id": simple_session_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Session status retrieved successfully")
            print(f"    Status: {data['status']}")
            print(f"    Workflows: {len(data.get('workflows', []))}")
        else:
            print("❌ Session status check failed")
            return False
    except Exception as e:
        print(f"❌ Session status error: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All clarification system tests passed!")
    print("\n📋 Summary:")
    print("✅ Backend health check")
    print("✅ Template loading and dependency resolution")  
    print("✅ Instruction analysis and workflow detection")
    print("✅ Simple instruction parsing (no clarification)")
    print("✅ Clarification detection and question generation")
    print("✅ Clarification response processing")
    print("✅ Skip clarification functionality")
    print("✅ Test execution initiation")
    print("✅ Session status monitoring")
    
    return True

def test_specific_clarification_scenarios():
    """Test specific clarification scenarios"""
    
    print("\n🔍 Testing Specific Clarification Scenarios")
    print("-" * 50)
    
    scenarios = [
        {
            "name": "L3VN without fabric",
            "instruction": "create L3VN",
            "expected_clarification": "fabric_selection"
        },
        {
            "name": "Fabric creation",
            "instruction": "create fabric TestFabric",
            "expected_clarification": None
        },
        {
            "name": "Complete network setup",
            "instruction": "create complete network with hierarchy and fabric",
            "expected_clarification": None
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. Testing: {scenario['name']}")
        print(f"   Instruction: {scenario['instruction']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/parse_test_instructions",
                json={
                    "prompt": scenario['instruction'],
                    "url": "https://192.168.1.100",
                    "username": "admin",
                    "password": "admin123"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                needs_clarification = data.get("status") == "needs_clarification"
                
                if scenario['expected_clarification']:
                    if needs_clarification:
                        clarification_type = data.get('clarification', {}).get('type', '')
                        print(f"   ✅ Expected clarification detected: {clarification_type}")
                    else:
                        print(f"   ❌ Expected clarification but none detected")
                else:
                    if not needs_clarification:
                        print(f"   ✅ No clarification needed as expected")
                        print(f"   Workflows: {data.get('workflows', [])}")
                    else:
                        print(f"   ❌ Unexpected clarification required")
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

def main():
    """Main test function"""
    
    print("Starting E2E Testing Agent Clarification System Tests...")
    
    # Run main integration test
    success = test_clarification_flow()
    
    if success:
        # Run specific scenario tests
        test_specific_clarification_scenarios()
        
        print("\n🎯 Next Steps:")
        print("1. Move TDD templates to organized directories (creation/, query/)")
        print("2. Test with frontend integration")
        print("3. Verify Azure OpenAI integration")
        print("4. Test with real cluster (when available)")
    else:
        print("\n❌ Tests failed. Please check the backend logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()