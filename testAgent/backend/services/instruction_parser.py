"""
Instruction Parser Service - Parses natural language instructions into structured test workflows
File: backend/services/instruction_parser.py
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class InstructionType(str, Enum):
    """Types of instructions that can be parsed"""
    NAVIGATION = "navigation"
    CLICK = "click"
    FILL = "fill"
    WAIT = "wait"
    ASSERT = "assert"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    WORKFLOW = "workflow"

@dataclass
class ParsedInstruction:
    """A parsed instruction with metadata"""
    type: InstructionType
    action: str
    target: Optional[str] = None
    value: Optional[str] = None
    condition: Optional[str] = None
    parameters: Dict[str, Any] = None
    confidence: float = 1.0
    raw_text: str = ""

class InstructionParserService:
    """Service for parsing natural language instructions into structured test steps"""
    
    def __init__(self):
        self.patterns = self._load_patterns()
        
    def _load_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load regex patterns for instruction parsing"""
        return {
            "navigation": [
                {
                    "pattern": r"(?:navigate|go|visit|open)\s+(?:to\s+)?(?:the\s+)?(.+)",
                    "confidence": 0.9
                },
                {
                    "pattern": r"(?:load|access)\s+(?:the\s+)?(.+)",
                    "confidence": 0.8
                }
            ],
            "click": [
                {
                    "pattern": r"(?:click|tap|press)\s+(?:on\s+)?(?:the\s+)?(.+)",
                    "confidence": 0.9
                },
                {
                    "pattern": r"(?:select|choose)\s+(?:the\s+)?(.+)",
                    "confidence": 0.8
                }
            ],
            "fill": [
                {
                    "pattern": r"(?:fill|enter|type|input)\s+['\"]([^'\"]+)['\"]?\s+(?:in|into)\s+(?:the\s+)?(.+)",
                    "confidence": 0.9
                },
                {
                    "pattern": r"(?:set|populate)\s+(?:the\s+)?(.+?)\s+(?:to|with)\s+['\"]([^'\"]+)['\"]?",
                    "confidence": 0.8
                }
            ],
            "wait": [
                {
                    "pattern": r"(?:wait|pause)\s+(?:for\s+)?(?:(\d+)\s+)?(?:seconds?|ms|milliseconds?)?",
                    "confidence": 0.9
                },
                {
                    "pattern": r"(?:wait|pause)\s+(?:for\s+)?(?:the\s+)?(.+?)\s+(?:to\s+)?(?:appear|load|be\s+visible)",
                    "confidence": 0.8
                }
            ],
            "assert": [
                {
                    "pattern": r"(?:verify|check|assert|confirm)\s+(?:that\s+)?(.+)",
                    "confidence": 0.9
                },
                {
                    "pattern": r"(?:ensure|make\s+sure)\s+(?:that\s+)?(.+)",
                    "confidence": 0.8
                }
            ]
        }
    
    def parse_instruction(self, instruction: str) -> Optional[ParsedInstruction]:
        """Parse a single instruction into a structured format"""
        instruction = instruction.strip().lower()
        
        if not instruction:
            return None
            
        best_match = None
        highest_confidence = 0.0
        
        for instruction_type, patterns in self.patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                base_confidence = pattern_info["confidence"]
                
                match = re.search(pattern, instruction, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    
                    parsed = ParsedInstruction(
                        type=InstructionType(instruction_type),
                        action=instruction_type,
                        raw_text=instruction,
                        confidence=base_confidence
                    )
                    
                    # Extract target and value based on instruction type
                    if instruction_type == "navigation" and groups:
                        parsed.target = groups[0].strip()
                    elif instruction_type == "click" and groups:
                        parsed.target = groups[0].strip()
                    elif instruction_type == "fill" and len(groups) >= 2:
                        parsed.value = groups[0].strip()
                        parsed.target = groups[1].strip()
                    elif instruction_type == "wait":
                        if groups and groups[0]:
                            if groups[0].isdigit():
                                parsed.value = groups[0]
                            else:
                                parsed.target = groups[0].strip()
                    elif instruction_type == "assert" and groups:
                        parsed.condition = groups[0].strip()
                    
                    if base_confidence > highest_confidence:
                        highest_confidence = base_confidence
                        best_match = parsed
        
        return best_match
    
    def parse_instructions(self, instructions: List[str]) -> List[ParsedInstruction]:
        """Parse multiple instructions"""
        parsed_instructions = []
        
        for instruction in instructions:
            parsed = self.parse_instruction(instruction)
            if parsed:
                parsed_instructions.append(parsed)
            else:
                logger.warning(f"Could not parse instruction: {instruction}")
        
        return parsed_instructions
    
    def extract_workflow_parameters(self, instructions: List[str]) -> Dict[str, Any]:
        """Extract workflow parameters from instructions"""
        parameters = {
            "base_url": None,
            "credentials": {},
            "test_data": {},
            "timeouts": {},
            "browser_config": {}
        }
        
        # Look for URL patterns
        url_pattern = r"https?://[^\s]+"
        for instruction in instructions:
            url_match = re.search(url_pattern, instruction)
            if url_match and not parameters["base_url"]:
                parameters["base_url"] = url_match.group()
        
        return parameters
    
    def generate_test_steps(self, parsed_instructions: List[ParsedInstruction]) -> List[Dict[str, Any]]:
        """Generate Playwright test steps from parsed instructions"""
        test_steps = []
        
        for instruction in parsed_instructions:
            step = {
                "action": instruction.action,
                "confidence": instruction.confidence,
                "raw_instruction": instruction.raw_text
            }
            
            if instruction.type == InstructionType.NAVIGATION:
                step.update({
                    "method": "page.goto",
                    "target": instruction.target,
                    "params": {"wait_until": "networkidle"}
                })
            
            elif instruction.type == InstructionType.CLICK:
                step.update({
                    "method": "page.click",
                    "selector": self._target_to_selector(instruction.target),
                    "params": {}
                })
            
            elif instruction.type == InstructionType.FILL:
                step.update({
                    "method": "page.fill",
                    "selector": self._target_to_selector(instruction.target),
                    "value": instruction.value,
                    "params": {}
                })
            
            elif instruction.type == InstructionType.WAIT:
                if instruction.value and instruction.value.isdigit():
                    step.update({
                        "method": "page.wait_for_timeout",
                        "timeout": int(instruction.value) * 1000,
                        "params": {}
                    })
                elif instruction.target:
                    step.update({
                        "method": "page.wait_for_selector",
                        "selector": self._target_to_selector(instruction.target),
                        "params": {"state": "visible"}
                    })
            
            elif instruction.type == InstructionType.ASSERT:
                step.update({
                    "method": "expect",
                    "condition": instruction.condition,
                    "params": {}
                })
            
            test_steps.append(step)
        
        return test_steps
    
    def _target_to_selector(self, target: str) -> str:
        """Convert natural language target to CSS selector"""
        if not target:
            return ""
        
        target = target.lower().strip()
        
        # Common element mappings
        element_mappings = {
            "submit button": "button[type='submit']",
            "login button": "button:has-text('login')",
            "username field": "input[name='username'], input[id='username']",
            "password field": "input[type='password']",
            "email field": "input[type='email']",
            "search box": "input[type='search']",
            "menu": "nav, .menu, [role='menu']",
            "header": "header, .header",
            "footer": "footer, .footer"
        }
        
        # Check for exact matches first
        if target in element_mappings:
            return element_mappings[target]
        
        # Try to generate selector based on common patterns
        if "button" in target:
            # Extract button text
            button_text = target.replace("button", "").strip()
            if button_text:
                return f"button:has-text('{button_text}')"
            return "button"
        
        elif "link" in target:
            link_text = target.replace("link", "").strip()
            if link_text:
                return f"a:has-text('{link_text}')"
            return "a"
        
        elif "field" in target or "input" in target:
            field_name = target.replace("field", "").replace("input", "").strip()
            if field_name:
                return f"input[name='{field_name}'], input[id='{field_name}']"
            return "input"
        
        # Default: use text content
        return f":has-text('{target}')"
    
    async def initialize(self):
        """Initialize the instruction parser service"""
        logger.info("InstructionParserService initialized")
        pass
