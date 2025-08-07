# 🚀 Comprehensive CI/CD Pipeline Setup Guide

## Overview

This guide provides complete setup instructions for the comprehensive CI/CD pipeline created for the unified-ai-system-clean project. The pipeline includes automated testing, security scanning, Docker image building, performance testing, and automated deployment to RunPod.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pipeline Overview](#pipeline-overview)
3. [Setup Instructions](#setup-instructions)
4. [Workflow Configuration](#workflow-configuration)
5. [Environment Management](#environment-management)
6. [Security Configuration](#security-configuration)
7. [Deployment Configuration](#deployment-configuration)
8. [Monitoring and Notifications](#monitoring-and-notifications)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Prerequisites

### Required Tools and Services

- **GitHub Repository** with admin access
- **Docker Hub or GitHub Container Registry** account
- **RunPod** account (for deployment)
- **Slack/Discord** (optional, for notifications)

### Local Development Requirements

- Python 3.10+
- Docker and Docker Compose
- Make (GNU Make)
- Git

## Pipeline Overview

### 🔄 CI/CD Workflows

1. **Main CI Pipeline** (`main-ci.yml`)
   - Code quality checks (linting, formatting, type checking)
   - Unit and integration tests
   - Docker image building
   - Security vulnerability scanning
   - Test coverage reporting

2. **Deployment Pipeline** (`deploy-runpod.yml`)
   - Production-ready image building
   - Automated deployment to RunPod
   - Health checks and validation
   - Rollback capabilities

3. **Performance Testing** (`performance-tests.yml`)
   - Load testing and performance benchmarks
   - Regression detection
   - Performance reporting

4. **Security Scanning** (`security-scanning.yml`)
   - Dependency vulnerability scanning
   - Static code analysis
   - Container security scanning
   - Infrastructure security checks

5. **Notifications** (`notifications.yml`)
   - Slack, Discord, Teams, and email notifications
   - Status updates and alerts

## Setup Instructions

### 1. Repository Setup

```bash
# Clone the repository
git clone https://github.com/your-username/unified-ai-system-clean.git
cd unified-ai-system-clean

# Verify CI/CD files are present
ls -la .github/workflows/
```

### 2. Environment Configuration

```bash
# Copy environment templates
cp .env.template .env.development
cp .env.template .env.staging  
cp .env.template .env.production

# Edit each environment file with appropriate values
nano .env.development
nano .env.staging
nano .env.production
```

### 3. GitHub Secrets Configuration

Configure the following secrets in your GitHub repository (`Settings > Secrets and variables > Actions`):

#### Required Secrets

```bash
# Docker Registry
DOCKER_USERNAME=your_docker_username
DOCKER_PASSWORD=your_docker_password_or_token

# RunPod Deployment
RUNPOD_API_KEY=your_runpod_api_key
RUNPOD_ENDPOINT_ID=your_runpod_endpoint_id

# Environment-specific secrets
STAGING_SECRET_KEY=your_staging_secret_key
PRODUCTION_SECRET_KEY=your_production_secret_key

# API Keys
STAGING_BRAVE_API_KEY=your_staging_brave_api_key
PRODUCTION_BRAVE_API_KEY=your_production_brave_api_key
STAGING_SCRAPINGBEE_API_KEY=your_staging_scrapingbee_key
PRODUCTION_SCRAPINGBEE_API_KEY=your_production_scrapingbee_key
```

#### Optional Notification Secrets

```bash
# Slack Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url

# Discord Notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook/url

# Microsoft Teams
TEAMS_WEBHOOK_URL=your_teams_webhook_url

# Email Notifications
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=alerts@your-domain.com
```

### 4. Docker Registry Setup

#### GitHub Container Registry (Recommended)

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build and push images manually (optional)
make ci-build
make runpod-push
```

#### Docker Hub Setup

```bash
# Login to Docker Hub
docker login

# Update Makefile variables
export DOCKER_REGISTRY=docker.io
export GITHUB_REPOSITORY=your-username/unified-ai-system
```

## Workflow Configuration

### Trigger Configuration

The pipelines are triggered by:

- **Push** to main/master/develop branches
- **Pull Requests** to main/master
- **Manual dispatch** with parameters
- **Scheduled runs** (security scans daily at 3 AM UTC)
- **Tags** (for releases)

### Branch Protection Rules

Configure branch protection in GitHub:

```yaml
# .github/branch-protection.yml (example)
protection_rules:
  main:
    required_status_checks:
      - "Code Quality & Linting"
      - "Test AI Chat Service"
      - "Test Document Search Service"
      - "Build & Test Docker Images"
    enforce_admins: false
    required_pull_request_reviews:
      required_approving_review_count: 1
    dismiss_stale_reviews: true
```

## Environment Management

### Development Environment

```bash
# Start development environment
make dev

# Run development tests
make ci-test

# Check code quality
make check-all
```

### Staging Environment

```bash
# Deploy to staging
ENVIRONMENT=staging make ci-deploy

# Run staging tests
ENVIRONMENT=staging make performance-test
```

### Production Environment

```bash
# Deploy to production (via GitHub Actions)
git tag v1.0.0
git push origin v1.0.0

# Manual production deployment
ENVIRONMENT=production make ci-deploy
```

## Security Configuration

### Dependency Scanning

The pipeline automatically scans for:
- Known vulnerabilities in Python packages
- Outdated dependencies with security fixes
- License compliance issues

### Code Security Analysis

- **Bandit**: Python security linter
- **Semgrep**: Static analysis for security patterns
- **Secret detection**: Hardcoded credentials scanning

### Container Security

- **Trivy**: Container vulnerability scanning
- **Docker Scout**: Advanced container analysis
- **Dockerfile best practices**: Security configuration checks

### Infrastructure Security

- **Checkov**: Infrastructure as code scanning
- **Docker Compose security**: Configuration validation
- **Kubernetes security**: Manifest analysis (if applicable)

## Deployment Configuration

### RunPod Deployment

The deployment pipeline supports:

1. **Automated deployment** on main branch pushes
2. **Manual deployment** with environment selection
3. **Health checks** and validation
4. **Automatic rollback** on failure

#### RunPod Configuration

Create a RunPod template with:

```yaml
# runpod-template.yml
name: "Unified AI System"
image: "ghcr.io/your-repo/unified-ai-system:latest"
ports:
  - "8000:8000"  # Unified UI
  - "8001:8001"  # Document Search
  - "8003:8003"  # AI Chat
environment:
  - ENVIRONMENT=production
  - REDIS_URL=redis://redis:6379
  - OLLAMA_HOST=http://localhost:11434
resources:
  gpu: "RTX A4000"
  cpu: 4
  memory: "16GB"
  storage: "50GB"
```

### Multi-Environment Deployment

The pipeline supports deployment to:

- **Development**: Local Docker Compose
- **Staging**: RunPod staging environment
- **Production**: RunPod production environment

## Monitoring and Notifications

### Health Monitoring

Each service includes:
- **Liveness probes**: Basic health checks
- **Readiness probes**: Service readiness validation
- **Metrics endpoints**: Prometheus-compatible metrics

### Notification Channels

Configure notifications for:
- **Build failures**: Immediate alerts
- **Security vulnerabilities**: Daily summaries
- **Deployment status**: Success/failure notifications
- **Performance regressions**: Threshold-based alerts

### Monitoring Dashboards

Access monitoring through:
- GitHub Actions dashboard
- Container registry insights
- RunPod monitoring interface
- Custom metrics endpoints

## Troubleshooting

### Common Issues

#### 1. Test Failures

```bash
# Debug test failures locally
make pytest-all
make ci-test

# Check test logs
docker-compose logs ai-chat
```

#### 2. Docker Build Issues

```bash
# Build images locally
make build-optimized

# Check Docker layer caching
docker system df
docker buildx du
```

#### 3. Deployment Failures

```bash
# Check deployment logs
make logs

# Validate configuration
make ci-validate

# Manual health check
make health
```

#### 4. Security Scan Failures

```bash
# Run security scans locally
make security-scan

# Check specific scan results
make security-deps
make security-code
make security-docker
```

### Debug Commands

```bash
# Comprehensive system status
make status

# View metrics
make metrics

# Clean up CI artifacts
make clean-ci

# Test GitHub Actions compatibility
make github-actions-test
```

## Best Practices

### 1. Code Quality

- **Always run** `make check-all` before committing
- **Fix linting issues** before pushing
- **Maintain test coverage** above 60%
- **Use type hints** for better code quality

### 2. Security

- **Never commit secrets** to version control
- **Use environment variables** for configuration
- **Regularly update dependencies** for security patches
- **Review security scan results** weekly

### 3. Performance

- **Monitor performance metrics** regularly
- **Set performance budgets** in tests
- **Optimize Docker images** for size and speed
- **Use caching** effectively in CI/CD

### 4. Deployment

- **Test in staging** before production
- **Use feature flags** for gradual rollouts
- **Monitor deployment** health continuously
- **Have rollback procedures** ready

### 5. Monitoring

- **Set up alerting** for critical failures
- **Monitor resource usage** in production
- **Track key performance indicators**
- **Review logs** regularly

## Advanced Configuration

### Custom Workflow Variables

```yaml
# .github/workflows/main-ci.yml
env:
  PYTHON_VERSION: '3.10'
  NODE_VERSION: '18'
  REGISTRY: ghcr.io
  IMAGE_NAME: unified-ai-system
  # Custom variables
  MAX_TEST_DURATION: '300'
  SECURITY_SCAN_LEVEL: 'high'
  PERFORMANCE_THRESHOLD: '95'
```

### Matrix Builds

The pipeline uses matrix builds for:
- Multiple Python versions
- Different service components
- Various deployment targets

### Caching Strategy

Optimized caching for:
- Python pip dependencies
- Docker layer caching
- Test result caching
- Build artifact caching

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review security scan results
2. **Monthly**: Update dependencies
3. **Quarterly**: Review pipeline performance
4. **Annually**: Security audit and updates

### Getting Help

- Check the [troubleshooting section](#troubleshooting)
- Review GitHub Actions logs
- Check container logs with `make logs`
- Run diagnostic commands with `make status`

### Contributing

When contributing to the CI/CD pipeline:

1. Test changes in a fork first
2. Update documentation as needed
3. Ensure backward compatibility
4. Add appropriate tests

---

**Pipeline Status**: ✅ Ready for Production
**Last Updated**: 2025-01-01
**Version**: 1.0.0