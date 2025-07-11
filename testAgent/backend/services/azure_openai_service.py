"""
Azure OpenAI Service Client with Cisco IDP Authentication - Uses LangChain AzureChatOpenAI
File: backend/services/azure_openai_service.py
"""

import logging
import asyncio
import json
import base64
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from core.config import settings

logger = logging.getLogger(__name__)

class AzureOpenAIService:
    """Service for interacting with Azure OpenAI API using Cisco IDP authentication"""
    
    def __init__(self):
        # Cisco IDP Authentication settings
        self.client_id = settings.AZURE_CLIENT_ID
        self.client_secret = settings.AZURE_CLIENT_SECRET
        self.app_key = settings.AZURE_OPENAI_APP_KEY
        self.cisco_idp = settings.CISCO_IDP
        
        # Azure OpenAI settings
        self.azure_endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.api_version = settings.AZURE_OPENAI_API_VERSION
        self.model = settings.AZURE_OPENAI_MODEL
        
        # Service configuration
        self.max_retries = settings.MAX_RETRIES
        self.request_timeout = settings.REQUEST_TIMEOUT
        self.temperature = settings.GENERATION_TEMPERATURE
        
        # Authentication state
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.llm: Optional[AzureChatOpenAI] = None
        
        # Session for async HTTP requests
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize the Azure OpenAI service with Cisco IDP authentication"""
        logger.info("Initializing Azure OpenAI service with Cisco IDP authentication...")
        
        # Create HTTP session
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        
        # Authenticate and initialize LLM
        await self._authenticate_and_initialize_llm()
        
        # Test connection
        await self.test_connection()
        logger.info("Azure OpenAI service with Cisco IDP authentication initialized successfully")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _authenticate_and_initialize_llm(self):
        """Authenticate with Cisco IDP and initialize Azure OpenAI LLM"""
        try:
            logger.info("Authenticating with Cisco IDP...")
            
            # Prepare authentication payload
            payload = "grant_type=client_credentials"
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            
            headers = {
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded_credentials}"
            }
            
            # Make authentication request (using requests for sync call)
            token_response = requests.post(
                self.cisco_idp, 
                headers=headers, 
                data=payload,
                timeout=self.request_timeout
            )
            
            if token_response.status_code != 200:
                raise Exception(f"Failed to fetch token from Cisco IDP: {token_response.text}")
            
            token_data = token_response.json()
            self.access_token = token_data.get("access_token")
            
            if not self.access_token:
                raise Exception("No access token returned from Cisco IDP.")
            
            # Calculate token expiration (assuming 1 hour if not provided)
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
            
            logger.info("Successfully authenticated with Cisco IDP")
            
            # Initialize Azure OpenAI LLM with the token
            self._initialize_llm()
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Cisco IDP: {str(e)}")
            raise
    
    def _initialize_llm(self):
        """Initialize the Azure OpenAI LLM with current access token"""
        try:
            self.llm = AzureChatOpenAI(
                deployment_name=self.model,
                azure_endpoint=self.azure_endpoint,
                api_key=self.access_token,
                api_version=self.api_version,
                temperature=self.temperature,
                model_kwargs={
                    "user": json.dumps({"appkey": self.app_key})
                }
            )
            
            logger.info(f"Initialized Azure OpenAI LLM with model: {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI LLM: {str(e)}")
            raise
    
    async def _ensure_valid_token(self):
        """Ensure we have a valid access token, refresh if needed"""
        if not self.access_token or not self.token_expires_at:
            await self._authenticate_and_initialize_llm()
            return
        
        # Check if token is about to expire
        if datetime.now() >= self.token_expires_at:
            logger.info("Access token expired, refreshing...")
            await self._authenticate_and_initialize_llm()
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Azure OpenAI with Cisco IDP authentication"""
        try:
            await self._ensure_valid_token()
            
            # Simple test prompt
            test_response = await self.generate_completion(
                prompt="Test connection. Respond with 'OK'.",
                max_tokens=10
            )
            
            if test_response and test_response.get("content"):
                return {
                    "status": "success",
                    "message": "Azure OpenAI connection with Cisco IDP authentication successful",
                    "timestamp": datetime.now().isoformat(),
                    "endpoint": self.azure_endpoint,
                    "model": self.model,
                    "authentication": "cisco_idp",
                    "app_key": self.app_key
                }
            else:
                raise Exception("No response from Azure OpenAI API")
                
        except Exception as e:
            logger.error(f"Azure OpenAI connection test failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "authentication": "cisco_idp"
            }
    
    async def generate_completion(self, prompt: str, max_tokens: int = 8000, 
                                system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate completion using Azure OpenAI with Cisco IDP authentication
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            system_prompt: System prompt (optional)
            
        Returns:
            Dictionary with response content and metadata
        """
        await self._ensure_valid_token()
        
        for attempt in range(self.max_retries):
            try:
                # Prepare messages
                messages = []
                if system_prompt:
                    messages.append(SystemMessage(content=system_prompt))
                messages.append(HumanMessage(content=prompt))
                
                # Make the API call using LangChain
                logger.info(f"Generating completion with Azure OpenAI (attempt {attempt + 1})")
                
                response = await asyncio.to_thread(
                    self.llm.invoke,
                    messages,
                    max_tokens=max_tokens
                )
                
                # Extract response content
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Get usage information if available
                usage_info = {}
                if hasattr(response, 'response_metadata'):
                    usage_info = response.response_metadata.get('token_usage', {})
                
                return {
                    "content": content,
                    "usage": usage_info,
                    "model": self.model,
                    "timestamp": datetime.now().isoformat(),
                    "attempt": attempt + 1,
                    "authentication": "cisco_idp"
                }
                
            except Exception as e:
                logger.warning(f"API call attempt {attempt + 1} failed: {str(e)}")
                
                # If it's an authentication error, try to refresh token
                if "unauthorized" in str(e).lower() or "invalid" in str(e).lower():
                    logger.info("Authentication error detected, refreshing token...")
                    await self._authenticate_and_initialize_llm()
                
                if attempt == self.max_retries - 1:
                    raise
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
    
    async def generate_playwright_test(self, tdd_template: str, cluster_config: Dict[str, Any],
                                     workflow_name: str) -> str:
        """
        Generate Playwright test using Azure OpenAI with Cisco IDP authentication
        
        Args:
            tdd_template: TDD template content
            cluster_config: Cluster configuration
            workflow_name: Name of the workflow
            
        Returns:
            Generated Playwright TypeScript test code
        """
        try:
            # Load the playwright prompt template
            from services.template_manager import TemplateManagerService
            template_manager = TemplateManagerService()
            prompt_template = await template_manager.get_playwright_prompt_template()
            
            # Format the prompt with actual values
            formatted_prompt = prompt_template.format(
                tdd_template=tdd_template,
                cluster_url=cluster_config.get("url", ""),
                username=cluster_config.get("username", ""),
                password=cluster_config.get("password", "")
            )
            
            system_prompt = f"""Create playwright test for the java-based enterprise microservices application built using Spring Framework with Maven for dependency management for the URL: https://172.27.248.237/
Test specs should be created based on the *.tdd files in the folder: /Users/varsaraf/Downloads/Agent/TESTAGENT/backend/templates/*
Read the creds.json for fetching the username and password for valid and invalid scenarios
Use multiple selector strategies (aria-label, data-test-name, data-test-id, CSS selectors, text content) to robustly find elements
Add appropriate timeout settings in the Playwright config:
- Set global timeout to 600 seconds
- Set action timeout to 300 seconds
- Set navigation timeout to 300 seconds
Implement retry logic for flaky actions like button clicks
Add detailed logging throughout the test for better debugging
Implement graceful error handling to make tests more resilient to timing issues
Take screenshots at key points for debugging failures
Configure Playwright to record videos and traces on test failures
Generate the code and save it in /Users/varsaraf/Downloads/Agent/TESTAGENT/e2e folder.
Put all the playwright configs in a separate folder/file in this Users/varsaraf/Downloads/Agent/TESTAGENT/e2e folder.
Save the navigate, click, text input, and similar others in a separate utils file to reuse that as well in Users/varsaraf/Downloads/Agent/TESTAGENT/e2e folder.
Save the login related code in a separate common folder in the /Users/varsaraf/evpn/evpn-fabric/e2e folder, so that it can be reused."""
            
            logger.info(f"Generating Playwright test for {workflow_name} using Azure OpenAI with Cisco IDP...")
            
            response = await self.generate_completion(
                prompt=formatted_prompt,
                max_tokens=4000,
                system_prompt=system_prompt
            )
            
            playwright_code = response["content"]
            
            # Clean up the generated code
            playwright_code = self._clean_generated_code(playwright_code)
            
            logger.info(f"Generated Playwright test for {workflow_name}: {len(playwright_code)} characters")
            
            return playwright_code
            
        except Exception as e:
            logger.error(f"Failed to generate Playwright test for {workflow_name}: {str(e)}")
            raise
    
    def _clean_generated_code(self, code: str) -> str:
        """Clean up generated code"""
        # Remove markdown code block markers if present
        if "```typescript" in code:
            code = code.split("```typescript")[1].split("```")[0]
        elif "```ts" in code:
            code = code.split("```ts")[1].split("```")[0]
        elif "```javascript" in code:
            code = code.split("```javascript")[1].split("```")[0]
        elif "```" in code:
            # Generic code block
            parts = code.split("```")
            if len(parts) >= 3:
                code = parts[1]
        
        # Clean up extra whitespace
        code = code.strip()
        
        # Ensure proper imports if missing
        if "import" not in code and "test(" in code:
            imports = "import { test, expect, Page } from '@playwright/test';\n\n"
            code = imports + code
        
        return code
    
    async def get_token_info(self) -> Dict[str, Any]:
        """Get current token information for debugging"""
        return {
            "has_token": bool(self.access_token),
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "time_until_expiry": str(self.token_expires_at - datetime.now()) if self.token_expires_at else None,
            "cisco_idp_endpoint": self.cisco_idp,
            "azure_endpoint": self.azure_endpoint,
            "model": self.model,
            "app_key": self.app_key
        }

# Global instance
azure_openai_service = AzureOpenAIService()