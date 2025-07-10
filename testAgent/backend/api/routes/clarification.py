"""
Clarification System API Routes - Handle user clarifications during workflow resolution
File: backend/api/routes/clarification.py
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from services.session_manager import SessionManagerService, session_manager
from services.workflow_manager import WorkflowManagerService, ClarificationType
from services.instruction_parser import InstructionParserService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["clarification"])

# Pydantic models for API requests/responses
class ClarificationOptionResponse(BaseModel):
    """Clarification option for API response"""
    value: str
    label: str
    description: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class ClarificationQuestionResponse(BaseModel):
    """Clarification question for API response"""
    type: str
    message: str
    options: List[ClarificationOptionResponse]
    workflow_context: str
    parameter_name: Optional[str] = None

class ClarificationNeededResponse(BaseModel):
    """Response when clarification is needed"""
    session_id: str
    status: str = "needs_clarification"
    question: ClarificationQuestionResponse
    context: Dict[str, Any]

class ProvideClarificationRequest(BaseModel):
    """Request to provide clarification response"""
    session_id: str
    clarification_response: Dict[str, Any]

class ClarificationProcessedResponse(BaseModel):
    """Response after processing clarification"""
    session_id: str
    status: str
    message: str
    updated_workflows: List[str]
    updated_parameters: Dict[str, Any]
    execution_plan: Optional[Dict[str, Any]] = None

# Initialize services (will be injected)
workflow_manager = WorkflowManagerService()
instruction_parser = InstructionParserService()

@router.post("/provide_clarification", response_model=ClarificationProcessedResponse)
async def provide_clarification(request: ProvideClarificationRequest):
    """
    Process user clarification response and update workflow execution plan
    
    Args:
        request: Clarification response from user
        
    Returns:
        Updated execution plan with resolved workflows
    """
    try:
        logger.info(f"Processing clarification for session: {request.session_id}")
        
        # Get the session
        session = await session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.status != "parsing":
            raise HTTPException(
                status_code=400, 
                detail=f"Session is not in clarification state. Current status: {session.status}"
            )
        
        # Validate clarification response structure
        clarification_response = request.clarification_response
        required_fields = ["type", "choice"]
        
        for field in required_fields:
            if field not in clarification_response:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field in clarification response: {field}"
                )
        
        # Process clarification with workflow manager
        updated_execution_plan = await workflow_manager.process_user_clarification(
            session_id=request.session_id,
            clarification_response=clarification_response,
            original_workflows=session.workflows,
            original_parameters=session.parameters
        )
        
        if updated_execution_plan.requires_clarification:
            # Still needs more clarification
            return ClarificationProcessedResponse(
                session_id=request.session_id,
                status="needs_more_clarification",
                message="Additional clarification required",
                updated_workflows=[],
                updated_parameters={},
                execution_plan={
                    "requires_clarification": True,
                    "clarification_question": _convert_clarification_to_dict(updated_execution_plan.clarification_question)
                }
            )
        
        # Update session with resolved workflows and parameters
        await session_manager.update_session_status(request.session_id, "parsed")
        
        # Store updated workflows and parameters in session
        session.workflows = updated_execution_plan.execution_chain
        session.parameters.update(updated_execution_plan.parameters)
        
        # Create execution plan response
        execution_plan_dict = await workflow_manager.get_workflow_execution_plan(
            updated_execution_plan.execution_chain,
            updated_execution_plan.parameters
        )
        
        logger.info(f"Clarification processed for session {request.session_id}: {len(updated_execution_plan.execution_chain)} workflows")
        
        return ClarificationProcessedResponse(
            session_id=request.session_id,
            status="clarification_resolved",
            message=f"Clarification processed successfully. {len(updated_execution_plan.execution_chain)} workflows ready for execution.",
            updated_workflows=updated_execution_plan.execution_chain,
            updated_parameters=updated_execution_plan.parameters,
            execution_plan=execution_plan_dict
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing clarification for session {request.session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process clarification: {str(e)}")

@router.get("/session/{session_id}/clarification_status")
async def get_clarification_status(session_id: str):
    """
    Get current clarification status for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Current clarification state and question if applicable
    """
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if session is in clarification state
        if session.status == "parsing":
            # This might be a clarification state - check if there's a pending question
            # In a full implementation, you might store the clarification question in the session
            return {
                "session_id": session_id,
                "status": "waiting_for_clarification",
                "message": "Session is waiting for user clarification",
                "has_pending_question": True
            }
        else:
            return {
                "session_id": session_id,
                "status": session.status,
                "message": f"Session status: {session.status}",
                "has_pending_question": False
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clarification status for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get clarification status: {str(e)}")

@router.post("/session/{session_id}/skip_clarification")
async def skip_clarification(session_id: str):
    """
    Skip clarification and proceed with default choices
    
    Args:
        session_id: Session identifier
        
    Returns:
        Execution plan with default choices applied
    """
    try:
        logger.info(f"Skipping clarification for session: {session_id}")
        
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.status != "parsing":
            raise HTTPException(
                status_code=400,
                detail=f"Session is not in clarification state. Current status: {session.status}"
            )
        
        # Apply default clarification response (always "create new")
        default_clarification = {
            "type": ClarificationType.FABRIC_SELECTION,
            "choice": "create_new"
        }
        
        # Process with default choice
        updated_execution_plan = await workflow_manager.process_user_clarification(
            session_id=session_id,
            clarification_response=default_clarification,
            original_workflows=session.workflows,
            original_parameters=session.parameters
        )
        
        # Update session
        await session_manager.update_session_status(session_id, "parsed")
        session.workflows = updated_execution_plan.execution_chain
        session.parameters.update(updated_execution_plan.parameters)
        
        execution_plan_dict = await workflow_manager.get_workflow_execution_plan(
            updated_execution_plan.execution_chain,
            updated_execution_plan.parameters
        )
        
        logger.info(f"Clarification skipped for session {session_id} with default choices")
        
        return {
            "session_id": session_id,
            "status": "clarification_skipped",
            "message": "Proceeded with default choices (create new resources)",
            "workflows": updated_execution_plan.execution_chain,
            "execution_plan": execution_plan_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error skipping clarification for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to skip clarification: {str(e)}")

@router.get("/clarification_types")
async def get_supported_clarification_types():
    """
    Get list of supported clarification types
    
    Returns:
        List of clarification types with descriptions
    """
    try:
        clarification_types = [
            {
                "type": ClarificationType.FABRIC_SELECTION,
                "name": "Fabric Selection",
                "description": "Choose between existing fabric or create new fabric",
                "example_options": ["Use existing fabric", "Create new fabric"]
            },
            {
                "type": ClarificationType.DEVICE_SELECTION,
                "name": "Device Selection", 
                "description": "Select specific devices for operations",
                "example_options": ["Device A", "Device B", "All devices"]
            },
            {
                "type": ClarificationType.RESOURCE_CREATION,
                "name": "Resource Creation",
                "description": "Choose resource creation options",
                "example_options": ["Create with defaults", "Custom configuration"]
            },
            {
                "type": ClarificationType.PARAMETER_SPECIFICATION,
                "name": "Parameter Specification",
                "description": "Provide missing required parameters",
                "example_options": ["Specify parameter value", "Use default value"]
            }
        ]
        
        return {
            "supported_types": clarification_types,
            "total_types": len(clarification_types)
        }
        
    except Exception as e:
        logger.error(f"Error getting clarification types: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get clarification types: {str(e)}")

@router.post("/test_clarification_generation")
async def test_clarification_generation(test_request: Dict[str, Any]):
    """
    Test endpoint for generating clarification questions (development/testing)
    
    Args:
        test_request: Test parameters for clarification generation
        
    Returns:
        Sample clarification question
    """
    try:
        instruction = test_request.get("instruction", "create L3VN")
        parameters = test_request.get("parameters", {})
        
        logger.info(f"Testing clarification generation for: {instruction}")
        
        # Parse instruction to get workflows
        parsed_result = await instruction_parser.parse_instruction(
            instruction=instruction,
            cluster_url=parameters.get("cluster_url"),
            username=parameters.get("username"),
            password=parameters.get("password")
        )
        
        # Try to resolve workflow chain (should trigger clarification)
        execution_plan = await workflow_manager.resolve_workflow_chain(
            primary_workflows=parsed_result.workflows,
            parameters=parsed_result.parameters,
            session_id="test_session"
        )
        
        if execution_plan.requires_clarification:
            return {
                "clarification_generated": True,
                "question": _convert_clarification_to_dict(execution_plan.clarification_question),
                "context": {
                    "detected_workflows": parsed_result.workflows,
                    "extracted_parameters": parsed_result.parameters
                }
            }
        else:
            return {
                "clarification_generated": False,
                "message": "No clarification needed for this instruction",
                "resolved_workflows": execution_plan.execution_chain
            }
        
    except Exception as e:
        logger.error(f"Error in test clarification generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Test clarification generation failed: {str(e)}")

# Helper functions
def _convert_clarification_to_dict(clarification_question) -> Dict[str, Any]:
    """Convert clarification question object to dictionary for API response"""
    
    if not clarification_question:
        return {}
    
    return {
        "type": clarification_question.type,
        "message": clarification_question.message,
        "workflow_context": clarification_question.workflow_context,
        "parameter_name": clarification_question.parameter_name,
        "options": [
            {
                "value": option.value,
                "label": option.label,
                "description": option.description,
                "data": option.data
            }
            for option in clarification_question.options
        ]
    }

def _convert_dict_to_clarification_response(clarification_dict: Dict[str, Any]) -> ClarificationQuestionResponse:
    """Convert dictionary to clarification question response model"""
    
    options = [
        ClarificationOptionResponse(
            value=opt["value"],
            label=opt["label"],
            description=opt.get("description"),
            data=opt.get("data")
        )
        for opt in clarification_dict.get("options", [])
    ]
    
    return ClarificationQuestionResponse(
        type=clarification_dict["type"],
        message=clarification_dict["message"],
        options=options,
        workflow_context=clarification_dict["workflow_context"],
        parameter_name=clarification_dict.get("parameter_name")
    )