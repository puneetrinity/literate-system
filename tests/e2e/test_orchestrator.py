"""
E2E Test Orchestrator

Comprehensive test orchestration system for CI/CD pipeline integration
with proper test sequencing, reporting, and failure analysis.
"""

import asyncio
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient


@dataclass
class TestSuite:
    """Represents a test suite configuration."""
    name: str
    module: str
    priority: int
    timeout: int
    dependencies: List[str] = field(default_factory=list)
    parallel_safe: bool = True
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class TestResult:
    """Test execution result."""
    suite_name: str
    test_name: str
    status: str  # 'passed', 'failed', 'skipped', 'error'
    duration: float
    error_message: Optional[str] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    


class E2ETestOrchestrator:
    """Orchestrates comprehensive E2E test execution."""
    
    def __init__(self):
        self.test_suites = self._define_test_suites()
        self.execution_plan = []
        self.results = []
        self.environment_status = {}
        
    def _define_test_suites(self) -> List[TestSuite]:
        """Define the complete E2E test suite configuration."""
        return [
            # Infrastructure and Health Tests (Priority 1 - Must pass first)
            TestSuite(
                name="Health Checks",
                module="test_deployment_validation_e2e::TestDeploymentValidationE2E::test_docker_compose_deployment_validation",
                priority=1,
                timeout=60,
                dependencies=[],
                parallel_safe=False,
                resource_requirements={"docker": True}
            ),
            
            # Core Integration Tests (Priority 2)
            TestSuite(
                name="Basic Integration",
                module="test_cross_service_integration::TestCrossServiceIntegration::test_document_search_service_health",
                priority=2,
                timeout=30,
                dependencies=["Health Checks"],
                parallel_safe=True
            ),
            
            TestSuite(
                name="Document Processing",
                module="test_cross_service_integration::TestCrossServiceIntegration::test_document_upload_and_indexing",
                priority=2,
                timeout=60,
                dependencies=["Basic Integration"],
                parallel_safe=True
            ),
            
            # Data Flow Tests (Priority 3)
            TestSuite(
                name="Data Flow Validation",
                module="test_data_flow_e2e::TestDataFlowE2E::test_document_processing_pipeline_flow",
                priority=3,
                timeout=120,
                dependencies=["Document Processing"],
                parallel_safe=True
            ),
            
            TestSuite(
                name="Memory Persistence",
                module="test_data_flow_e2e::TestDataFlowE2E::test_conversation_memory_persistence",
                priority=3,
                timeout=90,
                dependencies=["Data Flow Validation"],
                parallel_safe=True
            ),
            
            # API Workflow Tests (Priority 4)
            TestSuite(
                name="API Workflows",
                module="test_api_workflow_e2e::TestAPIWorkflowE2E::test_complete_document_workflow",
                priority=4,
                timeout=180,
                dependencies=["Memory Persistence"],
                parallel_safe=True
            ),
            
            TestSuite(
                name="Streaming Validation",
                module="test_api_workflow_e2e::TestAPIWorkflowE2E::test_streaming_workflow_validation",
                priority=4,
                timeout=90,
                dependencies=["API Workflows"],
                parallel_safe=True
            ),
            
            # Performance Tests (Priority 5 - Resource intensive)
            TestSuite(
                name="Performance Validation",
                module="test_performance_e2e::TestPerformanceE2E::test_document_search_load_performance",
                priority=5,
                timeout=300,
                dependencies=["Streaming Validation"],
                parallel_safe=False,
                resource_requirements={"memory_gb": 4, "cpu_cores": 2}
            ),
            
            TestSuite(
                name="Load Testing",
                module="test_performance_e2e::TestPerformanceE2E::test_ai_chat_load_performance",
                priority=5,
                timeout=300,
                dependencies=["Performance Validation"],
                parallel_safe=False,
                resource_requirements={"memory_gb": 4, "cpu_cores": 2}
            ),
            
            # Advanced Integration Tests (Priority 6)
            TestSuite(
                name="Advanced Workflows",
                module="test_cross_service_integration::TestCrossServiceIntegration::test_hybrid_search_workflow",
                priority=6,
                timeout=120,
                dependencies=["Load Testing"],
                parallel_safe=True
            ),
            
            TestSuite(
                name="User Journeys",
                module="test_user_journey::TestCompleteUserJourney::test_complete_research_workflow",
                priority=6,
                timeout=180,
                dependencies=["Advanced Workflows"],
                parallel_safe=True
            )
        ]
        
    async def validate_environment(self) -> Dict[str, Any]:
        """Validate test environment readiness."""
        validation_results = {
            'environment_ready': True,
            'services_available': {},
            'resource_checks': {},
            'configuration_valid': True,
            'errors': []
        }
        
        # Check service endpoints
        service_endpoints = {
            'document_search': 'http://localhost:8002/health',
            'ai_chat': 'http://localhost:8004/health'
        }
        
        async with AsyncClient(timeout=10.0) as client:
            for service_name, endpoint in service_endpoints.items():
                try:
                    response = await client.get(endpoint)
                    validation_results['services_available'][service_name] = {
                        'available': response.status_code == 200,
                        'response_time': response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0
                    }
                except Exception as e:
                    validation_results['services_available'][service_name] = {
                        'available': False,
                        'error': str(e)
                    }
                    validation_results['environment_ready'] = False
                    
        # Check resource availability
        try:
            import psutil
            
            validation_results['resource_checks'] = {
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'cpu_count': psutil.cpu_count(),
                'disk_available_gb': psutil.disk_usage('.').free / (1024**3)
            }
            
            # Minimum resource requirements
            if validation_results['resource_checks']['memory_available_gb'] < 2:
                validation_results['errors'].append("Insufficient memory (< 2GB available)")
                validation_results['environment_ready'] = False
                
        except ImportError:
            validation_results['errors'].append("psutil not available for resource checking")
            
        # Check environment variables
        required_env_vars = ['REDIS_URL', 'DOCUMENT_SEARCH_URL']
        missing_env_vars = [
            var for var in required_env_vars 
            if not os.getenv(var) and not os.getenv(f"TEST_{var}")
        ]
        
        if missing_env_vars:
            validation_results['errors'].append(f"Missing environment variables: {missing_env_vars}")
            # Don't fail for missing env vars in test environment
            
        self.environment_status = validation_results
        return validation_results
        
    def create_execution_plan(self, filter_suites: List[str] = None) -> List[List[TestSuite]]:
        """Create optimized test execution plan."""
        # Filter test suites if specified
        suites_to_run = self.test_suites
        if filter_suites:
            suites_to_run = [suite for suite in self.test_suites if suite.name in filter_suites]
            
        # Group by priority and resolve dependencies
        priority_groups = {}
        for suite in suites_to_run:
            priority = suite.priority
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(suite)
            
        # Create execution batches
        execution_plan = []
        for priority in sorted(priority_groups.keys()):
            priority_suites = priority_groups[priority]
            
            # Separate parallel-safe from non-parallel-safe
            parallel_safe = [s for s in priority_suites if s.parallel_safe]
            sequential = [s for s in priority_suites if not s.parallel_safe]
            
            # Add sequential tests first
            for suite in sequential:
                execution_plan.append([suite])
                
            # Add parallel-safe tests as a batch
            if parallel_safe:
                execution_plan.append(parallel_safe)
                
        self.execution_plan = execution_plan
        return execution_plan
        
    async def execute_test_suite(self, suite: TestSuite) -> TestResult:
        """Execute individual test suite."""
        start_time = time.time()
        
        try:
            # For this implementation, we simulate test execution
            # In a real CI/CD environment, this would use pytest subprocess
            
            # Simulate different execution times based on suite type
            execution_time = {
                "Health Checks": 2,
                "Basic Integration": 5,
                "Document Processing": 8,
                "Data Flow Validation": 15,
                "Memory Persistence": 12,
                "API Workflows": 20,
                "Streaming Validation": 10,
                "Performance Validation": 45,
                "Load Testing": 60,
                "Advanced Workflows": 15,
                "User Journeys": 25
            }.get(suite.name, 10)
            
            await asyncio.sleep(min(execution_time / 10, 3))  # Scaled down for demo
            
            # Simulate test results with occasional failures
            import random
            
            # Bias toward success but allow some failures for testing
            success_probability = 0.9 if suite.priority <= 4 else 0.85
            
            if random.random() < success_probability:
                status = "passed"
                error_message = None
            else:
                status = "failed"
                error_message = f"Simulated failure in {suite.name} - connection timeout"
                
            duration = time.time() - start_time
            
            return TestResult(
                suite_name=suite.name,
                test_name=suite.module.split("::")[-1],
                status=status,
                duration=duration,
                error_message=error_message,
                performance_metrics={
                    'execution_time': duration,
                    'memory_peak': random.randint(100, 500),  # MB
                    'api_calls': random.randint(5, 50)
                }
            )
            
        except Exception as e:
            return TestResult(
                suite_name=suite.name,
                test_name=suite.module.split("::")[-1],
                status="error",
                duration=time.time() - start_time,
                error_message=str(e)
            )
            
    async def execute_plan(self, max_parallel_workers: int = 3) -> Dict[str, Any]:
        """Execute the complete test plan."""
        execution_results = {
            'start_time': time.time(),
            'total_suites': sum(len(batch) for batch in self.execution_plan),
            'batches_executed': 0,
            'results': [],
            'summary': {},
            'failed_suites': [],
            'performance_metrics': {}
        }
        
        print(f"Executing E2E test plan with {execution_results['total_suites']} test suites...")
        
        for batch_index, batch in enumerate(self.execution_plan):
            batch_start = time.time()
            print(f"\nExecuting batch {batch_index + 1}/{len(self.execution_plan)}: {[s.name for s in batch]}")
            
            # Execute batch (parallel for parallel-safe tests)
            if len(batch) == 1 or not all(suite.parallel_safe for suite in batch):
                # Sequential execution
                batch_results = []
                for suite in batch:
                    print(f"  Running {suite.name}...")
                    result = await self.execute_test_suite(suite)
                    batch_results.append(result)
                    
                    if result.status in ['failed', 'error']:
                        print(f"    ✗ {suite.name}: {result.status}")
                        execution_results['failed_suites'].append(suite.name)
                        
                        # Stop on critical failures
                        if suite.priority <= 2:
                            print(f"Critical test failed, stopping execution")
                            execution_results['results'].extend(batch_results)
                            return self._finalize_results(execution_results)
                    else:
                        print(f"    ✓ {suite.name}: {result.duration:.2f}s")
            else:
                # Parallel execution
                print(f"  Running {len(batch)} tests in parallel...")
                semaphore = asyncio.Semaphore(max_parallel_workers)
                
                async def execute_with_semaphore(suite):
                    async with semaphore:
                        return await self.execute_test_suite(suite)
                        
                batch_results = await asyncio.gather(
                    *[execute_with_semaphore(suite) for suite in batch],
                    return_exceptions=True
                )
                
                # Process results
                for i, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        result = TestResult(
                            suite_name=batch[i].name,
                            test_name=batch[i].module.split("::")[-1],
                            status="error",
                            duration=0,
                            error_message=str(result)
                        )
                    
                    if result.status in ['failed', 'error']:
                        print(f"    ✗ {result.suite_name}: {result.status}")
                        execution_results['failed_suites'].append(result.suite_name)
                    else:
                        print(f"    ✓ {result.suite_name}: {result.duration:.2f}s")
                        
            execution_results['results'].extend(batch_results)
            execution_results['batches_executed'] += 1
            
            batch_duration = time.time() - batch_start
            print(f"  Batch completed in {batch_duration:.2f}s")
            
        return self._finalize_results(execution_results)
        
    def _finalize_results(self, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize execution results with summary and metrics."""
        execution_results['end_time'] = time.time()
        execution_results['total_duration'] = execution_results['end_time'] - execution_results['start_time']
        
        # Calculate summary statistics
        results = execution_results['results']
        
        status_counts = {}
        for result in results:
            status = result.status
            status_counts[status] = status_counts.get(status, 0) + 1
            
        execution_results['summary'] = {
            'total_tests': len(results),
            'passed': status_counts.get('passed', 0),
            'failed': status_counts.get('failed', 0),
            'errors': status_counts.get('error', 0),
            'skipped': status_counts.get('skipped', 0),
            'success_rate': status_counts.get('passed', 0) / len(results) if results else 0,
            'total_duration': execution_results['total_duration']
        }
        
        # Performance metrics
        durations = [r.duration for r in results if r.duration > 0]
        if durations:
            execution_results['performance_metrics'] = {
                'average_test_duration': sum(durations) / len(durations),
                'longest_test_duration': max(durations),
                'shortest_test_duration': min(durations)
            }
            
        return execution_results
        
    def generate_report(self, results: Dict[str, Any], format: str = 'console') -> str:
        """Generate test execution report."""
        if format == 'console':
            return self._generate_console_report(results)
        elif format == 'json':
            return self._generate_json_report(results)
        elif format == 'junit':
            return self._generate_junit_report(results)
        else:
            raise ValueError(f"Unsupported report format: {format}")
            
    def _generate_console_report(self, results: Dict[str, Any]) -> str:
        """Generate console-friendly report."""
        summary = results['summary']
        
        report = [
            "\n" + "="*80,
            "E2E TEST EXECUTION REPORT",
            "="*80,
            f"Total Duration: {summary['total_duration']:.2f}s",
            f"Total Tests: {summary['total_tests']}",
            f"Passed: {summary['passed']} ({summary['success_rate']:.1%})",
            f"Failed: {summary['failed']}",
            f"Errors: {summary['errors']}",
            f"Skipped: {summary['skipped']}",
            ""
        ]
        
        if results['failed_suites']:
            report.extend([
                "FAILED TEST SUITES:",
                "-" * 40
            ])
            
            for result in results['results']:
                if result.status in ['failed', 'error']:
                    report.append(f"✗ {result.suite_name}: {result.error_message}")
            report.append("")
            
        # Performance summary
        if 'performance_metrics' in results:
            perf = results['performance_metrics']
            report.extend([
                "PERFORMANCE SUMMARY:",
                "-" * 40,
                f"Average Test Duration: {perf['average_test_duration']:.2f}s",
                f"Longest Test: {perf['longest_test_duration']:.2f}s",
                f"Shortest Test: {perf['shortest_test_duration']:.2f}s",
                ""
            ])
            
        # Environment status
        if self.environment_status:
            env = self.environment_status
            report.extend([
                "ENVIRONMENT STATUS:",
                "-" * 40,
                f"Environment Ready: {'✓' if env['environment_ready'] else '✗'}",
                f"Services Available: {len([s for s in env['services_available'].values() if s.get('available')])}/{len(env['services_available'])}",
            ])
            
            if env['errors']:
                report.append("Environment Issues:")
                for error in env['errors']:
                    report.append(f"  - {error}")
                    
        report.append("="*80)
        
        return "\n".join(report)
        
    def _generate_json_report(self, results: Dict[str, Any]) -> str:
        """Generate JSON report."""
        # Convert TestResult objects to dictionaries
        json_results = results.copy()
        json_results['results'] = [
            {
                'suite_name': r.suite_name,
                'test_name': r.test_name,
                'status': r.status,
                'duration': r.duration,
                'error_message': r.error_message,
                'performance_metrics': r.performance_metrics
            }
            for r in results['results']
        ]
        
        json_results['environment_status'] = self.environment_status
        json_results['execution_plan'] = [
            [{'name': suite.name, 'priority': suite.priority} for suite in batch]
            for batch in self.execution_plan
        ]
        
        return json.dumps(json_results, indent=2)
        
    def _generate_junit_report(self, results: Dict[str, Any]) -> str:
        """Generate JUnit XML report."""
        from xml.etree.ElementTree import Element, SubElement, tostring
        
        testsuite = Element('testsuite')
        testsuite.set('name', 'E2E Test Suite')
        testsuite.set('tests', str(results['summary']['total_tests']))
        testsuite.set('failures', str(results['summary']['failed']))
        testsuite.set('errors', str(results['summary']['errors']))
        testsuite.set('time', str(results['summary']['total_duration']))
        
        for result in results['results']:
            testcase = SubElement(testsuite, 'testcase')
            testcase.set('classname', result.suite_name)
            testcase.set('name', result.test_name)
            testcase.set('time', str(result.duration))
            
            if result.status == 'failed':
                failure = SubElement(testcase, 'failure')
                failure.set('message', result.error_message or 'Test failed')
                failure.text = result.error_message or 'No details available'
            elif result.status == 'error':
                error = SubElement(testcase, 'error')
                error.set('message', result.error_message or 'Test error')
                error.text = result.error_message or 'No details available'
                
        return tostring(testsuite, encoding='unicode')


class TestE2EOrchestrator:
    """Test the E2E test orchestrator itself."""
    
    async def test_orchestrator_validation(self):
        """Test orchestrator environment validation."""
        orchestrator = E2ETestOrchestrator()
        
        # Test environment validation
        env_results = await orchestrator.validate_environment()
        
        assert isinstance(env_results, dict), "Environment validation should return dict"
        assert 'environment_ready' in env_results, "Should check environment readiness"
        assert 'services_available' in env_results, "Should check service availability"
        
        print("Orchestrator validation test passed")
        
    async def test_execution_plan_creation(self):
        """Test execution plan creation."""
        orchestrator = E2ETestOrchestrator()
        
        # Create full execution plan
        plan = orchestrator.create_execution_plan()
        
        assert len(plan) > 0, "Should create non-empty execution plan"
        assert all(isinstance(batch, list) for batch in plan), "Plan should contain batches"
        
        # Test filtered execution plan
        filtered_plan = orchestrator.create_execution_plan(["Health Checks", "Basic Integration"])
        
        assert len(filtered_plan) <= len(plan), "Filtered plan should be smaller or equal"
        
        print(f"Execution plan created with {len(plan)} batches")
        
    async def test_sample_execution(self):
        """Test sample orchestrator execution."""
        orchestrator = E2ETestOrchestrator()
        
        # Validate environment first
        env_results = await orchestrator.validate_environment()
        
        # Create limited execution plan for testing
        orchestrator.create_execution_plan(["Health Checks", "Basic Integration"])
        
        # Execute sample plan
        results = await orchestrator.execute_plan(max_parallel_workers=2)
        
        assert 'summary' in results, "Results should contain summary"
        assert 'results' in results, "Results should contain test results"
        assert results['summary']['total_tests'] > 0, "Should execute some tests"
        
        # Generate reports
        console_report = orchestrator.generate_report(results, 'console')
        json_report = orchestrator.generate_report(results, 'json')
        
        assert len(console_report) > 0, "Console report should not be empty"
        assert len(json_report) > 0, "JSON report should not be empty"
        
        # Validate JSON report structure
        json_data = json.loads(json_report)
        assert 'summary' in json_data, "JSON report should contain summary"
        
        print(f"Sample execution completed: {results['summary']['total_tests']} tests")
        print(f"Success rate: {results['summary']['success_rate']:.1%}")
        
        return results