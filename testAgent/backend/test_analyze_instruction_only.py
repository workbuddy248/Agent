#!/usr/bin/env python3
"""
Test script for the analyze_instruction_only method
File: test_analyze_instruction_only.py
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.instruction_parser import InstructionParserService
from services.template_manager import TemplateManagerService

async def test_analyze_instruction_only():
    """Test the analyze_instruction_only method"""
    
    # Initialize services
    instruction_parser = InstructionParserService()
    template_manager = TemplateManagerService()
    
    # Initialize template manager
    await template_manager.initialize()
    
    # Test instructions
    test_instructions = [
        "create L3VN for fabric TestFabric",
        "login to cluster with username admin and password admin123",
        "create network hierarchy with area TestArea and building TestBuilding",
        "import devices from devices.csv file",
        "create fabric with BGP ASN 1200",
        "get fabric settings for ProductionFabric"
    ]
    
    print("Testing analyze_instruction_only method...")
    print("=" * 60)
    
    for instruction in test_instructions:
        print(f"\nInstruction: {instruction}")
        print("-" * 40)
        
        try:
            # Analyze the instruction
            result = await instruction_parser.analyze_instruction_only(
                instruction, 
                template_manager=template_manager
            )
            
            print(f"✓ Analysis successful")
            print(f"  Detected parameters: {len(result.get('detected_parameters', {}))}")
            print(f"  Workflow scores: {len(result.get('workflow_scores', {}))}")
            print(f"  Suggested workflow: {result.get('suggested_primary_workflow', 'None')}")
            print(f"  Confidence: {result.get('analysis_confidence', 0.0):.2f}")
            
            # Show top 3 workflows
            workflow_scores = result.get('workflow_scores', {})
            if workflow_scores:
                sorted_workflows = sorted(workflow_scores.items(), key=lambda x: x[1]["score"], reverse=True)
                print(f"  Top workflows:")
                for i, (workflow, score_info) in enumerate(sorted_workflows[:3]):
                    print(f"    {i+1}. {workflow}: {score_info['score']:.2f}")
            
            # Show detected parameters
            detected_params = result.get('detected_parameters', {})
            if detected_params:
                print(f"  Parameters:")
                for param, value in detected_params.items():
                    print(f"    {param}: {value}")
            
        except Exception as e:
            print(f"✗ Analysis failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_analyze_instruction_only())
