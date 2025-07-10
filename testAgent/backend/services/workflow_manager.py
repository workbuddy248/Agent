"""
Enhanced Workflow Manager Service - Handles workflow dependencies, clarifications, and execution sequencing
File: backend/services/workflow_manager.py
"""

import logging
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from services.template_manager import TemplateManagerService, WorkflowType
from core.config import settings

logger = logging.getLogger(__name__)

class ClarificationType(str, Enum):
    """Types of clarifications needed from user"""
    FABRIC_SELECTION = "fabric_selection"
    DEVICE_SELECTION = "device_selection"
    RESOURCE_CREATION = "resource_creation"
    PARAMETER_SPECIFICATION = "parameter_specification"

@dataclass
class ClarificationOption:
    """Single clarification option"""
    value: str
    label: str
    description: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@dataclass
class ClarificationQuestion:
    """Clarification question for user"""
    type: ClarificationType
    message: str
    options: List[ClarificationOption]
    workflow_context: str
    parameter_name: Optional[str] = None

@dataclass
class WorkflowExecutionPlan:
    """Complete workflow execution plan"""
    session_id: str
    primary_workflows: List[str]
    execution_chain: List[str]
    parameters: Dict[str, Any]
    estimated_duration: int
    requires_clarification: bool = False
    clarification_question: Optional[ClarificationQuestion] = None

