"""
Enhanced Test Executor Service - Executes real or simulated Playwright tests
File: backend/services/test_executor.py
"""

import logging
import asyncio
import subprocess
import os
import json
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test execution result"""
    test_name: str
    status: str  # passed, failed, skipped
    duration: float
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    video_path: Optional[str] = None

@dataclass
class TestExecution:
    """Complete test execution details"""
    execution_id: str
    test_file_path: str
    results: List[TestResult]
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    total_duration: float
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "running"  # running, completed, failed

class TestExecutorService:
    """Enhanced service for executing Playwright tests (real or simulated)"""
    
    def __init__(self, output_dir: str = None, use_real_playwright: bool = True):
        self.output_dir = Path(output_dir or settings.TEST_OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        self.active_executions: Dict[str, TestExecution] = {}
        self.use_real_playwright = use_real_playwright
        
    async def execute_tests(self, session_id: str, playwright_tests: Dict[str, str], 
                           cluster_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute multiple Playwright tests for a session
        
        Args:
            session_id: Session identifier
            playwright_tests: Dictionary of {workflow_name: playwright_code}
            cluster_config: Cluster configuration
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Executing tests for session {session_id}: {len(playwright_tests)} test(s) (real_playwright: {self.use_real_playwright})")
        
        try:
            # Create output directory for this session
            session_output_dir = self.output_dir / session_id
            session_output_dir.mkdir(exist_ok=True)
            
            # Results storage
            execution_results = {
                "session_id": session_id,
                "success": True,
                "total_tests": len(playwright_tests),
                "passed_tests": 0,
                "failed_tests": 0,
                "test_results": {},
                "error_message": None,
                "execution_summary": [],
                "execution_mode": "real_playwright" if self.use_real_playwright else "simulation"
            }
            
            # Execute each workflow test
            for workflow_name, playwright_code in playwright_tests.items():
                logger.info(f"Executing test for workflow: {workflow_name}")
                
                try:
                    # Save test code to file
                    test_file_path = session_output_dir / f"{workflow_name}.spec.ts"
                    with open(test_file_path, 'w', encoding='utf-8') as f:
                        f.write(playwright_code)
                    
                    logger.info(f"Saved test file: {test_file_path}")
                    
                    # Execute test (real or simulated)
                    if self.use_real_playwright:
                        test_result = await self._execute_real_playwright_test(
                            workflow_name, test_file_path, cluster_config, session_output_dir
                        )
                    else:
                        test_result = await self._simulate_test_execution(
                            workflow_name, test_file_path, cluster_config
                        )
                    
                    execution_results["test_results"][workflow_name] = test_result
                    execution_results["execution_summary"].append({
                        "workflow": workflow_name,
                        "status": test_result["status"],
                        "duration": test_result.get("duration", 0),
                        "test_file": str(test_file_path),
                        "screenshot": test_result.get("screenshot_path"),
                        "video": test_result.get("video_path")
                    })
                    
                    if test_result["status"] == "passed":
                        execution_results["passed_tests"] += 1
                    else:
                        execution_results["failed_tests"] += 1
                        execution_results["success"] = False
                        
                except Exception as e:
                    logger.error(f"Failed to execute test for {workflow_name}: {str(e)}")
                    execution_results["test_results"][workflow_name] = {
                        "status": "failed",
                        "error": str(e),
                        "duration": 0
                    }
                    execution_results["failed_tests"] += 1
                    execution_results["success"] = False
            
            # Overall success if all tests passed
            if execution_results["failed_tests"] == 0:
                execution_results["success"] = True
                execution_results["message"] = f"All {len(playwright_tests)} test(s) completed successfully"
            else:
                execution_results["success"] = False
                execution_results["error_message"] = f"{execution_results['failed_tests']} test(s) failed"
            
            logger.info(f"Test execution completed for session {session_id}: {execution_results['passed_tests']} passed, {execution_results['failed_tests']} failed")
            
            return execution_results
            
        except Exception as e:
            logger.error(f"Error executing tests for session {session_id}: {str(e)}")
            return {
                "session_id": session_id,
                "success": False,
                "error_message": str(e),
                "total_tests": len(playwright_tests),
                "passed_tests": 0,
                "failed_tests": len(playwright_tests)
            }
    
    async def _execute_real_playwright_test(self, workflow_name: str, test_file_path: Path,
                                          cluster_config: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        """
        Execute real Playwright test
        
        Args:
            workflow_name: Name of the workflow being tested
            test_file_path: Path to the test file
            cluster_config: Cluster configuration
            output_dir: Output directory for results
            
        Returns:
            Real test execution result
        """
        logger.info(f"Executing real Playwright test for {workflow_name}")
        
        start_time = datetime.now()
        
        try:
            # Create playwright config file
            config_path = await self._create_playwright_config(test_file_path.parent, output_dir)
            
            # Prepare Playwright command
            cmd = [
                "npx", "playwright", "test",
                str(test_file_path),
                f"--config={config_path}",
                "--reporter=json",
                "--headed" if not settings.PLAYWRIGHT_HEADLESS else "--headless",
                f"--timeout={settings.PLAYWRIGHT_TIMEOUT}"
            ]
            
            # Set environment variables
            env = os.environ.copy()
            env.update({
                "CLUSTER_URL": cluster_config.get("url", ""),
                "CLUSTER_USERNAME": cluster_config.get("username", ""),
                "CLUSTER_PASSWORD": cluster_config.get("password", "")
            })
            
            # Execute the test
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=test_file_path.parent,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Parse results
            if process.returncode == 0:
                # Test passed
                result = {
                    "status": "passed",
                    "duration": execution_time,
                    "message": f"Real Playwright test {workflow_name} completed successfully",
                    "stdout": stdout.decode()[:1000],  # Limit output
                    "test_cases": []
                }
            else:
                # Test failed
                result = {
                    "status": "failed",
                    "duration": execution_time,
                    "error": stderr.decode()[:1000],  # Limit error output
                    "message": f"Real Playwright test {workflow_name} failed",
                    "stdout": stdout.decode()[:1000],
                    "test_cases": []
                }
            
            # Look for generated artifacts
            screenshots_dir = output_dir / "test-results"
            if screenshots_dir.exists():
                screenshots = list(screenshots_dir.glob("**/*.png"))
                if screenshots:
                    result["screenshot_path"] = str(screenshots[0])
                
                videos = list(screenshots_dir.glob("**/*.webm"))
                if videos:
                    result["video_path"] = str(videos[0])
            
            logger.info(f"Real Playwright test execution for {workflow_name}: {result['status']} in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error executing real Playwright test for {workflow_name}: {str(e)}")
            
            return {
                "status": "failed",
                "duration": execution_time,
                "error": str(e),
                "message": f"Real Playwright test {workflow_name} failed with error"
            }
    
    async def _create_playwright_config(self, test_dir: Path, output_dir: Path) -> Path:
        """Create Playwright configuration file"""
        config_content = f"""
