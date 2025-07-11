"""
E2E Testing Agent Backend - FastAPI Application
File: backend/main.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import uuid
import logging
from datetime import datetime

# Import our core services
from services.instruction_parser import InstructionParserService
from services.workflow_manager import WorkflowManagerService
from services.template_manager import TemplateManagerService
from services.playwright_generator import PlaywrightGeneratorService
from services.test_executor import TestExecutorService
from services.session_manager import SessionManagerService
from core.config import settings
from core.logging_config import setup_logging

# Import API routes
from api.routes import clarification

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="E2E Testing Agent API",
    description="Transform natural language instructions into automated Playwright tests",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
instruction_parser = InstructionParserService()
workflow_manager = WorkflowManagerService()
template_manager = TemplateManagerService()
playwright_generator = PlaywrightGeneratorService()
test_executor = TestExecutorService()
session_manager = SessionManagerService()

# Pydantic models for API
class ParseInstructionRequest(BaseModel):
    prompt: str
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class ExecuteTestRequest(BaseModel):
    session_id: str

class SessionStatusRequest(BaseModel):
    session_id: str

class AnalyzeInstructionRequest(BaseModel):
    instruction: str

# API Endpoints

@app.post("/parse_test_instructions")
async def parse_test_instructions(request: ParseInstructionRequest):
    """
    Parse natural language instruction and prepare test session (with clarification support)
    """
    try:
        logger.info(f"Parsing instruction: {request.prompt[:100]}...")
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Parse the instruction to identify workflows
        parsed_result = await instruction_parser.parse_instruction(
            instruction=request.prompt,
            cluster_url=request.url,
            username=request.username,
            password=request.password
        )
        
        # Resolve workflow dependencies and check for clarifications
        execution_plan = await workflow_manager.resolve_workflow_chain(
            primary_workflows=parsed_result.workflows,
            parameters=parsed_result.parameters,
            session_id=session_id
        )
        
        # Create session with initial data
        session = await session_manager.create_session(
            session_id=session_id,
            instruction=request.prompt,
            workflows=execution_plan.primary_workflows,  # Store original workflows
            parameters=parsed_result.parameters,
            cluster_config={
                "url": request.url,
                "username": request.username,
                "password": request.password
            }
        )
        
        # Check if clarification is needed
        if execution_plan.requires_clarification:
            logger.info(f"Clarification needed for session {session_id}: {execution_plan.clarification_question.type}")
            
            # Convert clarification question to API response format
            clarification_dict = {
                "type": execution_plan.clarification_question.type,
                "message": execution_plan.clarification_question.message,
                "workflow_context": execution_plan.clarification_question.workflow_context,
                "parameter_name": execution_plan.clarification_question.parameter_name,
                "options": [
                    {
                        "value": option.value,
                        "label": option.label,
                        "description": option.description,
                        "data": option.data
                    }
                    for option in execution_plan.clarification_question.options
                ]
            }
            
            return {
                "session_id": session_id,
                "status": "needs_clarification",
                "message": "User clarification required before proceeding",
                "clarification": clarification_dict,
                "detected_workflows": parsed_result.workflows,
                "extracted_parameters": parsed_result.parameters
            }
        
        # No clarification needed - store resolved workflows
        session.workflows = execution_plan.execution_chain
        session.parameters.update(execution_plan.parameters)
        await session_manager.update_session_status(session_id, "parsed")
        
        logger.info(f"Session {session_id} parsed successfully with workflows: {execution_plan.execution_chain}")
        
        return {
            "session_id": session_id,
            "workflows": execution_plan.execution_chain,
            "parameters": execution_plan.parameters,
            "status": "parsed",
            "estimated_duration": execution_plan.estimated_duration,
            "message": f"Identified {len(execution_plan.execution_chain)} workflow(s) to execute"
        }
        
    except Exception as e:
        logger.error(f"Error parsing instructions: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to parse instructions: {str(e)}")

@app.post("/execute_test_plan")
async def execute_test_plan(request: ExecuteTestRequest):
    """
    Execute the test plan for a session (supports post-clarification execution)
    """
    try:
        logger.info(f"Executing test plan for session: {request.session_id}")
        
        # Get session details
        session = await session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check session status - should be 'parsed' after clarification resolution
        if session.status not in ["parsed", "created"]:
            if session.status == "parsing":
                raise HTTPException(
                    status_code=400, 
                    detail="Session requires clarification. Please provide clarification first using /provide_clarification endpoint."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Session is not ready for execution. Current status: {session.status}"
                )
        
        # Validate that session has workflows to execute
        if not session.workflows:
            raise HTTPException(
                status_code=400,
                detail="Session has no workflows to execute. Session may need clarification or re-parsing."
            )
        
        # Update session status
        await session_manager.update_session_status(request.session_id, "generating")
        
        # Start async execution (don't wait for completion)
        asyncio.create_task(execute_test_workflow(request.session_id))
        
        return {
            "session_id": request.session_id,
            "status": "started",
            "workflows_count": len(session.workflows),
            "estimated_duration": await workflow_manager.estimate_remaining_time([], session.workflows),
            "message": f"Test execution started for {len(session.workflows)} workflows"
        }
        
    except Exception as e:
        logger.error(f"Error executing test plan: {str(e)}")
        await session_manager.update_session_status(request.session_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to execute test plan: {str(e)}")

@app.post("/get_session_status")
async def get_session_status(request: SessionStatusRequest):
    """
    Get current status of a test session
    """
    try:
        session = await session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": request.session_id,
            "status": session.status,
            "workflows": session.workflows,
            "current_workflow": session.current_workflow,
            "progress": session.progress,
            "steps": session.execution_steps,
            "error_message": session.error_message,
            "started_at": session.started_at,
            "updated_at": session.updated_at
        }
        
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")

@app.post("/analyze_instruction")
async def analyze_instruction(request: AnalyzeInstructionRequest):
    """
    Analyze instruction without executing (for testing/debugging with clarification detection)
    """
    try:
        # Parse instruction with template manager integration
        parsed_result = await instruction_parser.analyze_instruction_only(
            request.instruction, 
            template_manager=template_manager
        )
        
        # Try workflow resolution to detect clarifications
        test_session_id = "analysis_test"
        workflows = list(parsed_result.get("workflow_scores", {}).keys())
        
        if workflows:
            # Get the highest scoring workflow
            workflow_scores = parsed_result.get("workflow_scores", {})
            sorted_workflows = sorted(workflow_scores.items(), key=lambda x: x[1]["score"], reverse=True)
            primary_workflow = sorted_workflows[0][0]
            
            # Test clarification detection
            execution_plan = await workflow_manager.resolve_workflow_chain(
                primary_workflows=[primary_workflow],
                parameters=parsed_result.get("detected_parameters", {}),
                session_id=test_session_id
            )
            
            clarification_info = {
                "needs_clarification": execution_plan.requires_clarification,
                "clarification_type": execution_plan.clarification_question.type if execution_plan.clarification_question else None,
                "clarification_message": execution_plan.clarification_question.message if execution_plan.clarification_question else None
            }
        else:
            clarification_info = {
                "needs_clarification": False,
                "clarification_type": None,
                "clarification_message": None
            }
        
        # Get template information
        template_info = await template_manager.list_available_templates()
        
        analysis_result = {
            **parsed_result,
            "clarification_analysis": clarification_info,
            "available_templates": len(template_info),
            "template_details": [
                {
                    "name": t["name"], 
                    "type": t["workflow_type"],
                    "dependencies": t["dependencies"]
                } 
                for t in template_info
            ]
        }
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error analyzing instruction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze instruction: {str(e)}")

@app.get("/templates/list")
async def list_templates():
    """
    List all available TDD templates with metadata
    """
    try:
        templates = await template_manager.list_available_templates()
        stats = await template_manager.get_template_statistics()
        
        return {
            "templates": templates,
            "statistics": stats,
            "total_count": len(templates)
        }
        
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")

@app.get("/workflows/dependencies")
async def get_workflow_dependencies():
    """
    Get workflow dependency graph for debugging
    """
    try:
        templates = await template_manager.list_available_templates()
        dependency_graph = {}
        
        for template in templates:
            dependency_graph[template["name"]] = {
                "dependencies": template["dependencies"],
                "workflow_type": template["workflow_type"],
                "estimated_duration": template["estimated_duration"]
            }
        
        return {
            "dependency_graph": dependency_graph,
            "workflow_count": len(dependency_graph)
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow dependencies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workflow dependencies: {str(e)}")

@app.post("/list_active_sessions")
async def list_active_sessions():
    """
    List all active test sessions
    """
    try:
        sessions = await session_manager.list_active_sessions()
        return {
            "active_sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error listing active sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list active sessions: {str(e)}")

@app.post("/test_azure_openai_connection")
async def test_azure_openai_connection():
    """
    Test Azure OpenAI connectivity
    """
    try:
        result = await playwright_generator.test_connection()
        return {"status": "success", "message": "Azure OpenAI connection successful", "details": result}
        
    except Exception as e:
        logger.error(f"Azure OpenAI connection test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Azure OpenAI connection failed: {str(e)}")

@app.post("/test_browser_automation")
async def test_browser_automation():
    """
    Test browser automation setup
    """
    try:
        result = await test_executor.test_browser_setup()
        return {"status": "success", "message": "Browser automation setup successful", "details": result}
        
    except Exception as e:
        logger.error(f"Browser automation test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Browser automation test failed: {str(e)}")

# Background task for test execution
async def execute_test_workflow(session_id: str):
    """
    Background task to execute the complete test workflow
    """
    try:
        logger.info(f"Starting workflow execution for session: {session_id}")
        
        session = await session_manager.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return
        
        # Step 1: Load TDD templates for each workflow
        await session_manager.update_session_status(session_id, "loading_templates")
        templates = {}
        
        for workflow_name in session.workflows:
            logger.info(f"Loading template for workflow: {workflow_name}")
            template_content = await template_manager.load_tdd_template(workflow_name)
            templates[workflow_name] = template_content
        
        # Step 2: Generate Playwright tests
        await session_manager.update_session_status(session_id, "generating")
        playwright_tests = {}
        
        for workflow_name, template_content in templates.items():
            logger.info(f"Generating Playwright test for workflow: {workflow_name}")
            
            # Customize template with parameters
            customized_template = await template_manager.customize_template(
                template_content, session.parameters
            )
            
            # Generate Playwright code using Azure OpenAI
            playwright_code = await playwright_generator.generate_playwright_test(
                workflow_name=workflow_name,
                tdd_template=customized_template,
                cluster_config=session.cluster_config
            )
            
            playwright_tests[workflow_name] = playwright_code
        
        # Step 3: Execute Playwright tests
        await session_manager.update_session_status(session_id, "executing")
        
        execution_results = await test_executor.execute_tests(
            session_id=session_id,
            playwright_tests=playwright_tests,
            cluster_config=session.cluster_config
        )
        
        # Step 4: Process results and update session
        if execution_results.get("success", False):
            await session_manager.update_session_status(session_id, "completed")
        else:
            await session_manager.update_session_status(
                session_id, "failed", execution_results.get("error_message", "Test execution failed")
            )
        
        # Store execution results
        await session_manager.store_execution_results(session_id, execution_results)
        
        logger.info(f"Workflow execution completed for session: {session_id}")
        
    except Exception as e:
        logger.error(f"Error in workflow execution for session {session_id}: {str(e)}")
        await session_manager.update_session_status(session_id, "failed", str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

@app.post("/test_cisco_idp_connection")
async def test_cisco_idp_connection():
    """
    Test Cisco IDP authentication and Azure OpenAI connectivity
    """
    try:
        from services.azure_openai_service import azure_openai_service
        
        # Test Cisco IDP authentication
        print("Testing Cisco IDP authentication...")
        await azure_openai_service._authenticate_and_initialize_llm()
        
        # Get token information
        token_info = await azure_openai_service.get_token_info()
        
        # Test Azure OpenAI connection
        connection_result = await azure_openai_service.test_connection()
        
        if connection_result['status'] == 'success':
            return {
                "status": "success",
                "message": "Cisco IDP + Azure OpenAI connection successful",
                "authentication": {
                    "method": "cisco_idp",
                    "token_status": "valid" if token_info['has_token'] else "invalid",
                    "token_expires": token_info['token_expires_at'],
                    "idp_endpoint": token_info['cisco_idp_endpoint'],
                    "app_key": token_info['app_key']
                },
                "azure_openai": {
                    "endpoint": connection_result.get('endpoint'),
                    "model": connection_result.get('model'),
                    "api_version": azure_openai_service.api_version
                }
            }
        else:
            return {
                "status": "error",
                "message": "Cisco IDP authentication successful but Azure OpenAI connection failed",
                "cisco_idp": {
                    "status": "success",
                    "token_status": "valid" if token_info['has_token'] else "invalid"
                },
                "azure_openai": {
                    "status": "failed",
                    "error": connection_result.get('message')
                }
            }
        
    except Exception as e:
        logger.error(f"Cisco IDP + Azure OpenAI test failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Cisco IDP + Azure OpenAI test failed: {str(e)}",
            "suggestion": "Check your .env configuration for Cisco IDP credentials"
        }

@app.post("/test_cisco_ai_generation")
async def test_cisco_ai_generation():
    """
    Test AI-powered Playwright test generation with Cisco IDP authentication
    """
    try:
        # Test with a Cisco-specific TDD template
        test_tdd_template = """test_cisco_catalyst_login
