"""
Playwright Generator Service - Generates Playwright test code from parsed instructions
File: backend/services/playwright_generator.py
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import re

logger = logging.getLogger(__name__)

@dataclass
class TestCase:
    """Generated test case"""
    name: str
    description: str
    code: str
    setup_code: Optional[str] = None
    teardown_code: Optional[str] = None

class PlaywrightGeneratorService:
    """Service for generating Playwright test code"""
    
    def __init__(self):
        self.base_imports = [
            "import { test, expect, Page, BrowserContext } from '@playwright/test';",
            ""
        ]
        
    def generate_test_from_steps(self, 
                                test_name: str, 
                                steps: List[Dict[str, Any]], 
                                base_url: str = None) -> TestCase:
        """Generate a complete Playwright test from steps"""
        
        # Generate test description
        description = f"Generated test: {test_name}"
        
        # Generate test code
        test_code = self._generate_test_function(test_name, steps, base_url)
        
        return TestCase(
            name=test_name,
            description=description,
            code=test_code
        )
    
    def _generate_test_function(self, 
                               test_name: str, 
                               steps: List[Dict[str, Any]], 
                               base_url: str = None) -> str:
        """Generate the main test function"""
        
        code_lines = []
        code_lines.extend(self.base_imports)
        
        # Test function header
        sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', test_name)
        code_lines.append(f"test('{test_name}', async ({{ page }}) => {{")
        
        # Setup
        if base_url:
            code_lines.append(f"  // Navigate to base URL")
            code_lines.append(f"  await page.goto('{base_url}');")
            code_lines.append("")
        
        # Generate steps
        for i, step in enumerate(steps):
            step_code = self._generate_step_code(step, i + 1)
            if step_code:
                code_lines.extend(step_code)
                code_lines.append("")
        
        code_lines.append("});")
        
        return "\n".join(code_lines)
    
    def _generate_step_code(self, step: Dict[str, Any], step_number: int) -> List[str]:
        """Generate code for a single step"""
        code_lines = []
        
        # Add comment with original instruction
        if "raw_instruction" in step:
            code_lines.append(f"  // Step {step_number}: {step['raw_instruction']}")
        
        action = step.get("action", "")
        method = step.get("method", "")
        
        if action == "navigation" or method == "page.goto":
            target = step.get("target", "")
            if target:
                code_lines.append(f"  await page.goto('{target}');")
        
        elif action == "click" or method == "page.click":
            selector = step.get("selector", "")
            if selector:
                code_lines.append(f"  await page.click('{selector}');")
        
        elif action == "fill" or method == "page.fill":
            selector = step.get("selector", "")
            value = step.get("value", "")
            if selector and value:
                code_lines.append(f"  await page.fill('{selector}', '{value}');")
        
        elif action == "wait" or method.startswith("page.wait_for"):
            if method == "page.wait_for_timeout":
                timeout = step.get("timeout", 1000)
                code_lines.append(f"  await page.waitForTimeout({timeout});")
            elif method == "page.wait_for_selector":
                selector = step.get("selector", "")
                if selector:
                    code_lines.append(f"  await page.waitForSelector('{selector}');")
        
        elif action == "assert" or method == "expect":
            condition = step.get("condition", "")
            if condition:
                # Try to convert natural language condition to Playwright assertion
                assertion_code = self._generate_assertion(condition)
                if assertion_code:
                    code_lines.append(f"  {assertion_code}")
        
        return code_lines
    
    def _generate_assertion(self, condition: str) -> str:
        """Generate Playwright assertion from natural language condition"""
        condition = condition.lower().strip()
        
        # Common assertion patterns
        if "page title" in condition and "contains" in condition:
            # Extract expected title
            title_match = re.search(r"contains\s+['\"]([^'\"]+)['\"]", condition)
            if title_match:
                expected_title = title_match.group(1)
                return f"await expect(page).toHaveTitle(/{expected_title}/i);"
        
        elif "url" in condition and "contains" in condition:
            # Extract expected URL part
            url_match = re.search(r"contains\s+['\"]([^'\"]+)['\"]", condition)
            if url_match:
                expected_url = url_match.group(1)
                return f"await expect(page).toHaveURL(/{expected_url}/);"
        
        elif "text" in condition and "visible" in condition:
            # Extract expected text
            text_match = re.search(r"text\s+['\"]([^'\"]+)['\"]", condition)
            if text_match:
                expected_text = text_match.group(1)
                return f"await expect(page.locator('text={expected_text}')).toBeVisible();"
        
        elif "element" in condition and "visible" in condition:
            # Extract selector
            element_match = re.search(r"element\s+['\"]([^'\"]+)['\"]", condition)
            if element_match:
                selector = element_match.group(1)
                return f"await expect(page.locator('{selector}')).toBeVisible();"
        
        # Default assertion
        return f"// TODO: Implement assertion for: {condition}"
    
    def generate_test_suite(self, 
                           suite_name: str, 
                           test_cases: List[TestCase]) -> str:
        """Generate a complete test suite file"""
        
        code_lines = []
        code_lines.extend(self.base_imports)
        
        # Add test.describe block
        code_lines.append(f"test.describe('{suite_name}', () => {{")
        code_lines.append("")
        
        # Add each test case
        for test_case in test_cases:
            # Extract just the test function from the test case code
            test_function = self._extract_test_function(test_case.code)
            if test_function:
                indented_lines = ["  " + line for line in test_function.split("\n")]
                code_lines.extend(indented_lines)
                code_lines.append("")
        
        code_lines.append("});")
        
        return "\n".join(code_lines)
    
    def _extract_test_function(self, test_code: str) -> str:
        """Extract just the test function from complete test code"""
        lines = test_code.split("\n")
        
        # Find the start of the test function
        start_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("test("):
                start_index = i
                break
        
        if start_index == -1:
            return test_code
        
        # Return everything from the test function onwards
        return "\n".join(lines[start_index:])
    
    def add_test_hooks(self, 
                      test_code: str, 
                      setup_code: str = None, 
                      teardown_code: str = None) -> str:
        """Add beforeEach and afterEach hooks to test code"""
        
        lines = test_code.split("\n")
        result_lines = []
        
        # Add imports if not present
        if not any("import" in line for line in lines[:5]):
            result_lines.extend(self.base_imports)
        
        # Find describe block or add one
        describe_start = -1
        for i, line in enumerate(lines):
            if "test.describe(" in line:
                describe_start = i
                break
        
        if describe_start == -1:
            # No describe block, add one
            result_lines.append("test.describe('Generated Tests', () => {")
            
            # Add hooks
            if setup_code:
                result_lines.append("  test.beforeEach(async ({ page }) => {")
                for line in setup_code.split("\n"):
                    if line.strip():
                        result_lines.append(f"    {line}")
                result_lines.append("  });")
                result_lines.append("")
            
            if teardown_code:
                result_lines.append("  test.afterEach(async ({ page }) => {")
                for line in teardown_code.split("\n"):
                    if line.strip():
                        result_lines.append(f"    {line}")
                result_lines.append("  });")
                result_lines.append("")
            
            # Add existing test functions with indentation
            for line in lines:
                if line.strip() and not line.startswith("import"):
                    result_lines.append(f"  {line}")
            
            result_lines.append("});")
        else:
            # Insert hooks into existing describe block
            result_lines.extend(lines[:describe_start + 1])
            
            if setup_code:
                result_lines.append("  test.beforeEach(async ({ page }) => {")
                for line in setup_code.split("\n"):
                    if line.strip():
                        result_lines.append(f"    {line}")
                result_lines.append("  });")
                result_lines.append("")
            
            if teardown_code:
                result_lines.append("  test.afterEach(async ({ page }) => {")
                for line in teardown_code.split("\n"):
                    if line.strip():
                        result_lines.append(f"    {line}")
                result_lines.append("  });")
                result_lines.append("")
            
            result_lines.extend(lines[describe_start + 1:])
        
        return "\n".join(result_lines)
    
    async def initialize(self):
        """Initialize the playwright generator service"""
        logger.info("PlaywrightGeneratorService initialized")
        pass
