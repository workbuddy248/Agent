"""
Test Executor Service - Executes generated Playwright tests
File: backend/services/test_executor.py
"""

import logging
import asyncio
import subprocess
import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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
    """Service for executing Playwright tests"""
    
    def __init__(self, output_dir: str = "test_outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.active_executions: Dict[str, TestExecution] = {}
        
    async def execute_test_file(self, 
                               test_file_path: str, 
                               execution_id: str = None) -> TestExecution:
        """Execute a Playwright test file"""
        
        if not execution_id:
            execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        test_file = Path(test_file_path)
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file_path}")
        
        # Create execution record
        execution = TestExecution(
            execution_id=execution_id,
            test_file_path=test_file_path,
            results=[],
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            total_duration=0.0,
            started_at=datetime.now()
        )
        
        self.active_executions[execution_id] = execution
        
        try:
            # Execute the test
            await self._run_playwright_test(execution)
            execution.status = "completed"
            
        except Exception as e:
            logger.error(f"Test execution failed: {str(e)}")
            execution.status = "failed"
            
        finally:
            execution.completed_at = datetime.now()
            execution.total_duration = (
                execution.completed_at - execution.started_at
            ).total_seconds()
        
        return execution
    
    async def _run_playwright_test(self, execution: TestExecution) -> None:
        """Run the actual Playwright test"""
        
        test_file = Path(execution.test_file_path)
        output_dir = self.output_dir / execution.execution_id
        output_dir.mkdir(exist_ok=True)
        
        # Prepare Playwright command
        cmd = [
            "npx", "playwright", "test", 
            str(test_file),
            "--reporter=json",
            f"--output-dir={output_dir}",
            "--video=on",
            "--screenshot=on"
        ]
        
        try:
            # Run the test
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=test_file.parent
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse results
            if process.returncode == 0 or stdout:
                await self._parse_test_results(execution, stdout.decode(), output_dir)
            else:
                logger.error(f"Playwright execution failed: {stderr.decode()}")
                raise RuntimeError(f"Playwright execution failed: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Failed to run Playwright test: {str(e)}")
            raise
    
    async def _parse_test_results(self, 
                                 execution: TestExecution, 
                                 output: str, 
                                 output_dir: Path) -> None:
        """Parse Playwright JSON output"""
        
        try:
            # Try to parse JSON output
            if output.strip():
                results_data = json.loads(output)
                
                if "tests" in results_data:
                    for test_data in results_data["tests"]:
                        result = TestResult(
                            test_name=test_data.get("title", "Unknown Test"),
                            status=test_data.get("outcome", "unknown"),
                            duration=test_data.get("duration", 0) / 1000.0,  # Convert ms to seconds
                            error_message=test_data.get("error", {}).get("message")
                        )
                        
                        # Look for screenshots and videos
                        if "attachments" in test_data:
                            for attachment in test_data["attachments"]:
                                if attachment.get("contentType") == "image/png":
                                    result.screenshot_path = attachment.get("path")
                                elif attachment.get("contentType") == "video/webm":
                                    result.video_path = attachment.get("path")
                        
                        execution.results.append(result)
                        
                        # Update counters
                        if result.status == "passed":
                            execution.passed_tests += 1
                        elif result.status == "failed":
                            execution.failed_tests += 1
                        elif result.status == "skipped":
                            execution.skipped_tests += 1
                        
                        execution.total_tests += 1
                
        except json.JSONDecodeError:
            # Fallback: parse text output
            logger.warning("Could not parse JSON output, falling back to text parsing")
            await self._parse_text_output(execution, output)
    
    async def _parse_text_output(self, execution: TestExecution, output: str) -> None:
        """Fallback parser for text output"""
        
        lines = output.split('\n')
        current_test = None
        
        for line in lines:
            line = line.strip()
            
            # Look for test start/result patterns
            if "✓" in line or "✗" in line or "○" in line:
                if "✓" in line:
                    status = "passed"
                elif "✗" in line:
                    status = "failed"
                else:
                    status = "skipped"
                
                # Extract test name (basic pattern)
                test_name = line.replace("✓", "").replace("✗", "").replace("○", "").strip()
                
                result = TestResult(
                    test_name=test_name,
                    status=status,
                    duration=0.0  # Duration not available in text output
                )
                
                execution.results.append(result)
                
                # Update counters
                if status == "passed":
                    execution.passed_tests += 1
                elif status == "failed":
                    execution.failed_tests += 1
                elif status == "skipped":
                    execution.skipped_tests += 1
                
                execution.total_tests += 1
    
    def get_execution_status(self, execution_id: str) -> Optional[TestExecution]:
        """Get execution status"""
        return self.active_executions.get(execution_id)
    
    def list_executions(self) -> List[TestExecution]:
        """List all executions"""
        return list(self.active_executions.values())
    
    async def generate_report(self, execution_id: str) -> Dict[str, Any]:
        """Generate a test report"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        report = {
            "execution_id": execution.execution_id,
            "test_file": execution.test_file_path,
            "status": execution.status,
            "summary": {
                "total_tests": execution.total_tests,
                "passed": execution.passed_tests,
                "failed": execution.failed_tests,
                "skipped": execution.skipped_tests,
                "duration": execution.total_duration
            },
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "results": []
        }
        
        for result in execution.results:
            report["results"].append({
                "test_name": result.test_name,
                "status": result.status,
                "duration": result.duration,
                "error_message": result.error_message,
                "screenshot_path": result.screenshot_path,
                "video_path": result.video_path
            })
        
        return report
    
    async def cleanup_execution(self, execution_id: str) -> bool:
        """Clean up execution artifacts"""
        if execution_id in self.active_executions:
            # Remove from active executions
            del self.active_executions[execution_id]
            
            # Clean up output directory
            output_dir = self.output_dir / execution_id
            if output_dir.exists():
                import shutil
                shutil.rmtree(output_dir)
            
            return True
        
        return False
    
    async def initialize(self):
        """Initialize the test executor service"""
        logger.info("TestExecutorService initialized")
        pass