Given: User with valid Cisco credentials admin1/password123
When: The user navigates to Cisco Catalyst Center login page
When: The user enters username and password in Cisco login form
When: The user clicks the Cisco login button
Then: The system should redirect to Catalyst Center dashboard
Then: The system should display "Welcome to Catalyst Center!" message
Then: The system should show Cisco navigation menu with Design, Policy, Provision options"""
        
        test_cluster_config = {
            "url": "https://172.27.248.237:443/",
            "username": "admin1",
            "password": "password123"
        }
        
        # Generate using Cisco IDP authenticated Azure OpenAI
        playwright_code = await playwright_generator.generate_playwright_test(
            workflow_name="cisco_catalyst_login_test",
            tdd_template=test_tdd_template,
            cluster_config=test_cluster_config
        )
        
        # Analyze the generated code for Cisco-specific elements
        cisco_analysis = {
            "generated_length": len(playwright_code),
            "contains_cisco_elements": any(keyword in playwright_code.lower() 
                                         for keyword in ["cisco", "catalyst", "center"]),
            "contains_navigation": "navigation" in playwright_code.lower(),
            "contains_welcome_message": "welcome" in playwright_code.lower(),
            "contains_proper_selectors": "[data-test-id" in playwright_code or "text=" in playwright_code,
            "contains_waits": "waitFor" in playwright_code,
            "contains_assertions": "expect(" in playwright_code,
            "line_count": len(playwright_code.split('\n')),
            "authentication_method": "cisco_idp"
        }
        
        return {
            "status": "success",
            "message": "Cisco IDP authenticated AI generation successful",
            "generated_code_preview": playwright_code[:600] + "..." if len(playwright_code) > 600 else playwright_code,
            "cisco_analysis": cisco_analysis,
            "full_code_length": len(playwright_code),
            "authentication": "cisco_idp_azure_openai"
        }
        
    except Exception as e:
        logger.error(f"Cisco AI generation test failed: {str(e)}")
        return {
            "status": "error", 
            "message": f"Cisco AI generation test failed: {str(e)}",
            "authentication": "cisco_idp_azure_openai"
        }

@app.get("/cisco_system_status")
async def get_cisco_system_status():
    """
    Get comprehensive system status for Cisco IDP + Azure OpenAI integration
    """
    try:
        from services.azure_openai_service import azure_openai_service
        from core.config import settings
        
        # Check configuration
        config_status = {
            "cisco_client_id": bool(settings.CISCO_CLIENT_ID),
            "cisco_client_secret": bool(settings.CISCO_CLIENT_SECRET),
            "cisco_app_key": bool(settings.CISCO_APP_KEY),
            "cisco_idp_endpoint": bool(settings.CISCO_IDP_ENDPOINT),
            "azure_openai_endpoint": bool(settings.AZURE_OPENAI_ENDPOINT),
            "deployment_name": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            "api_version": settings.AZURE_OPENAI_API_VERSION
        }
        
        # Test authentication if possible
        auth_status = {"status": "unknown", "error": None}
        try:
            token_info = await azure_openai_service.get_token_info()
            auth_status = {
                "status": "success" if token_info['has_token'] else "no_token",
                "token_expires": token_info['token_expires_at'],
                "time_until_expiry": token_info['time_until_expiry']
            }
        except Exception as e:
            auth_status = {
                "status": "error",
                "error": str(e)
            }
        
        # Overall system health
        all_config_valid = all([
            config_status['cisco_client_id'],
            config_status['cisco_client_secret'], 
            config_status['cisco_app_key'],
            config_status['cisco_idp_endpoint'],
            config_status['azure_openai_endpoint']
        ])
        
        system_health = "healthy" if all_config_valid and auth_status['status'] == "success" else "degraded"
        
        return {
            "system_health": system_health,
            "authentication_method": "cisco_idp",
            "ai_provider": "azure_openai",
            "configuration": config_status,
            "authentication": auth_status,
            "services": {
                "instruction_parser": "initialized",
                "workflow_manager": "initialized", 
                "template_manager": "initialized",
                "playwright_generator": "initialized_with_cisco_idp",
                "test_executor": "initialized"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "system_health": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/test_azure_openai_connection")
async def test_azure_openai_connection():
    """
    Test Azure OpenAI connectivity and generation capabilities
    """
    try:
        from services.azure_openai_service import azure_openai_service
        
        # Test basic connection
        connection_result = await azure_openai_service.test_connection()
        
        if connection_result['status'] == 'success':
            # Test actual generation
            test_prompt = """Generate a simple Playwright test that:
