#!/usr/bin/env python3
"""
Comprehensive E2E Test Runner

A comprehensive test runner for the unified AI system E2E tests with support for
various execution modes, reporting, and CI/CD integration.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional


class E2ETestRunner:
    """Comprehensive E2E test runner with orchestration capabilities."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.tests_dir = self.project_root / "tests" / "e2e"
        self.results_dir = self.project_root / "test-results"
        
    def setup_environment(self) -> Dict[str, Any]:
        """Set up test environment and validate prerequisites."""
        print("🔧 Setting up E2E test environment...")
        
        setup_results = {
            'environment_ready': True,
            'prerequisites': {},
            'services': {},
            'errors': []
        }
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            setup_results['errors'].append(f"Python 3.8+ required, got {python_version.major}.{python_version.minor}")
            setup_results['environment_ready'] = False
        else:
            setup_results['prerequisites']['python'] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
            
        # Check required packages
        required_packages = [
            'pytest', 'pytest-asyncio', 'httpx', 'docker', 
            'redis', 'psutil', 'aiofiles', 'pyyaml'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                setup_results['prerequisites'][package] = '✓'
            except ImportError:
                missing_packages.append(package)
                setup_results['prerequisites'][package] = '✗'
                
        if missing_packages:
            setup_results['errors'].append(f"Missing packages: {', '.join(missing_packages)}")
            setup_results['environment_ready'] = False
            
        # Check Docker availability
        try:
            import docker
            client = docker.from_env()
            client.ping()
            setup_results['prerequisites']['docker'] = '✓'
        except Exception as e:
            setup_results['prerequisites']['docker'] = f'✗ ({str(e)[:50]}...)'
            setup_results['errors'].append(f"Docker not available: {e}")
            
        # Create results directory
        self.results_dir.mkdir(exist_ok=True)
        
        return setup_results
        
    def install_dependencies(self) -> bool:
        """Install required dependencies."""
        print("📦 Installing dependencies...")
        
        try:
            # Install E2E test requirements
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "pytest", "pytest-asyncio", "httpx", "docker",
                "redis", "psutil", "aiofiles", "pyyaml"
            ], check=True, capture_output=True)
            
            print("✓ Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies: {e}")
            return False
            
    def run_test_suite(
        self, 
        suite_name: str, 
        test_pattern: str = None, 
        timeout: int = 300,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """Run a specific test suite."""
        print(f"🧪 Running test suite: {suite_name}")
        
        # Prepare pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.tests_dir),
            f"--timeout={timeout}",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
            
        if test_pattern:
            cmd.extend(["-k", test_pattern])
            
        # Add markers based on suite name
        suite_markers = {
            'health': 'health',
            'integration': 'integration',
            'performance': 'performance',
            'data_flow': 'data_flow', 
            'api_workflow': 'api_workflow',
            'deployment': 'deployment'
        }
        
        if suite_name in suite_markers:
            cmd.extend(["-m", suite_markers[suite_name]])
            
        # Add JUnit XML output
        junit_file = self.results_dir / f"{suite_name}_results.xml"
        cmd.extend(["--junitxml", str(junit_file)])
        
        # Add JSON report output
        json_file = self.results_dir / f"{suite_name}_results.json"
        cmd.extend(["--json-report", f"--json-report-file={json_file}"])
        
        # Execute tests
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout + 60  # Add buffer to pytest timeout
            )
            
            duration = time.time() - start_time
            
            return {
                'suite_name': suite_name,
                'status': 'passed' if result.returncode == 0 else 'failed',
                'duration': duration,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'junit_file': str(junit_file) if junit_file.exists() else None,
                'json_file': str(json_file) if json_file.exists() else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                'suite_name': suite_name,
                'status': 'timeout',
                'duration': timeout,
                'return_code': -1,
                'error': f'Test suite timed out after {timeout}s'
            }
        except Exception as e:
            return {
                'suite_name': suite_name,
                'status': 'error',
                'duration': time.time() - start_time,
                'return_code': -1,
                'error': str(e)
            }
            
    def run_orchestrated_tests(self, filter_suites: List[str] = None) -> Dict[str, Any]:
        """Run orchestrated test execution."""
        print("🎭 Running orchestrated E2E tests...")
        
        # Import and run the orchestrator
        sys.path.insert(0, str(self.tests_dir))
        
        try:
            from test_orchestrator import E2ETestOrchestrator
            
            orchestrator = E2ETestOrchestrator()
            
            # Validate environment
            env_validation = asyncio.run(orchestrator.validate_environment())
            
            if not env_validation['environment_ready']:
                return {
                    'status': 'failed',
                    'error': 'Environment validation failed',
                    'validation_results': env_validation
                }
                
            # Create execution plan
            orchestrator.create_execution_plan(filter_suites)
            
            # Execute tests
            results = asyncio.run(orchestrator.execute_plan())
            
            # Generate reports
            console_report = orchestrator.generate_report(results, 'console')
            json_report = orchestrator.generate_report(results, 'json')
            
            # Save reports
            (self.results_dir / "orchestration_report.txt").write_text(console_report)
            (self.results_dir / "orchestration_report.json").write_text(json_report)
            
            print(console_report)
            
            return {
                'status': 'completed',
                'orchestration_results': results,
                'environment_validation': env_validation,
                'reports': {
                    'console': str(self.results_dir / "orchestration_report.txt"),
                    'json': str(self.results_dir / "orchestration_report.json")
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def generate_summary_report(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        summary = {
            'timestamp': time.time(),
            'total_suites': len(all_results),
            'passed_suites': len([r for r in all_results if r.get('status') == 'passed']),
            'failed_suites': len([r for r in all_results if r.get('status') == 'failed']),
            'error_suites': len([r for r in all_results if r.get('status') == 'error']),
            'timeout_suites': len([r for r in all_results if r.get('status') == 'timeout']),
            'total_duration': sum(r.get('duration', 0) for r in all_results),
            'success_rate': 0,
            'results': all_results
        }
        
        if summary['total_suites'] > 0:
            summary['success_rate'] = summary['passed_suites'] / summary['total_suites']
            
        # Save summary
        summary_file = self.results_dir / "test_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        return summary
        
    def print_summary(self, summary: Dict[str, Any]):
        """Print test execution summary."""
        print("\n" + "="*80)
        print("🏁 E2E TEST EXECUTION SUMMARY")
        print("="*80)
        print(f"Total Test Suites: {summary['total_suites']}")
        print(f"Passed: {summary['passed_suites']} ✓")
        print(f"Failed: {summary['failed_suites']} ✗")
        print(f"Errors: {summary['error_suites']} ⚠")
        print(f"Timeouts: {summary['timeout_suites']} ⏰")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Total Duration: {summary['total_duration']:.1f}s")
        print("="*80)
        
        # Show failed suites
        failed_results = [r for r in summary['results'] if r.get('status') != 'passed']
        if failed_results:
            print("\n❌ FAILED SUITES:")
            for result in failed_results:
                print(f"  - {result['suite_name']}: {result.get('status', 'unknown')}")
                if 'error' in result:
                    print(f"    Error: {result['error']}")
                    
        print(f"\n📊 Results saved to: {self.results_dir}")


def main():
    """Main entry point for E2E test runner."""
    parser = argparse.ArgumentParser(
        description="Comprehensive E2E Test Runner for Unified AI System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all E2E tests with orchestration
  python run_e2e_tests.py --orchestrated
  
  # Run specific test suite
  python run_e2e_tests.py --suite integration --verbose
  
  # Run tests matching pattern
  python run_e2e_tests.py --pattern "*workflow*" --timeout 600
  
  # Install dependencies and run health checks
  python run_e2e_tests.py --install-deps --suite health
  
  # Run in CI mode with minimal output
  python run_e2e_tests.py --ci-mode --orchestrated
        """
    )
    
    parser.add_argument(
        '--orchestrated', '-o',
        action='store_true',
        help='Run orchestrated test execution (recommended)'
    )
    
    parser.add_argument(
        '--suite', '-s',
        choices=['health', 'integration', 'performance', 'data_flow', 'api_workflow', 'deployment', 'all'],
        default='all',
        help='Specific test suite to run'
    )
    
    parser.add_argument(
        '--pattern', '-p',
        help='Test pattern to match (pytest -k option)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=300,
        help='Test timeout in seconds (default: 300)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--install-deps',
        action='store_true',
        help='Install required dependencies before running tests'
    )
    
    parser.add_argument(
        '--ci-mode',
        action='store_true',
        help='CI mode with optimized output and error handling'
    )
    
    parser.add_argument(
        '--filter',
        nargs='*',
        help='Filter specific test suites for orchestrated execution'
    )
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = E2ETestRunner()
    
    # Setup environment
    setup_results = runner.setup_environment()
    
    if not setup_results['environment_ready']:
        print("❌ Environment setup failed:")
        for error in setup_results['errors']:
            print(f"  - {error}")
            
        if args.install_deps:
            print("\n📦 Attempting to install dependencies...")
            if runner.install_dependencies():
                setup_results = runner.setup_environment()
            else:
                print("❌ Failed to install dependencies")
                sys.exit(1)
        else:
            print("\n💡 Try running with --install-deps to install missing dependencies")
            sys.exit(1)
            
    if not args.ci_mode:
        print("✅ Environment setup completed")
        print("Prerequisites:")
        for prereq, status in setup_results['prerequisites'].items():
            print(f"  - {prereq}: {status}")
            
    # Execute tests
    all_results = []
    
    if args.orchestrated:
        # Run orchestrated tests
        orchestration_result = runner.run_orchestrated_tests(args.filter)
        all_results.append({
            'suite_name': 'orchestrated_execution',
            'status': orchestration_result['status'],
            'duration': orchestration_result.get('orchestration_results', {}).get('total_duration', 0)
        })
        
        if orchestration_result['status'] != 'completed':
            print(f"❌ Orchestrated execution failed: {orchestration_result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    else:
        # Run individual test suites
        if args.suite == 'all':
            suites = ['health', 'integration', 'data_flow', 'api_workflow', 'performance', 'deployment']
        else:
            suites = [args.suite]
            
        for suite in suites:
            result = runner.run_test_suite(
                suite, 
                args.pattern, 
                args.timeout, 
                args.verbose
            )
            all_results.append(result)
            
            if not args.ci_mode:
                status_emoji = {"passed": "✅", "failed": "❌", "error": "⚠️", "timeout": "⏰"}.get(result['status'], "❓")
                print(f"{status_emoji} {suite}: {result['status']} ({result['duration']:.1f}s)")
                
    # Generate and display summary
    summary = runner.generate_summary_report(all_results)
    
    if not args.ci_mode:
        runner.print_summary(summary)
    else:
        # CI mode - minimal output
        print(f"E2E Tests: {summary['passed_suites']}/{summary['total_suites']} passed ({summary['success_rate']:.1%})")
        
    # Exit with appropriate code
    if summary['success_rate'] < 1.0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()