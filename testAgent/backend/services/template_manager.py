"""
Enhanced Template Manager Service - Handles loading and customization of TDD.md templates with metadata
File: backend/services/template_manager.py
"""

import os
import re
import yaml
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from core.config import settings

logger = logging.getLogger(__name__)

class WorkflowType(str, Enum):
    """Workflow type enumeration"""
    CREATION = "creation"
    QUERY = "query"
    MODIFICATION = "modification"

@dataclass
class WorkflowMetadata:
    """Workflow metadata from TDD template"""
    workflow_type: WorkflowType
    dependencies: List[str] = field(default_factory=list)
    can_run_standalone: bool = True
    requires_existing_fabric: bool = False
    estimated_duration: int = 60
    required_parameters: List[str] = field(default_factory=list)
    optional_parameters: List[str] = field(default_factory=list)

@dataclass
class TDDTemplate:
    """Enhanced TDD template with metadata and content"""
    name: str
    workflow_type: WorkflowType
    metadata: WorkflowMetadata
    content: str
    test_cases: List[str]
    parameters: List[str]
    file_path: str
    last_modified: float

class TemplateManagerService:
    """Enhanced service for managing TDD templates with metadata parsing"""
    
    def __init__(self):
        self.templates: Dict[str, TDDTemplate] = {}
        self.templates_by_type: Dict[WorkflowType, List[str]] = {
            WorkflowType.CREATION: [],
            WorkflowType.QUERY: [],
            WorkflowType.MODIFICATION: []
        }
        self.dependency_graph: Dict[str, List[str]] = {}
        self.playwright_prompt_template: Optional[str] = None
        
    async def initialize(self):
        """Initialize template manager and load all templates with metadata"""
        logger.info("Initializing Enhanced Template Manager Service...")
        
        # Load TDD templates with metadata
        await self._load_tdd_templates_with_metadata()
        
        # Build dependency graph
        await self._build_dependency_graph()
        
        # Load playwright prompt template
        await self._load_playwright_prompt_template()
        
        logger.info(f"Loaded {len(self.templates)} TDD templates with metadata")
        logger.info(f"Templates by type: {dict((k.value, len(v)) for k, v in self.templates_by_type.items())}")

    async def _load_tdd_templates_with_metadata(self):
        """Load all TDD.md templates with metadata parsing"""
        
        templates_base_path = Path(settings.TEMPLATES_DIR)
        
        if not templates_base_path.exists():
            logger.warning(f"Templates directory not found: {templates_base_path}")
            await self._create_sample_templates_with_metadata(templates_base_path)
            return
        
        # Load templates from organized directories
        workflow_dirs = {
            WorkflowType.CREATION: templates_base_path / "creation",
            WorkflowType.QUERY: templates_base_path / "query", 
            WorkflowType.MODIFICATION: templates_base_path / "modification"
        }
        
        # Create directories if they don't exist
        for workflow_type, dir_path in workflow_dirs.items():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Load templates from each directory
        total_loaded = 0
        for workflow_type, dir_path in workflow_dirs.items():
            # Match both .TDD.md and .tdd.md files
            tdd_files_upper = list(dir_path.glob("*.TDD.md"))
            tdd_files_lower = list(dir_path.glob("*.tdd.md"))
            tdd_files = tdd_files_upper + tdd_files_lower
            
            logger.info(f"Found {len(tdd_files)} template files in {dir_path} (.TDD.md: {len(tdd_files_upper)}, .tdd.md: {len(tdd_files_lower)})")
            
            for file_path in tdd_files:
                try:
                    await self._load_single_template_with_metadata(file_path, workflow_type)
                    total_loaded += 1
                except Exception as e:
                    logger.error(f"Failed to load template {file_path}: {str(e)}")
        
        if total_loaded == 0:
            logger.warning("No TDD.md template files found, creating samples...")
            await self._create_sample_templates_with_metadata(templates_base_path)

    async def _load_single_template_with_metadata(self, file_path: Path, expected_type: WorkflowType):
        """Load a single TDD template file with metadata parsing"""
        
        # Extract template name - handle both .TDD.md and .tdd.md extensions
        if file_path.name.endswith('.TDD.md'):
            template_name = file_path.stem.replace(".TDD", "")
        elif file_path.name.endswith('.tdd.md'):
            template_name = file_path.stem.replace(".tdd", "")
        else:
            template_name = file_path.stem
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse metadata and content - handle files without metadata section
            try:
                metadata, clean_content, test_cases = self._parse_template_content(content)
            except ValueError as e:
                logger.warning(f"Template {template_name} has no metadata section, using defaults: {e}")
                # Create default metadata for templates without metadata section
                metadata = WorkflowMetadata(
                    workflow_type=expected_type,
                    dependencies=[],
                    can_run_standalone=True,
                    requires_existing_fabric=False,
                    estimated_duration=60,
                    required_parameters=[],
                    optional_parameters=[]
                )
                clean_content = content
                test_cases = self._extract_test_cases(content)
            
            # Validate workflow type matches directory
            if metadata.workflow_type != expected_type:
                logger.warning(f"Template {template_name} type mismatch: expected {expected_type}, got {metadata.workflow_type}")
                # Override with expected type from directory
                metadata.workflow_type = expected_type
            
            # Extract parameter placeholders from content
            parameters = self._extract_template_parameters(clean_content)
            
            # Create template object
            template = TDDTemplate(
                name=template_name,
                workflow_type=metadata.workflow_type,
                metadata=metadata,
                content=clean_content,
                test_cases=test_cases,
                parameters=parameters,
                file_path=str(file_path),
                last_modified=file_path.stat().st_mtime
            )
            
            # Store template
            self.templates[template_name] = template
            self.templates_by_type[metadata.workflow_type].append(template_name)
            
            logger.info(f"Loaded template: {template_name} ({metadata.workflow_type.value}) with {len(parameters)} parameters")
            
        except Exception as e:
            logger.error(f"Error loading template {file_path}: {str(e)}")
            raise

    def _parse_template_content(self, content: str) -> Tuple[WorkflowMetadata, str, List[str]]:
        """Parse template content to extract metadata and test cases"""
        
        # Define both metadata patterns at the beginning
        metadata_pattern = r'## Workflow Metadata\s*\n(.*?)\n(?=##|\Z)'
        metadata_pattern_alt = r'# Workflow Metadata\s*\n(.*?)\n(?=#|\Z)'
        
        # Try to find metadata section
        metadata_match = re.search(metadata_pattern, content, re.DOTALL)
        used_pattern = metadata_pattern
        
        if not metadata_match:
            # Try alternative metadata pattern
            metadata_match = re.search(metadata_pattern_alt, content, re.DOTALL)
            used_pattern = metadata_pattern_alt
            
            if not metadata_match:
                raise ValueError("No workflow metadata section found in template")
        
        metadata_text = metadata_match.group(1).strip()
        
        # Parse metadata as YAML-like format
        metadata = self._parse_metadata_yaml(metadata_text)
        
        # Extract test cases
        test_cases = self._extract_test_cases(content)
        
        # Remove metadata section from content for clean template (using the pattern that was found)
        clean_content = re.sub(used_pattern, '', content, flags=re.DOTALL).strip()
        
        return metadata, clean_content, test_cases

    def _parse_metadata_yaml(self, metadata_text: str) -> WorkflowMetadata:
        """Parse metadata text as YAML-like format with fallback defaults"""
        
        try:
            # Parse as YAML
            metadata_dict = yaml.safe_load(metadata_text)
            
            if not metadata_dict:
                # Empty metadata, use defaults
                return self._create_default_metadata()
            
            # Extract parameters section
            parameters_section = metadata_dict.get('parameters', {})
            required_params = parameters_section.get('required', [])
            optional_params = parameters_section.get('optional', [])
            
            # Create metadata object with defaults for missing fields
            metadata = WorkflowMetadata(
                workflow_type=WorkflowType(metadata_dict.get('workflow_type', 'creation')),
                dependencies=metadata_dict.get('dependencies', []),
                can_run_standalone=metadata_dict.get('can_run_standalone', True),
                requires_existing_fabric=metadata_dict.get('requires_existing_fabric', False),
                estimated_duration=metadata_dict.get('estimated_duration', 60),
                required_parameters=required_params,
                optional_parameters=optional_params
            )
            
            return metadata
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing metadata YAML: {str(e)}")
            logger.warning("Using default metadata due to YAML parsing error")
            return self._create_default_metadata()
        except Exception as e:
            logger.error(f"Unexpected error parsing metadata: {str(e)}")
            return self._create_default_metadata()

    def _create_default_metadata(self) -> WorkflowMetadata:
        """Create default metadata for templates without metadata section"""
        return WorkflowMetadata(
            workflow_type=WorkflowType.CREATION,  # Will be overridden by directory
            dependencies=[],
            can_run_standalone=True,
            requires_existing_fabric=False,
            estimated_duration=60,
            required_parameters=[],
            optional_parameters=[]
        )

    def _infer_metadata_from_content(self, content: str, template_name: str) -> WorkflowMetadata:
        """Infer metadata from template content when no metadata section exists"""
        
        content_lower = content.lower()
        
        # Infer dependencies based on content
        dependencies = []
        if "login" in content_lower and template_name != "login_flow":
            dependencies.append("login_flow")
        if "hierarchy" in content_lower or "area" in content_lower:
            dependencies.append("network_hierarchy_creation")
        if "inventory" in content_lower or "device" in content_lower:
            dependencies.append("inventory_workflow")
        
        # Infer if it requires existing fabric
        requires_existing_fabric = any(phrase in content_lower for phrase in [
            "existing fabric", "fabric settings", "view fabric", "get fabric"
        ])
        
        # Infer estimated duration based on complexity
        step_count = content.lower().count("when:") + content.lower().count("then:")
        estimated_duration = max(30, min(300, step_count * 20))  # 30-300 seconds
        
        # Extract parameter placeholders
        parameter_pattern = r'\{\{([^}]+)\}\}'
        found_params = re.findall(parameter_pattern, content)
        required_parameters = list(set(param.strip() for param in found_params))
        
        return WorkflowMetadata(
            workflow_type=WorkflowType.CREATION,  # Will be overridden by directory
            dependencies=dependencies,
            can_run_standalone=len(dependencies) == 0,
            requires_existing_fabric=requires_existing_fabric,
            estimated_duration=estimated_duration,
            required_parameters=required_parameters,
            optional_parameters=[]
        )


    def _extract_test_cases(self, content: str) -> List[str]:
        """Extract test case names from template content"""
        
        # Find all test case definitions
        test_case_pattern = r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*$'
        test_cases = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('##') and not line.startswith('#') and not line.startswith('Given:') and not line.startswith('When:') and not line.startswith('Then:'):
                if re.match(test_case_pattern, line):
                    test_cases.append(line)
        
        return test_cases

    def _extract_template_parameters(self, content: str) -> List[str]:
        """Extract parameter placeholders from template content"""
        
        # Find all {{parameter}} patterns
        parameter_pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(parameter_pattern, content)
        
        # Remove duplicates and clean up
        parameters = list(set(param.strip() for param in matches))
        
        return sorted(parameters)

    async def _build_dependency_graph(self):
        """Build dependency graph from template metadata"""
        
        self.dependency_graph = {}
        
        for template_name, template in self.templates.items():
            self.dependency_graph[template_name] = template.metadata.dependencies
        
        # Validate dependency graph
        await self._validate_dependency_graph()
        
        logger.info(f"Built dependency graph with {len(self.dependency_graph)} workflows")

    async def _validate_dependency_graph(self):
        """Validate dependency graph for circular dependencies and missing workflows"""
        
        # Check for missing dependencies
        all_workflows = set(self.templates.keys())
        
        for workflow_name, dependencies in self.dependency_graph.items():
            for dep in dependencies:
                if dep not in all_workflows:
                    logger.warning(f"Workflow '{workflow_name}' depends on unknown workflow '{dep}'")
        
        # Check for circular dependencies
        if self._has_circular_dependencies():
            raise ValueError("Circular dependencies detected in workflow templates")

    def _has_circular_dependencies(self) -> bool:
        """Check if there are circular dependencies in the workflow graph"""
        
        def has_cycle_util(node: str, visited: set, rec_stack: set) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for dependency in self.dependency_graph.get(node, []):
                if dependency not in visited:
                    if has_cycle_util(dependency, visited, rec_stack):
                        return True
                elif dependency in rec_stack:
                    logger.error(f"Circular dependency detected: {node} -> {dependency}")
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        rec_stack = set()
        
        for workflow in self.dependency_graph:
            if workflow not in visited:
                if has_cycle_util(workflow, visited, rec_stack):
                    return True
        
        return False

    async def load_tdd_template(self, workflow_name: str) -> str:
        """Load TDD template content for a specific workflow"""
        
        if workflow_name not in self.templates:
            raise ValueError(f"TDD template not found for workflow: {workflow_name}")
        
        template = self.templates[workflow_name]
        
        # Check if template file has been modified
        file_path = Path(template.file_path)
        if file_path.exists():
            current_mtime = file_path.stat().st_mtime
            if current_mtime > template.last_modified:
                logger.info(f"Reloading modified template: {workflow_name}")
                workflow_type = template.workflow_type
                await self._load_single_template_with_metadata(file_path, workflow_type)
        
        return self.templates[workflow_name].content

    async def get_workflow_metadata(self, workflow_name: str) -> Optional[WorkflowMetadata]:
        """Get workflow metadata for a specific workflow"""
        
        template = self.templates.get(workflow_name)
        return template.metadata if template else None

    async def get_workflow_dependencies(self, workflow_name: str) -> List[str]:
        """Get dependencies for a specific workflow"""
        
        return self.dependency_graph.get(workflow_name, [])

    async def get_workflows_by_type(self, workflow_type: WorkflowType) -> List[str]:
        """Get all workflows of a specific type"""
        
        return self.templates_by_type.get(workflow_type, [])

    async def customize_template(self, template_content: str, parameters: Dict[str, Any]) -> str:
        """Customize template by replacing parameter placeholders with actual values"""
        
        customized_content = template_content
        
        # Replace all {{parameter}} placeholders
        for param_name, param_value in parameters.items():
            placeholder = f"{{{{{param_name}}}}}"
            customized_content = customized_content.replace(placeholder, str(param_value))
        
        # Handle default values for unreplaced placeholders
        customized_content = self._apply_default_values(customized_content)
        
        # Log any remaining unreplaced placeholders
        remaining_placeholders = re.findall(r'\{\{([^}]+)\}\}', customized_content)
        if remaining_placeholders:
            logger.warning(f"Unreplaced placeholders: {remaining_placeholders}")
        
        return customized_content

    def _apply_default_values(self, content: str) -> str:
        """Apply default values to any remaining placeholders"""
        
        default_values = {
            "cluster_ip": "192.168.1.100",
            "cluster_url": "https://192.168.1.100",
            "username": "admin",
            "password": "admin123",
            "fabric_name": "TestFabric",
            "area_name": "TestArea", 
            "building_name": "TestBuilding",
            "device_count": "1",
            "l3vn_count": "1",
            "timeout": "30000",
            "file_name": "devices.csv",
            "bgp_asn": "1200"
        }
        
        for param, default_value in default_values.items():
            placeholder = f"{{{{{param}}}}}"
            content = content.replace(placeholder, default_value)
        
        return content

    async def validate_template_parameters(self, workflow_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that a template can be customized with given parameters"""
        
        if workflow_name not in self.templates:
            return {
                "valid": False,
                "error": f"Template '{workflow_name}' not found"
            }
        
        template = self.templates[workflow_name]
        metadata = template.metadata
        
        required_params = set(metadata.required_parameters)
        optional_params = set(metadata.optional_parameters)
        provided_params = set(parameters.keys())
        
        missing_params = required_params - provided_params
        extra_params = provided_params - (required_params | optional_params)
        
        return {
            "valid": len(missing_params) == 0,
            "template_parameters": metadata.required_parameters + metadata.optional_parameters,
            "required_parameters": metadata.required_parameters,
            "optional_parameters": metadata.optional_parameters,
            "provided_parameters": list(provided_params),
            "missing_parameters": list(missing_params),
            "extra_parameters": list(extra_params),
            "warnings": [
                f"Missing required parameter: {p}" for p in missing_params
            ] + [
                f"Extra parameter provided: {p}" for p in extra_params
            ]
        }

    async def list_available_templates(self) -> List[Dict[str, Any]]:
        """List all available TDD templates with metadata"""
        
        templates_info = []
        
        for name, template in self.templates.items():
            templates_info.append({
                "name": name,
                "workflow_type": template.workflow_type.value,
                "dependencies": template.metadata.dependencies,
                "required_parameters": template.metadata.required_parameters,
                "optional_parameters": template.metadata.optional_parameters,
                "parameter_count": len(template.parameters),
                "estimated_duration": template.metadata.estimated_duration,
                "can_run_standalone": template.metadata.can_run_standalone,
                "requires_existing_fabric": template.metadata.requires_existing_fabric,
                "test_cases": template.test_cases,
                "file_path": template.file_path,
                "last_modified": template.last_modified
            })
        
        return templates_info

    async def _load_playwright_prompt_template(self):
        """Load the playwright prompt template"""
        
        prompt_path = Path(settings.PLAYWRIGHT_PROMPT_PATH)
        
        if not prompt_path.exists():
            logger.warning(f"Playwright prompt template not found: {prompt_path}")
            await self._create_sample_playwright_prompt(prompt_path)
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.playwright_prompt_template = f.read()
            
            logger.info("Loaded playwright prompt template")
            
        except Exception as e:
            logger.error(f"Failed to load playwright prompt template: {str(e)}")
            raise

    async def get_playwright_prompt_template(self) -> str:
        """Get the playwright prompt template for Azure OpenAI"""
        
        if not self.playwright_prompt_template:
            await self._load_playwright_prompt_template()
        
        return self.playwright_prompt_template

    async def _create_sample_templates_with_metadata(self, templates_path: Path):
        """Create sample TDD templates with metadata if none exist"""
        
        # Create directory structure
        creation_dir = templates_path / "creation"
        query_dir = templates_path / "query"
        modification_dir = templates_path / "modification"
        
        for dir_path in [creation_dir, query_dir, modification_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create sample login template in creation directory
        login_template = self._get_sample_login_template()
        with open(creation_dir / "login_flow.TDD.md", 'w', encoding='utf-8') as f:
            f.write(login_template)
        
        logger.info("Created sample template: login_flow.TDD.md")

    def _get_sample_login_template(self) -> str:
        """Get sample login template with metadata"""
        
        return """# Login Flow Workflow

## Workflow Metadata
workflow_type: creation
dependencies: []
can_run_standalone: true
requires_existing_fabric: false
estimated_duration: 30
parameters:
  required: [username, password, cluster_url]
  optional: [timeout]

## Test Cases (Write Tests First)

test_valid_login
Given: User with a valid username {{username}} and password {{password}}
When: The user navigates to {{cluster_url}} login page
When: The user enters credentials and clicks login button
Then: The system should land into the home page on successful login
Then: The system should check the title element be present in the home page

test_invalid_login
Given: User with an invalid username and password
When: The user click on the login in button.
Then: The system should see an error "Sign in failed" on unsuccessful login
"""

    async def _create_sample_playwright_prompt(self, prompt_path: Path):
        """Create sample playwright prompt template"""
        
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        
        playwright_prompt = """# Playwright Test Generation Prompt

You are an expert in generating Playwright TypeScript tests for enterprise network management applications.

## Context
You will be provided with:
1. A Test-Driven Development (TDD) template describing the test scenario
2. Cluster configuration details for the target system

## Your Task
Generate a complete, executable Playwright TypeScript test based on the TDD template.

## TDD Template
```
{tdd_template}
```

## Cluster Configuration
- URL: {cluster_url}
- Username: {username}
- Password: {password}

Generate the complete Playwright test now:
"""
        
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(playwright_prompt)
        
        logger.info("Created sample playwright prompt template")

    async def get_template_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded templates"""
        
        stats = {
            "total_templates": len(self.templates),
            "templates_by_type": {
                wf_type.value: len(templates) 
                for wf_type, templates in self.templates_by_type.items()
            },
            "total_dependencies": sum(len(deps) for deps in self.dependency_graph.values()),
            "workflows_with_dependencies": len([w for w, deps in self.dependency_graph.items() if deps]),
            "standalone_workflows": len([w for w, t in self.templates.items() if t.metadata.can_run_standalone]),
            "fabric_dependent_workflows": len([w for w, t in self.templates.items() if t.metadata.requires_existing_fabric])
        }
        
        return stats