class WorkflowManagerService:
    """Enhanced service for managing workflow dependencies, clarifications, and execution"""
    
    def __init__(self):
        self.template_manager: Optional[TemplateManagerService] = None
        self.mock_cluster_resources: Dict[str, List[Dict[str, Any]]] = {
            "fabrics": [],  # Mock empty for POC
            "devices": [],  # Mock empty for POC
            "areas": [],    # Mock empty for POC
            "buildings": [] # Mock empty for POC
        }
        
    async def initialize(self):
        """Initialize workflow manager with template manager integration"""
        logger.info("Initializing Enhanced Workflow Manager Service...")
        
        # Initialize template manager if not provided
        if not self.template_manager:
            self.template_manager = TemplateManagerService()
            await self.template_manager.initialize()
        
        # Initialize mock cluster resources for POC
        await self._initialize_mock_cluster_resources()
        
        logger.info("Enhanced Workflow Manager Service initialized")

    async def set_template_manager(self, template_manager: TemplateManagerService):
        """Set the template manager instance"""
        self.template_manager = template_manager

    async def _initialize_mock_cluster_resources(self):
        """Initialize mock cluster resources for POC testing"""
        
        # For POC, we return empty resources to simulate "nothing found"
        # This forces the "create new" workflow path
        self.mock_cluster_resources = {
            "fabrics": [],
            "devices": [], 
            "areas": [],
            "buildings": []
        }
        
        logger.info("Initialized mock cluster resources (empty for POC)")

    async def resolve_workflow_chain(self, primary_workflows: List[str], 
                                   parameters: Dict[str, Any],
                                   session_id: str) -> WorkflowExecutionPlan:
        """
        Resolve the complete workflow chain including dependencies and clarifications
        
        Args:
            primary_workflows: List of workflows identified from instruction
            parameters: Parameters extracted from instruction
            session_id: Unique session identifier
            
        Returns:
            WorkflowExecutionPlan with execution chain and potential clarifications
        """
        logger.info(f"Resolving workflow chain for session {session_id}: {primary_workflows}")
        
        try:
            # Step 1: Collect all required workflows including dependencies
            all_required_workflows = await self._collect_all_dependencies(primary_workflows)
            
            # Step 2: Check for ambiguities that need clarification
            clarification = await self._detect_clarification_needs(all_required_workflows, parameters)
            
            if clarification:
                logger.info(f"Clarification needed for session {session_id}: {clarification.type}")
                return WorkflowExecutionPlan(
                    session_id=session_id,
                    primary_workflows=primary_workflows,
                    execution_chain=[],
                    parameters=parameters,
                    estimated_duration=0,
                    requires_clarification=True,
                    clarification_question=clarification
                )
            
            # Step 3: Sort workflows by dependencies using topological sort
            ordered_workflows = await self._topological_sort_workflows(all_required_workflows)
            
            # Step 4: Calculate estimated duration
            estimated_duration = await self._calculate_total_duration(ordered_workflows)
            
            # Step 5: Validate the workflow chain
            await self._validate_workflow_chain(ordered_workflows, parameters)
            
            execution_plan = WorkflowExecutionPlan(
                session_id=session_id,
                primary_workflows=primary_workflows,
                execution_chain=ordered_workflows,
                parameters=parameters,
                estimated_duration=estimated_duration,
                requires_clarification=False
            )
            
            logger.info(f"Resolved workflow chain for session {session_id}: {ordered_workflows}")
            return execution_plan
            
        except Exception as e:
            logger.error(f"Failed to resolve workflow chain for session {session_id}: {str(e)}")
            raise

    async def _collect_all_dependencies(self, workflows: List[str]) -> List[str]:
        """Collect all workflows including their dependencies recursively"""
        
        all_workflows = set()
        
        async def add_workflow_with_deps(workflow: str):
            if workflow in all_workflows:
                return
            
            # Get dependencies from template metadata
            dependencies = await self.template_manager.get_workflow_dependencies(workflow)
            
            # Add dependencies first (depth-first)
            for dep in dependencies:
                await add_workflow_with_deps(dep)
            
            # Then add the workflow itself
            all_workflows.add(workflow)
        
        # Process each primary workflow
        for workflow in workflows:
            await add_workflow_with_deps(workflow)
        
        return list(all_workflows)

    async def _detect_clarification_needs(self, workflows: List[str], 
                                        parameters: Dict[str, Any]) -> Optional[ClarificationQuestion]:
        """Detect if user clarification is needed before execution"""
        
        # Check for fabric-dependent workflows without fabric specification
        fabric_dependent_workflows = []
        for workflow in workflows:
            metadata = await self.template_manager.get_workflow_metadata(workflow)
            if metadata and metadata.requires_existing_fabric:
                fabric_dependent_workflows.append(workflow)
        
        if fabric_dependent_workflows:
            # Check if fabric is specified in parameters
            fabric_specified = any(key in parameters for key in ['fabric_name', 'fabric_id', 'existing_fabric'])
            
            if not fabric_specified:
                # Try to auto-detect existing fabrics
                existing_fabrics = await self._get_existing_cluster_resources("fabrics", parameters)
                
                if existing_fabrics:
                    # User has choice between existing and creating new
                    return await self._create_fabric_selection_question(fabric_dependent_workflows[0], existing_fabrics)
                else:
                    # No existing fabrics found, will create new - no clarification needed
                    logger.info("No existing fabrics found, will proceed with fabric creation")
                    return None
        
        # Check for missing required parameters
        missing_params_clarification = await self._check_missing_required_parameters(workflows, parameters)
        if missing_params_clarification:
            return missing_params_clarification
        
        return None

    async def _get_existing_cluster_resources(self, resource_type: str, 
                                           parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get existing cluster resources (mock implementation for POC)"""
        
        # For POC, always return empty to simulate "nothing found"
        # In real implementation, this would make API calls to the cluster
        
        try:
            cluster_config = {
                "url": parameters.get("cluster_url", ""),
                "username": parameters.get("username", ""),
                "password": parameters.get("password", "")
            }
            
            logger.info(f"Checking for existing {resource_type} on cluster {cluster_config.get('url', 'unknown')}")
            
            # Mock cluster API call (always returns empty for POC)
            existing_resources = self.mock_cluster_resources.get(resource_type, [])
            
            logger.info(f"Found {len(existing_resources)} existing {resource_type}")
            return existing_resources
            
        except Exception as e:
            logger.error(f"Failed to check existing {resource_type}: {str(e)}")
            # If auto-detection fails, return empty list (will create new)
            return []

    async def _create_fabric_selection_question(self, workflow_context: str, 
                                              existing_fabrics: List[Dict[str, Any]]) -> ClarificationQuestion:
        """Create fabric selection clarification question"""
        
        options = []
        
        # Add options for existing fabrics
        for fabric in existing_fabrics:
            options.append(ClarificationOption(
                value=f"existing_{fabric['id']}",
                label=f"Use existing fabric: {fabric['name']}",
                description=f"Status: {fabric.get('status', 'Unknown')}",
                data=fabric
            ))
        
        # Add option to create new fabric
        options.append(ClarificationOption(
            value="create_new",
            label="Create new fabric",
            description="Create a new fabric with devices and settings"
        ))
        
        return ClarificationQuestion(
            type=ClarificationType.FABRIC_SELECTION,
            message="Which fabric do you want to use for this workflow?",
            options=options,
            workflow_context=workflow_context
        )

    async def _check_missing_required_parameters(self, workflows: List[str], 
                                               parameters: Dict[str, Any]) -> Optional[ClarificationQuestion]:
        """Check for missing required parameters across all workflows"""
        
        all_missing_params = {}
        
        for workflow in workflows:
            metadata = await self.template_manager.get_workflow_metadata(workflow)
            if metadata:
                for param in metadata.required_parameters:
                    if param not in parameters:
                        if param not in all_missing_params:
                            all_missing_params[param] = []
                        all_missing_params[param].append(workflow)
        
        if all_missing_params:
            # For now, just log the missing parameters
            # In a full implementation, you might create clarification questions for these
            logger.warning(f"Missing required parameters: {all_missing_params}")
            
            # For POC, we'll use default values instead of asking user
            # In production, you might want to create clarification questions
        
        return None

    async def _topological_sort_workflows(self, workflows: List[str]) -> List[str]:
        """Sort workflows based on dependencies using topological sort"""
        
        # Create adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize all workflows with in-degree 0
        for workflow in workflows:
            in_degree[workflow] = 0
        
        # Build the graph from template dependencies
        for workflow in workflows:
            dependencies = await self.template_manager.get_workflow_dependencies(workflow)
            for dep in dependencies:
                if dep in workflows:  # Only consider dependencies that are in our workflow list
                    graph[dep].append(workflow)
                    in_degree[workflow] += 1
        
        # Topological sort using Kahn's algorithm
        queue = deque([workflow for workflow in workflows if in_degree[workflow] == 0])
        result = []
        
        while queue:
            # Sort queue by priority to ensure deterministic order
            queue = deque(sorted(queue, key=lambda w: self._get_workflow_priority(w)))
            
            current = queue.popleft()
            result.append(current)
            
            # Reduce in-degree of neighbors
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check if all workflows were processed (no cycles)
        if len(result) != len(workflows):
            remaining = set(workflows) - set(result)
            raise ValueError(f"Circular dependency detected involving: {remaining}")
        
        return result

    def _get_workflow_priority(self, workflow_name: str) -> int:
        """Get workflow priority for sorting (lower number = higher priority)"""
        
        priority_map = {
            "login_flow": 1,
            "network_hierarchy_creation": 2,
            "inventory_workflow": 3,
            "fabric_creation": 4,
            "device_provisioning": 5,
            "l3vn_management": 6,
            "fabric_settings": 7,
            "get_fabric": 8
        }
        
        return priority_map.get(workflow_name, 999)

    async def _calculate_total_duration(self, workflows: List[str]) -> int:
        """Calculate total estimated duration for workflow chain"""
        
        total_duration = 0
        
        for workflow in workflows:
            metadata = await self.template_manager.get_workflow_metadata(workflow)
            if metadata:
                total_duration += metadata.estimated_duration
            else:
                total_duration += 60  # Default 60 seconds
        
        return total_duration

    async def _validate_workflow_chain(self, workflows: List[str], parameters: Dict[str, Any]):
        """Validate that the workflow chain can be executed with given parameters"""
        
        validation_issues = []
        
        for workflow in workflows:
            # Validate template exists
            if workflow not in self.template_manager.templates:
                validation_issues.append(f"Template not found for workflow: {workflow}")
                continue
            
            # Validate parameters
            validation_result = await self.template_manager.validate_template_parameters(workflow, parameters)
            if not validation_result["valid"]:
                validation_issues.extend(validation_result["warnings"])
        
        if validation_issues:
            logger.warning(f"Workflow chain validation issues: {validation_issues}")
            # For POC, just log warnings. In production, you might want to fail or ask for clarification

    async def process_user_clarification(self, session_id: str, clarification_response: Dict[str, Any],
                                       original_workflows: List[str], 
                                       original_parameters: Dict[str, Any]) -> WorkflowExecutionPlan:
        """
        Process user clarification response and update workflow chain
        
        Args:
            session_id: Session identifier
            clarification_response: User's response to clarification question
            original_workflows: Original workflow list
            original_parameters: Original parameters
            
        Returns:
            Updated WorkflowExecutionPlan
        """
        logger.info(f"Processing clarification response for session {session_id}: {clarification_response}")
        
        # Update parameters based on clarification response
        updated_parameters = original_parameters.copy()
        
        clarification_type = clarification_response.get("type")
        user_choice = clarification_response.get("choice")
        
        if clarification_type == ClarificationType.FABRIC_SELECTION:
            if user_choice == "create_new":
                # User wants to create new fabric - no changes needed
                logger.info(f"User chose to create new fabric for session {session_id}")
            elif user_choice.startswith("existing_"):
                # User selected existing fabric
                fabric_id = user_choice.replace("existing_", "")
                updated_parameters["fabric_id"] = fabric_id
                updated_parameters["use_existing_fabric"] = True
                
                # Remove fabric creation from workflow chain since we're using existing
                original_workflows = [w for w in original_workflows if w != "fabric_creation"]
                
                logger.info(f"User selected existing fabric {fabric_id} for session {session_id}")
        
        # Now resolve the workflow chain without clarification
        return await self.resolve_workflow_chain(original_workflows, updated_parameters, session_id)

    async def get_workflow_execution_plan(self, workflows: List[str], 
                                        parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a detailed execution plan for the workflow chain"""
        
        total_duration = 0
        workflow_details = []
        
        for i, workflow in enumerate(workflows):
            metadata = await self.template_manager.get_workflow_metadata(workflow)
            if not metadata:
                continue
                
            duration = metadata.estimated_duration
            total_duration += duration
            
            # Get template for parameter validation
            validation_result = await self.template_manager.validate_template_parameters(workflow, parameters)
            
            workflow_info = {
                "sequence": i + 1,
                "name": workflow,
                "workflow_type": metadata.workflow_type.value,
                "description": f"Execute {workflow.replace('_', ' ').title()}",
                "estimated_duration": duration,
                "dependencies": metadata.dependencies,
                "required_parameters": metadata.required_parameters,
                "optional_parameters": metadata.optional_parameters,
                "provided_parameters": validation_result.get("provided_parameters", []),
                "missing_parameters": validation_result.get("missing_parameters", []),
                "can_run_standalone": metadata.can_run_standalone,
                "requires_existing_fabric": metadata.requires_existing_fabric
            }
            
            workflow_details.append(workflow_info)
        
        return {
            "total_workflows": len(workflows),
            "estimated_total_duration": total_duration,
            "workflows": workflow_details,
            "execution_summary": {
                "will_create_hierarchy": "network_hierarchy_creation" in workflows,
                "will_create_fabric": "fabric_creation" in workflows,
                "will_provision_devices": "device_provisioning" in workflows or "inventory_workflow" in workflows,
                "will_manage_l3vn": "l3vn_management" in workflows,
                "requires_authentication": "login_flow" in workflows,
                "has_query_operations": any(
                    self.template_manager.templates.get(w, {}).workflow_type == WorkflowType.QUERY 
                    for w in workflows
                )
            }
        }

    async def get_next_workflow(self, completed_workflows: List[str], 
                              all_workflows: List[str]) -> Optional[str]:
        """Get the next workflow that can be executed based on completed workflows"""
        
        for workflow in all_workflows:
            if workflow in completed_workflows:
                continue
            
            # Check if all dependencies are satisfied
            dependencies = await self.template_manager.get_workflow_dependencies(workflow)
            if all(dep in completed_workflows for dep in dependencies):
                return workflow
        
        return None

    async def estimate_remaining_time(self, completed_workflows: List[str], 
                                    all_workflows: List[str]) -> int:
        """Estimate remaining execution time in seconds"""
        
        remaining_time = 0
        
        for workflow in all_workflows:
            if workflow not in completed_workflows:
                metadata = await self.template_manager.get_workflow_metadata(workflow)
                remaining_time += metadata.estimated_duration if metadata else 60
        
        return remaining_time

    async def get_workflow_status_summary(self, completed_workflows: List[str], 
                                        current_workflow: Optional[str],
                                        all_workflows: List[str]) -> Dict[str, Any]:
        """Get a summary of workflow execution status"""
        
        total_workflows = len(all_workflows)
        completed_count = len(completed_workflows)
        remaining_time = await self.estimate_remaining_time(completed_workflows, all_workflows)
        
        return {
            "total_workflows": total_workflows,
            "completed_workflows": completed_count,
            "current_workflow": current_workflow,
            "progress_percentage": round((completed_count / total_workflows) * 100, 1) if total_workflows > 0 else 0,
            "estimated_remaining_time": remaining_time,
            "completed_list": completed_workflows,
            "remaining_list": [w for w in all_workflows if w not in completed_workflows]
        }

    async def get_manager_statistics(self) -> Dict[str, Any]:
        """Get workflow manager statistics"""
        
        template_stats = await self.template_manager.get_template_statistics()
        
        return {
            "template_manager": template_stats,
            "mock_cluster_resources": {
                resource_type: len(resources) 
                for resource_type, resources in self.mock_cluster_resources.items()
            },
            "clarification_types_supported": [ct.value for ct in ClarificationType],
            "workflow_priorities": {
                "login_flow": 1,
                "network_hierarchy_creation": 2,
                "inventory_workflow": 3,
                "fabric_creation": 4,
                "device_provisioning": 5,
                "l3vn_management": 6
            }
        }