1. Navigates to https://example.com
2. Clicks a login button
3. Verifies the page title"""
            
            generation_result = await azure_openai_service.generate_completion(
                prompt=test_prompt,
                max_tokens=500,
                system_prompt="You are a Playwright test expert. Generate concise, working test code."
            )
            
            return {
                "status": "success",
                "message": "Azure OpenAI connection and generation successful",
                "connection_details": connection_result,
                "generation_test": {
                    "prompt_length": len(test_prompt),
                    "response_length": len(generation_result.get('content', '')),
                    "model_used": generation_result.get('model', 'unknown'),
                    "tokens_used": generation_result.get('usage', {})
                }
            }
        else:
            return {
                "status": "error",
                "message": "Azure OpenAI connection failed",
                "details": connection_result
            }
        
    except Exception as e:
        logger.error(f"Azure OpenAI connection test failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Azure OpenAI test failed: {str(e)}",
            "suggestion": "Check your .env configuration and API credentials"
        }

@app.post("/test_ai_playwright_generation")
async def test_ai_playwright_generation():
    """
    Test AI-powered Playwright test generation
    """
    try:
        # Test with a sample TDD template
        test_tdd_template = """test_sample_login
Given: User with valid credentials admin/password123
When: The user navigates to https://example.com/login
When: The user enters username and password
When: The user clicks login button
Then: The system should redirect to dashboard
Then: The system should display welcome message"""
        
        test_cluster_config = {
            "url": "https://example.com",
            "username": "admin",
            "password": "password123"
        }
        
        # Generate using AI
        playwright_code = await playwright_generator.generate_playwright_test(
            workflow_name="sample_login_test",
            tdd_template=test_tdd_template,
            cluster_config=test_cluster_config
        )
        
        # Analyze the generated code
        analysis = {
            "generated_length": len(playwright_code),
            "contains_imports": "import" in playwright_code,
            "contains_test_function": "test(" in playwright_code,
            "contains_expect": "expect(" in playwright_code,
            "contains_page_actions": "page." in playwright_code,
            "line_count": len(playwright_code.split('\n'))
        }
        
        return {
            "status": "success",
            "message": "AI Playwright generation successful",
            "generated_code_preview": playwright_code[:500] + "..." if len(playwright_code) > 500 else playwright_code,
            "analysis": analysis,
            "full_code_length": len(playwright_code)
        }
        
    except Exception as e:
        logger.error(f"AI Playwright generation test failed: {str(e)}")
        return {
            "status": "error", 
            "message": f"AI generation test failed: {str(e)}"
        }

# Add to startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize services on startup
    """
    logger.info("Starting E2E Testing Agent Backend with Azure OpenAI...")
    
    # Initialize all services
    await instruction_parser.initialize()
    await workflow_manager.initialize()
    await template_manager.initialize()
    await playwright_generator.initialize()  # Now includes Azure OpenAI
    await test_executor.initialize()
    
    # Test Azure OpenAI connection on startup
    try:
        from services.azure_openai_service import azure_openai_service
        connection_result = await azure_openai_service.test_connection()
        if connection_result['status'] == 'success':
            logger.info(f"✅ Azure OpenAI ready: {connection_result.get('message', 'Connected')}")
        else:
            logger.warning(f"⚠️  Azure OpenAI connection issue: {connection_result.get('message', 'Unknown error')}")
    except Exception as e:
        logger.warning(f"⚠️  Azure OpenAI initialization failed: {str(e)}")
        logger.info("System will fall back to basic test generation")
    
    logger.info("All services initialized successfully with AI capabilities")

# Add to shutdown event  
@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown
    """
    logger.info("Shutting down E2E Testing Agent Backend...")
    
    # Cleanup resources
    await session_manager.cleanup_expired_sessions()
    
    # Cleanup Azure OpenAI service
    try:
        from services.azure_openai_service import azure_openai_service
        await azure_openai_service.cleanup()
    except Exception as e:
        logger.warning(f"Error cleaning up Azure OpenAI service: {e}")
    
    logger.info("Shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )