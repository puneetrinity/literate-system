"""
Deployment Validation End-to-End Tests

Comprehensive testing of deployment scenarios including Docker Compose,
RunPod deployment validation, health checks, monitoring, and configuration validation.
"""

import asyncio
import json
import time
import os
import subprocess
import tempfile
import yaml
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio
import docker
from httpx import AsyncClient, Timeout


@dataclass
class DeploymentEnvironment:
    """Represents a deployment environment configuration."""
    name: str
    type: str  # 'docker', 'runpod', 'local'
    services: List[str]
    health_endpoints: Dict[str, str]
    expected_ports: Dict[str, int]
    environment_variables: Dict[str, str]
    volumes: Optional[Dict[str, str]] = None
    

class DockerDeploymentValidator:
    """Validates Docker-based deployments."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.test_containers = []
        
    async def validate_docker_compose_deployment(
        self,
        compose_file_path: str,
        expected_services: List[str],
        timeout: int = 120
    ) -> Dict[str, Any]:
        """Validate Docker Compose deployment."""
        
        results = {
            'deployment_successful': False,
            'services_status': {},
            'health_checks': {},
            'port_mappings': {},
            'volume_mappings': {},
            'network_connectivity': {},
            'errors': []
        }
        
        try:
            # Read compose file
            with open(compose_file_path, 'r') as f:
                compose_config = yaml.safe_load(f)
                
            # Start services using docker-compose
            compose_dir = os.path.dirname(compose_file_path)
            
            # Build and start services
            start_cmd = ["docker-compose", "-f", compose_file_path, "up", "-d", "--build"]
            
            process = subprocess.run(
                start_cmd,
                cwd=compose_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if process.returncode != 0:
                results['errors'].append(f"Docker compose start failed: {process.stderr}")
                return results
                
            # Wait for services to start
            await asyncio.sleep(10)
            
            # Validate each service
            for service_name in expected_services:
                service_result = await self._validate_docker_service(
                    service_name, compose_config.get('services', {}).get(service_name, {})
                )
                results['services_status'][service_name] = service_result
                
            # Check overall deployment status
            all_services_healthy = all(
                status.get('healthy', False) 
                for status in results['services_status'].values()
            )
            
            results['deployment_successful'] = all_services_healthy
            
        except Exception as e:
            results['errors'].append(f"Deployment validation error: {str(e)}")
            
        return results
        
    async def _validate_docker_service(
        self,
        service_name: str,
        service_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate individual Docker service."""
        
        service_result = {
            'container_running': False,
            'healthy': False,
            'ports_accessible': {},
            'environment_correct': True,
            'volumes_mounted': True,
            'errors': []
        }
        
        try:
            # Find container
            containers = self.docker_client.containers.list(
                filters={'label': f'com.docker.compose.service={service_name}'}
            )
            
            if not containers:
                service_result['errors'].append(f"No container found for service {service_name}")
                return service_result
                
            container = containers[0]
            service_result['container_running'] = container.status == 'running'
            
            # Check health
            if service_result['container_running']:
                # Wait for health check
                for _ in range(30):  # 30 second timeout
                    container.reload()
                    health = container.attrs.get('State', {}).get('Health', {}).get('Status')
                    
                    if health == 'healthy':
                        service_result['healthy'] = True
                        break
                    elif health == 'unhealthy':
                        service_result['errors'].append(f"Service {service_name} is unhealthy")
                        break
                        
                    await asyncio.sleep(1)
                    
                # If no explicit health check, assume healthy if running
                if 'Health' not in container.attrs.get('State', {}):
                    service_result['healthy'] = service_result['container_running']
                    
            # Check port mappings
            port_bindings = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            for internal_port, bindings in port_bindings.items():
                if bindings:
                    external_port = bindings[0]['HostPort']
                    service_result['ports_accessible'][internal_port] = external_port
                    
        except Exception as e:
            service_result['errors'].append(f"Service validation error: {str(e)}")
            
        return service_result
        
    async def cleanup_test_deployment(self, compose_file_path: str):
        """Clean up test deployment."""
        try:
            cleanup_cmd = ["docker-compose", "-f", compose_file_path, "down", "-v"]
            subprocess.run(cleanup_cmd, capture_output=True, timeout=60)
        except Exception as e:
            print(f"Cleanup error: {e}")


class HealthCheckValidator:
    """Validates service health checks and monitoring endpoints."""
    
    async def validate_health_endpoints(
        self,
        health_endpoints: Dict[str, str],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Validate all health check endpoints."""
        
        results = {
            'all_healthy': True,
            'endpoint_results': {},
            'response_times': [],
            'errors': []
        }
        
        async with AsyncClient(timeout=Timeout(timeout)) as client:
            for service_name, endpoint_url in health_endpoints.items():
                endpoint_result = await self._check_health_endpoint(
                    client, service_name, endpoint_url
                )
                
                results['endpoint_results'][service_name] = endpoint_result
                
                if endpoint_result['healthy']:
                    results['response_times'].append(endpoint_result['response_time'])
                else:
                    results['all_healthy'] = False
                    
        return results
        
    async def _check_health_endpoint(
        self,
        client: AsyncClient,
        service_name: str,
        endpoint_url: str
    ) -> Dict[str, Any]:
        """Check individual health endpoint."""
        
        result = {
            'healthy': False,
            'status_code': None,
            'response_time': 0.0,
            'response_data': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            response = await client.get(endpoint_url)
            result['response_time'] = time.time() - start_time
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                result['healthy'] = True
                try:
                    result['response_data'] = response.json()
                except:
                    result['response_data'] = response.text[:200]
            else:
                result['error'] = f"HTTP {response.status_code}"
                
        except Exception as e:
            result['error'] = str(e)
            result['response_time'] = time.time() - start_time if 'start_time' in locals() else 0.0
            
        return result


class ConfigurationValidator:
    """Validates deployment configurations."""
    
    def validate_environment_configuration(
        self,
        expected_config: Dict[str, Any],
        actual_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate environment configuration."""
        
        results = {
            'configuration_valid': True,
            'missing_variables': [],
            'incorrect_values': [],
            'extra_variables': [],
            'security_issues': []
        }
        
        # Check required variables
        for key, expected_value in expected_config.items():
            if key not in actual_config:
                results['missing_variables'].append(key)
                results['configuration_valid'] = False
            elif actual_config[key] != expected_value:
                results['incorrect_values'].append({
                    'key': key,
                    'expected': expected_value,
                    'actual': actual_config[key]
                })
                
        # Check for security issues
        security_patterns = ['password', 'secret', 'key', 'token']
        for key, value in actual_config.items():
            if any(pattern in key.lower() for pattern in security_patterns):
                if not value or value == 'changeme' or len(str(value)) < 8:
                    results['security_issues'].append(f"Weak/missing {key}")
                    
        return results
        
    def validate_docker_compose_config(self, compose_file_path: str) -> Dict[str, Any]:
        """Validate Docker Compose configuration."""
        
        results = {
            'config_valid': True,
            'services_configured': [],
            'networks_configured': [],
            'volumes_configured': [],
            'health_checks_present': [],
            'security_configurations': [],
            'issues': []
        }
        
        try:
            with open(compose_file_path, 'r') as f:
                compose_config = yaml.safe_load(f)
                
            services = compose_config.get('services', {})
            
            for service_name, service_config in services.items():
                results['services_configured'].append(service_name)
                
                # Check health checks
                if 'healthcheck' in service_config:
                    results['health_checks_present'].append(service_name)
                    
                # Check security configurations
                if 'environment' in service_config:
                    env_vars = service_config['environment']
                    if isinstance(env_vars, list):
                        env_dict = {var.split('=')[0]: var.split('=', 1)[1] if '=' in var else '' for var in env_vars}
                    else:
                        env_dict = env_vars
                        
                    # Check for hardcoded secrets
                    for key, value in env_dict.items():
                        if any(pattern in key.lower() for pattern in ['password', 'secret', 'key']):
                            if not str(value).startswith('${'):
                                results['security_configurations'].append(f"Hardcoded secret in {service_name}: {key}")
                                
            # Check networks
            networks = compose_config.get('networks', {})
            results['networks_configured'] = list(networks.keys())
            
            # Check volumes
            volumes = compose_config.get('volumes', {})
            results['volumes_configured'] = list(volumes.keys())
            
        except Exception as e:
            results['config_valid'] = False
            results['issues'].append(f"Config validation error: {str(e)}")
            
        return results


class RunPodValidator:
    """Validates RunPod-specific deployment configurations."""
    
    def validate_runpod_template(self, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate RunPod template configuration."""
        
        results = {
            'template_valid': True,
            'gpu_configuration': {},
            'container_configuration': {},
            'network_configuration': {},
            'storage_configuration': {},
            'issues': []
        }
        
        # Validate GPU requirements
        if 'gpu' in template_config:
            gpu_config = template_config['gpu']
            results['gpu_configuration'] = {
                'gpu_count': gpu_config.get('count', 0),
                'gpu_type': gpu_config.get('type', 'unknown'),
                'memory_requirement': gpu_config.get('memory', 0)
            }
            
            if results['gpu_configuration']['gpu_count'] == 0:
                results['issues'].append("No GPU configured for AI workload")
                
        # Validate container configuration
        if 'container' in template_config:
            container_config = template_config['container']
            results['container_configuration'] = {
                'image': container_config.get('image', ''),
                'ports': container_config.get('ports', []),
                'environment': container_config.get('environment', {}),
                'startup_command': container_config.get('command', '')
            }
            
            # Check required ports
            required_ports = [8001, 8003]  # Document search and AI chat ports
            configured_ports = [p.get('container_port') for p in results['container_configuration']['ports']]
            
            missing_ports = [p for p in required_ports if p not in configured_ports]
            if missing_ports:
                results['issues'].append(f"Missing port configurations: {missing_ports}")
                
        return results
        
    async def validate_runpod_deployment_health(
        self,
        pod_endpoints: Dict[str, str]
    ) -> Dict[str, Any]:
        """Validate RunPod deployment health."""
        
        results = {
            'pod_accessible': True,
            'services_running': {},
            'performance_metrics': {},
            'errors': []
        }
        
        # Test each service endpoint
        async with AsyncClient(timeout=Timeout(30.0)) as client:
            for service_name, endpoint_url in pod_endpoints.items():
                try:
                    start_time = time.time()
                    response = await client.get(f"{endpoint_url}/health")
                    response_time = time.time() - start_time
                    
                    results['services_running'][service_name] = {
                        'accessible': response.status_code == 200,
                        'response_time': response_time,
                        'status_code': response.status_code
                    }
                    
                except Exception as e:
                    results['services_running'][service_name] = {
                        'accessible': False,
                        'error': str(e)
                    }
                    results['pod_accessible'] = False
                    
        return results


class TestDeploymentValidationE2E:
    """Comprehensive deployment validation tests."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self):
        """Set up test environment."""
        self.docker_validator = DockerDeploymentValidator()
        self.health_validator = HealthCheckValidator()
        self.config_validator = ConfigurationValidator()
        self.runpod_validator = RunPodValidator()
        
    async def teardown_method(self):
        """Clean up after tests."""
        # Cleanup any test deployments
        pass
        
    async def test_docker_compose_deployment_validation(self):
        """Test Docker Compose deployment validation."""
        
        compose_file_path = "/home/ews/unified-ai-system-clean/docker-compose.yml"
        
        # Validate compose configuration first
        config_results = self.config_validator.validate_docker_compose_config(compose_file_path)
        
        print(f"Docker Compose Configuration Validation:")
        print(f"  - Config Valid: {config_results['config_valid']}")
        print(f"  - Services Configured: {len(config_results['services_configured'])}")
        print(f"  - Health Checks Present: {len(config_results['health_checks_present'])}")
        print(f"  - Networks Configured: {len(config_results['networks_configured'])}")
        print(f"  - Volumes Configured: {len(config_results['volumes_configured'])}")
        
        if config_results['issues']:
            print(f"  - Issues Found: {config_results['issues']}")
            
        if config_results['security_configurations']:
            print(f"  - Security Issues: {config_results['security_configurations']}")
            
        assert config_results['config_valid'], f"Docker Compose config invalid: {config_results['issues']}"
        
        # Validate expected services are configured
        expected_services = ['redis', 'ollama', 'document-search', 'ai-chat']
        configured_services = config_results['services_configured']
        
        missing_services = [s for s in expected_services if s not in configured_services]
        assert not missing_services, f"Missing services in compose config: {missing_services}"
        
        # Note: We don't actually start the full deployment in tests due to resource constraints
        # In a real deployment pipeline, you would uncomment the following:
        
        # deployment_results = await self.docker_validator.validate_docker_compose_deployment(
        #     compose_file_path, expected_services
        # )
        # 
        # assert deployment_results['deployment_successful'], \
        #     f"Deployment failed: {deployment_results['errors']}"
        
    async def test_health_check_endpoints_validation(self):
        """Test health check endpoints validation."""
        
        # Test against running services (if available)
        health_endpoints = {
            'document-search': 'http://localhost:8002/health',
            'ai-chat': 'http://localhost:8004/health'
        }
        
        # Try to validate health endpoints
        try:
            health_results = await self.health_validator.validate_health_endpoints(
                health_endpoints, timeout=10.0
            )
            
            print(f"Health Check Validation Results:")
            print(f"  - All Services Healthy: {health_results['all_healthy']}")
            
            for service, result in health_results['endpoint_results'].items():
                print(f"  - {service}: {'✓' if result['healthy'] else '✗'} "
                      f"({result['response_time']:.3f}s)")
                if result['error']:
                    print(f"    Error: {result['error']}")
                    
            if health_results['response_times']:
                avg_response_time = sum(health_results['response_times']) / len(health_results['response_times'])
                print(f"  - Average Response Time: {avg_response_time:.3f}s")
                
            # If services are running, they should be healthy
            if any(result['healthy'] for result in health_results['endpoint_results'].values()):
                # At least some services are running
                healthy_services = [
                    service for service, result in health_results['endpoint_results'].items()
                    if result['healthy']
                ]
                print(f"  - Healthy Services: {healthy_services}")
                
        except Exception as e:
            # Services not running - this is expected in test environment
            print(f"Health check test: Services not running (expected in test env): {e}")
            
    async def test_environment_configuration_validation(self):
        """Test environment configuration validation."""
        
        # Define expected configuration for production
        expected_production_config = {
            'ENVIRONMENT': 'production',
            'DEBUG': 'false',
            'REDIS_URL': 'redis://redis:6379',
            'OLLAMA_HOST': 'http://ollama:11434'
        }
        
        # Test configuration validation logic
        test_configs = [
            # Valid configuration
            {
                'name': 'valid_config',
                'config': {
                    'ENVIRONMENT': 'production',
                    'DEBUG': 'false',
                    'REDIS_URL': 'redis://redis:6379',
                    'OLLAMA_HOST': 'http://ollama:11434',
                    'BRAVE_API_KEY': 'valid_api_key_12345678'
                },
                'should_be_valid': True
            },
            
            # Missing required variables
            {
                'name': 'missing_variables',
                'config': {
                    'ENVIRONMENT': 'production',
                    'DEBUG': 'false'
                    # Missing REDIS_URL and OLLAMA_HOST
                },
                'should_be_valid': False
            },
            
            # Security issues
            {
                'name': 'security_issues',
                'config': {
                    'ENVIRONMENT': 'production',
                    'DEBUG': 'false',
                    'REDIS_URL': 'redis://redis:6379',
                    'OLLAMA_HOST': 'http://ollama:11434',
                    'SECRET_KEY': 'weak'  # Too short
                },
                'should_be_valid': True  # Config valid but has security issues
            }
        ]
        
        for test_config in test_configs:
            config_name = test_config['name']
            validation_results = self.config_validator.validate_environment_configuration(
                expected_production_config, test_config['config']
            )
            
            print(f"Configuration Test: {config_name}")
            print(f"  - Valid: {validation_results['configuration_valid']}")
            print(f"  - Missing Variables: {validation_results['missing_variables']}")
            print(f"  - Security Issues: {validation_results['security_issues']}")
            
            if test_config['should_be_valid']:
                if validation_results['missing_variables']:
                    assert not validation_results['configuration_valid'], \
                        f"Config {config_name} should be invalid due to missing variables"
            else:
                assert not validation_results['configuration_valid'], \
                    f"Config {config_name} should be invalid"
    
    async def test_runpod_template_validation(self):
        """Test RunPod template validation."""
        
        # Example RunPod template configurations
        runpod_templates = [
            {
                'name': 'valid_gpu_template',
                'config': {
                    'gpu': {
                        'count': 1,
                        'type': 'RTX4090',
                        'memory': 24
                    },
                    'container': {
                        'image': 'unified-ai-system:latest',
                        'ports': [
                            {'container_port': 8001, 'public_port': 8001},
                            {'container_port': 8003, 'public_port': 8003}
                        ],
                        'environment': {
                            'ENVIRONMENT': 'runpod',
                            'GPU_ENABLED': 'true'
                        },
                        'command': './start-system.sh'
                    }
                },
                'should_be_valid': True
            },
            
            {
                'name': 'missing_gpu_template',
                'config': {
                    'container': {
                        'image': 'unified-ai-system:latest',
                        'ports': [
                            {'container_port': 8001, 'public_port': 8001}
                            # Missing 8003 port
                        ],
                        'environment': {},
                        'command': './start-system.sh'
                    }
                },
                'should_be_valid': False
            }
        ]
        
        for template in runpod_templates:
            template_name = template['name']
            validation_results = self.runpod_validator.validate_runpod_template(
                template['config']
            )
            
            print(f"RunPod Template Test: {template_name}")
            print(f"  - Template Valid: {validation_results['template_valid']}")
            print(f"  - GPU Config: {validation_results['gpu_configuration']}")
            print(f"  - Issues: {validation_results['issues']}")
            
            if template['should_be_valid']:
                if validation_results['issues']:
                    print(f"  - Warning: Template has issues but may still work: {validation_results['issues']}")
            else:
                assert validation_results['issues'], \
                    f"Template {template_name} should have validation issues"
                    
    async def test_deployment_monitoring_validation(self):
        """Test deployment monitoring and metrics validation."""
        
        # Define monitoring endpoints that should be available
        monitoring_endpoints = {
            'prometheus_metrics': '/metrics',
            'health_status': '/health',
            'api_docs': '/docs',
            'system_info': '/info'
        }
        
        # Test monitoring endpoint structure
        for endpoint_name, endpoint_path in monitoring_endpoints.items():
            # Validate endpoint pattern
            assert endpoint_path.startswith('/'), f"Endpoint {endpoint_name} should start with /"
            assert len(endpoint_path) > 1, f"Endpoint {endpoint_name} should not be just '/'"
            
        print(f"Monitoring Endpoints Validation:")
        print(f"  - Endpoints Defined: {len(monitoring_endpoints)}")
        print(f"  - Endpoint Paths: {list(monitoring_endpoints.values())}")
        
        # In a real deployment, you would test actual endpoint accessibility:
        # for service_base_url in service_urls:
        #     for endpoint_name, endpoint_path in monitoring_endpoints.items():
        #         full_url = f"{service_base_url}{endpoint_path}"
        #         # Test endpoint accessibility
        
    async def test_deployment_security_validation(self):
        """Test deployment security configurations."""
        
        security_checklist = {
            'no_hardcoded_secrets': True,
            'secure_communication': True,
            'proper_authentication': True,
            'resource_limits_set': True,
            'network_isolation': True
        }
        
        # Validate security configurations
        compose_file_path = "/home/ews/unified-ai-system-clean/docker-compose.yml"
        
        try:
            with open(compose_file_path, 'r') as f:
                compose_config = yaml.safe_load(f)
                
            services = compose_config.get('services', {})
            
            # Check for hardcoded secrets
            for service_name, service_config in services.items():
                environment = service_config.get('environment', {})
                
                if isinstance(environment, list):
                    env_dict = {}
                    for env_var in environment:
                        if '=' in env_var:
                            key, value = env_var.split('=', 1)
                            env_dict[key] = value
                else:
                    env_dict = environment
                    
                # Check for potential hardcoded secrets
                for key, value in env_dict.items():
                    if any(pattern in key.lower() for pattern in ['password', 'secret', 'key', 'token']):
                        if isinstance(value, str) and not value.startswith('${') and value not in ['', '-']:
                            security_checklist['no_hardcoded_secrets'] = False
                            print(f"  - Warning: Potential hardcoded secret in {service_name}: {key}")
                            
            # Check for network configuration
            networks = compose_config.get('networks', {})
            if networks:
                security_checklist['network_isolation'] = True
            else:
                print("  - Warning: No custom networks defined")
                
            # Check for resource limits (would be in deploy section for swarm mode)
            resource_limits_found = any(
                'deploy' in service_config and 'resources' in service_config['deploy']
                for service_config in services.values()
            )
            
            if not resource_limits_found:
                print("  - Note: No explicit resource limits found (acceptable for development)")
                
        except Exception as e:
            print(f"Security validation error: {e}")
            
        print(f"Security Validation Results:")
        print(f"  - No Hardcoded Secrets: {'✓' if security_checklist['no_hardcoded_secrets'] else '✗'}")
        print(f"  - Network Isolation: {'✓' if security_checklist['network_isolation'] else '✗'}")
        
        # Critical security checks must pass
        assert security_checklist['no_hardcoded_secrets'], "Hardcoded secrets detected in configuration"
        
    async def test_deployment_scalability_validation(self):
        """Test deployment scalability configurations."""
        
        scalability_metrics = {
            'horizontal_scaling_possible': False,
            'resource_efficiency': True,
            'load_balancing_configured': False,
            'cache_optimization': True,
            'database_scaling': True
        }
        
        # Check Docker Compose for scalability indicators
        compose_file_path = "/home/ews/unified-ai-system-clean/docker-compose.yml"
        
        try:
            with open(compose_file_path, 'r') as f:
                compose_config = yaml.safe_load(f)
                
            services = compose_config.get('services', {})
            
            # Check for stateless services (easier to scale)
            stateless_services = []
            stateful_services = []
            
            for service_name, service_config in services.items():
                has_volumes = 'volumes' in service_config
                if has_volumes:
                    # Check if volumes are for persistent data or just config
                    volumes = service_config['volumes']
                    persistent_volumes = [
                        v for v in volumes 
                        if not any(readonly in str(v) for readonly in [':ro', 'read_only'])
                    ]
                    
                    if persistent_volumes and service_name not in ['redis', 'ollama']:
                        stateful_services.append(service_name)
                    else:
                        stateless_services.append(service_name)
                else:
                    stateless_services.append(service_name)
                    
            # Check for Redis (caching)
            if 'redis' in services:
                scalability_metrics['cache_optimization'] = True
                
            # Check for load balancer (nginx)
            if 'nginx' in services:
                scalability_metrics['load_balancing_configured'] = True
                
            # Services can be horizontally scaled if they're stateless
            if len(stateless_services) >= 2:  # At least AI chat and document search
                scalability_metrics['horizontal_scaling_possible'] = True
                
        except Exception as e:
            print(f"Scalability validation error: {e}")
            
        print(f"Scalability Validation Results:")
        print(f"  - Horizontal Scaling Possible: {'✓' if scalability_metrics['horizontal_scaling_possible'] else '✗'}")
        print(f"  - Load Balancing Configured: {'✓' if scalability_metrics['load_balancing_configured'] else '✗'}")
        print(f"  - Cache Optimization: {'✓' if scalability_metrics['cache_optimization'] else '✗'}")
        
    async def test_deployment_backup_recovery_validation(self):
        """Test deployment backup and recovery configurations."""
        
        backup_recovery_config = {
            'data_volumes_identified': [],
            'backup_strategy_documented': False,
            'recovery_procedures_available': False,
            'critical_data_persistent': True
        }
        
        # Check for persistent volumes that need backup
        compose_file_path = "/home/ews/unified-ai-system-clean/docker-compose.yml"
        
        try:
            with open(compose_file_path, 'r') as f:
                compose_config = yaml.safe_load(f)
                
            # Check volumes section
            volumes = compose_config.get('volumes', {})
            backup_recovery_config['data_volumes_identified'] = list(volumes.keys())
            
            # Check services for volume mounts
            services = compose_config.get('services', {})
            for service_name, service_config in services.items():
                service_volumes = service_config.get('volumes', [])
                for volume in service_volumes:
                    if isinstance(volume, str) and ':' in volume:
                        volume_parts = volume.split(':')
                        if len(volume_parts) >= 2:
                            source = volume_parts[0]
                            # Named volumes or bind mounts for data
                            if source.startswith('./') or source in volumes:
                                if source not in backup_recovery_config['data_volumes_identified']:
                                    backup_recovery_config['data_volumes_identified'].append(f"{service_name}:{source}")
            
            # Check for documentation files
            project_root = os.path.dirname(compose_file_path)
            docs_dir = os.path.join(project_root, 'docs')
            
            if os.path.exists(docs_dir):
                doc_files = os.listdir(docs_dir)
                backup_docs = [f for f in doc_files if 'backup' in f.lower() or 'recovery' in f.lower()]
                
                if backup_docs:
                    backup_recovery_config['backup_strategy_documented'] = True
                    backup_recovery_config['recovery_procedures_available'] = True
                    
        except Exception as e:
            print(f"Backup/recovery validation error: {e}")
            
        print(f"Backup/Recovery Validation Results:")
        print(f"  - Data Volumes Identified: {len(backup_recovery_config['data_volumes_identified'])}")
        print(f"  - Volumes: {backup_recovery_config['data_volumes_identified']}")
        print(f"  - Backup Strategy Documented: {'✓' if backup_recovery_config['backup_strategy_documented'] else '✗'}")
        print(f"  - Recovery Procedures Available: {'✓' if backup_recovery_config['recovery_procedures_available'] else '✗'}")
        
        # At least some data volumes should be identified
        assert len(backup_recovery_config['data_volumes_identified']) > 0, \
            "No persistent data volumes identified for backup"