import {{ defineConfig, devices }} from '@playwright/test';

export default defineConfig({{
  testDir: '{test_dir}',
  outputDir: '{output_dir}/test-results',
  
  // Test timeout
  timeout: {settings.PLAYWRIGHT_TIMEOUT},
  
  // Expect timeout
  expect: {{
    timeout: 10000
  }},
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Reporter to use
  reporter: [
    ['html', {{ outputFolder: '{output_dir}/html-report' }}],
    ['json', {{ outputFile: '{output_dir}/results.json' }}]
  ],
  
  // Global setup
  use: {{
    // Base URL
    baseURL: process.env.CLUSTER_URL,
    
    // Global timeout
    actionTimeout: 15000,
    navigationTimeout: 30000,
    
    // Screenshots and videos
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Trace
    trace: 'retain-on-failure',
  }},
  
  // Browser projects
  projects: [
    {{
      name: 'chromium',
      use: {{ ...devices['Desktop Chrome'] }},
    }},
  ],
  
  // Web Server (if needed)
  // webServer: {{
  //   command: 'npm run start',
  //   port: 3000,
  // }},
}});
"""
        
        config_path = test_dir / "playwright.config.ts"
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        return config_path
    
    async def _simulate_test_execution(self, workflow_name: str, test_file_path: Path, 
                                     cluster_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate test execution for POC (enhanced with Azure OpenAI-generated tests)
        
        Args:
            workflow_name: Name of the workflow being tested
            test_file_path: Path to the test file
            cluster_config: Cluster configuration
            
        Returns:
            Simulated test result
        """
        # Simulate test execution time (longer for more realistic feel)
        execution_time = random.uniform(5.0, 15.0)  # 5-15 seconds
        await asyncio.sleep(min(execution_time, 5.0))  # Cap simulation time at 5 seconds
        
        # Enhanced success rate based on workflow type
        success_rates = {
            "login_flow": 0.95,  # Login tests are usually reliable
            "network_hierarchy": 0.85,
            "inventory_workflow": 0.80,
            "fabric_creation": 0.75,  # More complex workflows have lower success rates
            "l3vn_management": 0.70,
            "fabric_settings": 0.90   # Query operations are usually reliable
        }
        
        success_rate = success_rates.get(workflow_name, 0.85)
        is_success = random.random() < success_rate
        
        if is_success:
            result = {
                "status": "passed",
                "duration": execution_time,
                "message": f"Simulated test {workflow_name} completed successfully (using Azure OpenAI generated test)",
                "test_cases": [
                    {
                        "name": f"test_valid_{workflow_name}",
                        "status": "passed",
                        "duration": execution_time / 2
                    }
                ],
                "generated_with": "azure_openai"
            }
        else:
            # Simulate realistic failure scenarios
            failure_reasons = [
                "Element not found: login button",
                "Network timeout waiting for page load",
                "Authentication failed - check credentials",
                "Navigation timeout - cluster may be unreachable",
                "Assertion failed: expected element not visible"
            ]
            
            selected_failure = random.choice(failure_reasons)
            
            result = {
                "status": "failed", 
                "duration": execution_time,
                "error": f"Simulated failure: {selected_failure}",
                "message": f"Simulated test {workflow_name} failed (using Azure OpenAI generated test)",
                "test_cases": [
                    {
                        "name": f"test_valid_{workflow_name}",
                        "status": "failed",
                        "duration": execution_time / 2,
                        "error": selected_failure
                    }
                ],
                "generated_with": "azure_openai"
            }
        
        logger.info(f"Simulated test execution for {workflow_name}: {result['status']} in {execution_time:.2f}s")
        
        return result
    
    async def test_browser_setup(self) -> Dict[str, Any]:
        """Test browser automation setup"""
        if self.use_real_playwright:
            try:
                # Test if Playwright is installed
                process = await asyncio.create_subprocess_exec(
                    "npx", "playwright", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    version = stdout.decode().strip()
                    return {
                        "status": "success",
                        "message": f"Real Playwright ready: {version}",
                        "timestamp": datetime.now().isoformat(),
                        "mode": "real_playwright"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Playwright not properly installed: {stderr.decode()}",
                        "timestamp": datetime.now().isoformat(),
                        "mode": "real_playwright"
                    }
                    
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error checking Playwright: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "mode": "real_playwright"
                }
        else:
            return {
                "status": "success",
                "message": "Test executor service ready (enhanced simulation mode with Azure OpenAI)",
                "timestamp": datetime.now().isoformat(),
                "mode": "enhanced_simulation"
            }
    
    def toggle_real_playwright(self, enabled: bool = True):
        """Toggle between real Playwright execution and simulation"""
        self.use_real_playwright = enabled
        mode = "real Playwright" if enabled else "enhanced simulation"
        logger.info(f"Test execution mode switched to: {mode}")
    
    # Keep all existing methods for backward compatibility...
    # [Previous methods remain the same]
    
    async def initialize(self):
        """Initialize the test executor service"""
        mode = "real Playwright" if self.use_real_playwright else "enhanced simulation with Azure OpenAI"
        logger.info(f"TestExecutorService initialized in {mode} mode")