#!/usr/bin/env python3
"""
Test script to verify parse_instruction fix
File: test_parse_instruction_fix.py
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.instruction_parser import InstructionParserService

async def test_parse_instruction_with_config():
    """Test the parse_instruction method with cluster configuration"""
    
    # Initialize service
    instruction_parser = InstructionParserService()
    
    # Test data similar to what the UI sends
    test_instruction = "test login to the cluster"
    cluster_url = "https://172.27.248.237:443/"
    username = "admin1"
    password = "password123"
    
    print("Testing parse_instruction method with cluster config...")
    print("=" * 60)
    print(f"Instruction: {test_instruction}")
    print(f"Cluster URL: {cluster_url}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print("-" * 60)
    
    try:
        # Test the method call that was failing
        result = await instruction_parser.parse_instruction(
            instruction=test_instruction,
            cluster_url=cluster_url,
            username=username,
            password=password
        )
        
        print("✓ parse_instruction method executed successfully!")
        print(f"Result type: {type(result)}")
        print(f"Workflows found: {result.workflows}")
        print(f"Parameters found: {len(result.parameters)}")
        
        # Show the parameters
        print("\nParameters:")
        for key, value in result.parameters.items():
            print(f"  {key}: {value}")
        
        # Show the analysis
        print(f"\nAnalysis confidence: {result.analysis.get('analysis_confidence', 'N/A')}")
        print(f"Suggested primary workflow: {result.analysis.get('suggested_primary_workflow', 'N/A')}")
        
    except Exception as e:
        print(f"✗ parse_instruction method failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_parse_instruction_with_config())