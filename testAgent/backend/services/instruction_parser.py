"""
Enhanced Instruction Parser Service - Parses natural language instructions into structured test workflows
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

@dataclass
class ParsedInstructionResult:
    """Result of parsing instruction with cluster configuration"""
    workflows: List[str]
    parameters: Dict[str, Any]
    analysis: Dict[str, Any]

class InstructionParserService:
    """Service for parsing natural language instructions into structured test steps"""
    
    def __init__(self):
        self.patterns = self._load_patterns()
        self.workflow_keywords = self._load_workflow_keywords()
        self.parameter_patterns = self._load_parameter_patterns()
        
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
    
    def _load_workflow_keywords(self) -> Dict[str, List[str]]:
        """Load workflow keywords for matching instructions to templates"""
        return {
            "login_flow": [
                "login", "log in", "sign in", "authenticate", "credentials", 
                "username", "password", "access", "home page"
            ],
            "network_hierarchy_creation": [
                "network hierarchy", "create area", "create building", "hierarchy",
                "area", "building", "site", "global", "design"
            ],
            "inventory_workflow": [
                "inventory", "import devices", "add device", "provision device",
                "device", "import", "csv", "file", "upload"
            ],
            "fabric_creation": [
                "fabric", "create fabric", "fabric site", "sd access",
                "device group", "border", "leaf", "spine", "bgp"
            ],
            "l3vn_management": [
                "l3vn", "l3 vn", "virtual network", "vn", "overlay",
                "anycast", "ip pool", "vrf"
            ],
            "fabric_settings": [
                "fabric settings", "settings", "configuration", "fabric config",
                "get fabric", "view fabric", "fabric details"
            ]
        }
    
    def _load_parameter_patterns(self) -> Dict[str, str]:
        """Load parameter extraction patterns"""
        return {
            "cluster_url": r"(?:cluster|url|ip|address)[\s:]*['\"]?(https?://[^\s'\"]+|(?:\d{1,3}\.){3}\d{1,3})['\"]?",
            "cluster_ip": r"(?:ip|address)[\s:]*['\"]?((?:\d{1,3}\.){3}\d{1,3})['\"]?",
            "username": r"(?:username|user|login)[\s:]*['\"]?([a-zA-Z0-9_]+)['\"]?",
            "password": r"(?:password|pwd|pass)[\s:]*['\"]?([^\s'\"]+)['\"]?",
            "fabric_name": r"(?:fabric|fabric[\s_]name)[\s:]*['\"]?([a-zA-Z0-9_\-\s]+)['\"]?",
            "area_name": r"(?:area|area[\s_]name)[\s:]*['\"]?([a-zA-Z0-9_\-\s]+)['\"]?",
            "building_name": r"(?:building|building[\s_]name|site)[\s:]*['\"]?([a-zA-Z0-9_\-\s]+)['\"]?",
            "file_name": r"(?:file|filename|csv)[\s:]*['\"]?([a-zA-Z0-9_\-\.]+)['\"]?",
            "device_count": r"(?:(\d+)\s+devices?|devices?\s+(\d+))",
            "l3vn_count": r"(?:(\d+)\s+l3vn|l3vn\s+(\d+))",
            "bgp_asn": r"(?:bgp|asn)[\s:]*['\"]?(\d+)['\"]?",
            "timeout": r"(?:timeout|wait)[\s:]*['\"]?(\d+)['\"]?"
        }
    
    async def parse_instruction(self, instruction: str, cluster_url: str = None, 
                              username: str = None, password: str = None) -> ParsedInstructionResult:
        """
        Parse instruction with cluster configuration and return workflows and parameters
        
        Args:
            instruction: Natural language instruction to parse
            cluster_url: Cluster URL (optional)
            username: Username for cluster access (optional)
            password: Password for cluster access (optional)
            
        Returns:
            ParsedInstructionResult with workflows and parameters
        """
        logger.info(f"Parsing instruction with config: {instruction[:100]}...")
        
        # Use analyze_instruction_only to get workflow analysis
        analysis_result = await self.analyze_instruction_only(instruction)
        
        # Extract workflows from analysis (get top scoring workflows)
        workflow_scores = analysis_result.get("workflow_scores", {})
        detected_parameters = analysis_result.get("detected_parameters", {})
        
        # Get primary workflows based on scores
        workflows = []
        if workflow_scores:
            # Sort by score and take workflows with score > 0.3
            sorted_workflows = sorted(workflow_scores.items(), key=lambda x: x[1]["score"], reverse=True)
            workflows = [workflow for workflow, score_info in sorted_workflows if score_info["score"] > 0.3]
        
        # If no workflows found, try to infer from instruction
        if not workflows:
            workflows = self._infer_workflows_from_instruction(instruction)
        
        # Combine detected parameters with provided cluster configuration
        combined_parameters = detected_parameters.copy()
        
        # Add cluster configuration parameters
        if cluster_url:
            combined_parameters["cluster_url"] = cluster_url
        if username:
            combined_parameters["username"] = username
        if password:
            combined_parameters["password"] = password
        
        # Extract cluster IP from URL if not already detected
        if cluster_url and "cluster_ip" not in combined_parameters:
            ip_match = re.search(r"(?:https?://)?([0-9]{1,3}(?:\.[0-9]{1,3}){3})", cluster_url)
            if ip_match:
                combined_parameters["cluster_ip"] = ip_match.group(1)
        
        # Create result object with expected structure
        result = ParsedInstructionResult(
            workflows=workflows,
            parameters=combined_parameters,
            analysis=analysis_result
        )
        
        logger.info(f"Parsed instruction: {len(workflows)} workflows, {len(combined_parameters)} parameters")
        return result
    
    def _infer_workflows_from_instruction(self, instruction: str) -> List[str]:
        """Infer workflows from instruction when no high-scoring matches found"""
        instruction_lower = instruction.lower()
        
        # Simple keyword-based inference
        inferred_workflows = []
        
        # Check for login-related keywords
        if any(keyword in instruction_lower for keyword in ["login", "log in", "sign in", "authenticate"]):
            inferred_workflows.append("login_flow")
        
        # Check for creation-related keywords
        if any(keyword in instruction_lower for keyword in ["create", "add", "build", "make"]):
            if "hierarchy" in instruction_lower or "area" in instruction_lower or "building" in instruction_lower:
                inferred_workflows.append("network_hierarchy_creation")
            elif "fabric" in instruction_lower:
                inferred_workflows.append("fabric_creation")
            elif "l3vn" in instruction_lower or "vn" in instruction_lower:
                inferred_workflows.append("l3vn_management")
        
        # Check for import/inventory keywords
        if any(keyword in instruction_lower for keyword in ["import", "inventory", "device"]):
            inferred_workflows.append("inventory_workflow")
        
        # Default to login if no specific workflow detected
        if not inferred_workflows:
            inferred_workflows.append("login_flow")
        
        return inferred_workflows
    
    def parse_single_instruction(self, instruction: str) -> Optional[ParsedInstruction]:
        """Parse a single instruction into a structured format (original method)"""
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

    async def analyze_instruction_only(self, instruction: str, template_manager=None) -> Dict[str, Any]:
        """
        Analyze instruction and match against available TDD templates without execution
        
        Args:
            instruction: Natural language instruction to analyze
            template_manager: Optional TemplateManagerService instance for template matching
            
        Returns:
            Dictionary containing workflow_scores and detected_parameters
        """
        logger.info(f"Analyzing instruction: {instruction[:100]}...")
        
        # Extract parameters from instruction
        detected_parameters = await self._extract_parameters_from_instruction(instruction)
        
        # Score workflows against instruction
        workflow_scores = await self._score_workflows_against_instruction(
            instruction, template_manager
        )
        
        # Additional analysis
        instruction_complexity = self._analyze_instruction_complexity(instruction)
        
        result = {
            "workflow_scores": workflow_scores,
            "detected_parameters": detected_parameters,
            "instruction_complexity": instruction_complexity,
            "analysis_confidence": self._calculate_overall_confidence(workflow_scores),
            "suggested_primary_workflow": self._get_highest_scoring_workflow(workflow_scores),
            "parameter_extraction_summary": {
                "total_parameters": len(detected_parameters),
                "required_parameters": list(detected_parameters.keys()),
                "missing_common_parameters": self._identify_missing_common_parameters(detected_parameters)
            }
        }
        
        logger.info(f"Analysis complete. Found {len(workflow_scores)} potential workflows, {len(detected_parameters)} parameters")
        return result
    
    async def _extract_parameters_from_instruction(self, instruction: str) -> Dict[str, Any]:
        """Extract parameters from instruction using regex patterns"""
        detected_parameters = {}
        
        # Apply parameter extraction patterns
        for param_name, pattern in self.parameter_patterns.items():
            matches = re.findall(pattern, instruction, re.IGNORECASE)
            if matches:
                # Handle different match patterns
                if isinstance(matches[0], tuple):
                    # Multiple capture groups - take first non-empty
                    value = next((m for m in matches[0] if m), None)
                else:
                    value = matches[0]
                
                if value:
                    detected_parameters[param_name] = value.strip()
        
        # Extract quoted strings that might be names/values
        quoted_strings = re.findall(r"['\"]([^'\"]+)['\"]", instruction)
        if quoted_strings:
            detected_parameters["quoted_values"] = quoted_strings
        
        # Extract numeric values
        numbers = re.findall(r"\b(\d+)\b", instruction)
        if numbers:
            detected_parameters["numeric_values"] = [int(n) for n in numbers]
        
        # Clean up and standardize parameter names
        detected_parameters = self._clean_and_standardize_parameters(detected_parameters)
        
        return detected_parameters
    
    def _clean_and_standardize_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize extracted parameters"""
        cleaned_params = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # Remove quotes and extra whitespace
                cleaned_value = value.strip().strip('\'"')
                if cleaned_value:
                    cleaned_params[key] = cleaned_value
            elif isinstance(value, list) and value:
                cleaned_params[key] = value
            elif isinstance(value, (int, float)):
                cleaned_params[key] = value
        
        return cleaned_params
    
    async def _score_workflows_against_instruction(self, instruction: str, template_manager=None) -> Dict[str, Dict[str, Any]]:
        """Score available workflows against the instruction"""
        workflow_scores = {}
        
        # Get available workflows from template manager if provided
        available_workflows = []
        if template_manager:
            try:
                templates = await template_manager.list_available_templates()
                available_workflows = [t["name"] for t in templates]
            except Exception as e:
                logger.warning(f"Could not get templates from template manager: {e}")
                # Fallback to predefined workflows
                available_workflows = list(self.workflow_keywords.keys())
        else:
            available_workflows = list(self.workflow_keywords.keys())
        
        # Score each workflow
        for workflow_name in available_workflows:
            score_info = self._calculate_workflow_score(instruction, workflow_name)
            if score_info["score"] > 0:
                workflow_scores[workflow_name] = score_info
        
        return workflow_scores
    
    def _calculate_workflow_score(self, instruction: str, workflow_name: str) -> Dict[str, Any]:
        """Calculate score for a specific workflow against instruction"""
        instruction_lower = instruction.lower()
        keywords = self.workflow_keywords.get(workflow_name, [])
        
        score = 0.0
        matched_keywords = []
        
        # Keyword matching with different weights
        for keyword in keywords:
            if keyword.lower() in instruction_lower:
                # Exact match gets higher score
                if keyword.lower() == instruction_lower.strip():
                    score += 1.0
                # Partial match with word boundaries
                elif re.search(r'\b' + re.escape(keyword.lower()) + r'\b', instruction_lower):
                    score += 0.8
                # Substring match
                else:
                    score += 0.3
                
                matched_keywords.append(keyword)
        
        # Normalize score by number of keywords
        if keywords:
            score = score / len(keywords)
        
        # Boost score for workflows that match instruction patterns
        pattern_boost = self._get_pattern_boost(instruction, workflow_name)
        score += pattern_boost
        
        # Cap score at 1.0
        score = min(score, 1.0)
        
        return {
            "score": score,
            "matched_keywords": matched_keywords,
            "keyword_count": len(matched_keywords),
            "total_keywords": len(keywords),
            "pattern_boost": pattern_boost,
            "confidence": score
        }
    
    def _get_pattern_boost(self, instruction: str, workflow_name: str) -> float:
        """Get pattern-based boost for workflow scoring"""
        instruction_lower = instruction.lower()
        
        # Pattern-based boosts
        pattern_boosts = {
            "login_flow": [
                (r"log\s*in", 0.3),
                (r"sign\s*in", 0.3),
                (r"authenticate", 0.2),
                (r"home\s*page", 0.2)
            ],
            "network_hierarchy_creation": [
                (r"create.*(?:area|building|hierarchy)", 0.4),
                (r"network\s*hierarchy", 0.5),
                (r"design.*(?:area|building)", 0.3)
            ],
            "inventory_workflow": [
                (r"import.*device", 0.4),
                (r"add.*device", 0.3),
                (r"provision.*device", 0.4),
                (r"csv|file|upload", 0.2)
            ],
            "fabric_creation": [
                (r"create.*fabric", 0.5),
                (r"fabric.*site", 0.4),
                (r"sd\s*access", 0.3),
                (r"device\s*group", 0.3)
            ],
            "l3vn_management": [
                (r"create.*l3vn", 0.5),
                (r"l3\s*vn", 0.4),
                (r"virtual\s*network", 0.3),
                (r"\d+\s*l3vn", 0.3)
            ],
            "fabric_settings": [
                (r"get.*fabric", 0.4),
                (r"view.*fabric", 0.3),
                (r"fabric.*settings", 0.5),
                (r"fabric.*details", 0.3)
            ]
        }
        
        boost = 0.0
        if workflow_name in pattern_boosts:
            for pattern, boost_value in pattern_boosts[workflow_name]:
                if re.search(pattern, instruction_lower):
                    boost += boost_value
        
        return min(boost, 0.5)  # Cap boost at 0.5
    
    def _analyze_instruction_complexity(self, instruction: str) -> Dict[str, Any]:
        """Analyze the complexity of the instruction"""
        word_count = len(instruction.split())
        
        # Count different types of actions
        action_indicators = {
            "creation": len(re.findall(r"\b(?:create|add|build|make|new)\b", instruction, re.IGNORECASE)),
            "navigation": len(re.findall(r"\b(?:go|navigate|visit|open)\b", instruction, re.IGNORECASE)),
            "interaction": len(re.findall(r"\b(?:click|select|choose|enter|fill)\b", instruction, re.IGNORECASE)),
            "verification": len(re.findall(r"\b(?:verify|check|confirm|ensure)\b", instruction, re.IGNORECASE))
        }
        
        # Determine complexity level
        complexity_score = sum(action_indicators.values())
        if word_count > 20 or complexity_score > 5:
            complexity_level = "high"
        elif word_count > 10 or complexity_score > 2:
            complexity_level = "medium"
        else:
            complexity_level = "low"
        
        return {
            "word_count": word_count,
            "action_indicators": action_indicators,
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "estimated_steps": max(complexity_score, 1)
        }
    
    def _calculate_overall_confidence(self, workflow_scores: Dict[str, Dict[str, Any]]) -> float:
        """Calculate overall confidence in the analysis"""
        if not workflow_scores:
            return 0.0
        
        scores = [ws["score"] for ws in workflow_scores.values()]
        max_score = max(scores)
        
        # High confidence if there's a clear winner
        if max_score > 0.7:
            return 0.9
        elif max_score > 0.5:
            return 0.7
        elif max_score > 0.3:
            return 0.5
        else:
            return 0.3
    
    def _get_highest_scoring_workflow(self, workflow_scores: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """Get the workflow with the highest score"""
        if not workflow_scores:
            return None
        
        return max(workflow_scores.items(), key=lambda x: x[1]["score"])[0]
    
    def _identify_missing_common_parameters(self, detected_parameters: Dict[str, Any]) -> List[str]:
        """Identify commonly needed parameters that are missing"""
        common_parameters = [
            "cluster_url", "cluster_ip", "username", "password"
        ]
        
        missing = []
        for param in common_parameters:
            if param not in detected_parameters:
                missing.append(param)
        
        return missing
    
    def parse_instructions(self, instructions: List[str]) -> List[ParsedInstruction]:
        """Parse multiple instructions"""
        parsed_instructions = []
        
        for instruction in instructions:
            parsed = self.parse_single_instruction(instruction)
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