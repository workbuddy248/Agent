#!/usr/bin/env python3
"""
Test script to verify template loading fix
File: test_template_fix.py
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_fixed_template_loading():
    """Test the fixed template loading"""
    print("Testing fixed template loading...")
    print("=" * 50)
    
    try:
        from services.template_manager import TemplateManagerService
        
        # Create and initialize template manager
        template_manager = TemplateManagerService()
        await template_manager.initialize()
        
        # Check results
        total_templates = len(template_manager.templates)
        print(f"✓ Templates loaded: {total_templates}")
        
        # Show by type
        creation_count = len(template_manager.templates_by_type.get('creation', []))
        query_count = len(template_manager.templates_by_type.get('query', []))
        modification_count = len(template_manager.templates_by_type.get('modification', []))
        
        print(f"  Creation: {creation_count}")
        print(f"  Query: {query_count}")
        print(f"  Modification: {modification_count}")
        
        # List all loaded templates
        print(f"\nLoaded template details:")
        for name, template in template_manager.templates.items():
            print(f"  - {name} ({template.workflow_type.value}) - {len(template.parameters)} params")
        
        # Expected: 5 creation + 1 query = 6 total
        if total_templates >= 6 and creation_count >= 5 and query_count >= 1:
            print("\n🎉 SUCCESS: All templates loaded correctly!")
            return True
        else:
            print(f"\n❌ ISSUE: Expected 6 templates (5 creation + 1 query), got {total_templates}")
            return False
            
    except Exception as e:
        print(f"❌ Template loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_fixed_template_loading())