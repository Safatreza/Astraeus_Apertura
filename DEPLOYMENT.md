# Astraeus Apertura - AWS Deployment Guide

Complete guide for deploying Astraeus Apertura to AWS using Docker, ECS Fargate, and automated CI/CD.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Internet/Users                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Application Load    │
              │     Balancer (ALB)   │
              └──────────┬───────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
   ┌────────────────┐        ┌────────────────┐
   │  ECS Service   │        │  ECS Service   │
   │  (Dashboard)   │        │   (Worker)     │
   │  Fargate Task  │        │  Fargate Task  │
   └────────┬───────┘        └────────┬───────┘
            │                         │
            └────────────┬────────────┘
                         │
                    ┌────▼─────┐
                    │    S3    │
                    │  Storage │
                    └──────────┘
```

## 📋 Prerequisites

### Required Tools
- Docker (>= 20.10)
- AWS CLI (>= 2.0)
- Git
- Bash shell

### AWS Requirements
- AWS Account with appropriate permissions
- IAM role for ECS task execution
- ECR repository access
- Secrets Manager access

### API Keys (Optional but Recommended)
- Anthropic Claude API key
- OpenAI GPT API key
- Notion API key

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/Safatreza/Astraeus_Apertura.git
cd Astraeus_Apertura
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your values
vi .env
```

Required environment variables:
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=your-account-id

# API Keys
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key
NOTION_API_KEY=your-notion-key

# Environment
ENVIRONMENT=production
```

### 3. Setup Infrastructure

```bash
# Login to AWS
aws configure

# Setup infrastructure (VPC, ECS, ALB, etc.)
export ENVIRONMENT=production
./deploy/setup-infrastructure.sh
```

This will:
- Create VPC with public/private subnets
- Setup Application Load Balancer
- Create ECS Fargate cluster
- Configure security groups
- Create ECR repository
- Setup Secrets Manager

### 4. Deploy Application

```bash
# Build and deploy
./deploy/deploy.sh
```

This will:
- Build Docker image
- Push to ECR
- Update ECS service
- Wait for deployment to complete

### 5. Access Application

```bash
# Get load balancer URL
aws cloudformation describe-stacks \
  --stack-name production-astraeus-infrastructure \
  --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
  --output text
```

Open the URL in your browser!

## 🔧 Deployment Options

### Option 1: CloudFormation

Use AWS CloudFormation for infrastructure as code:

```bash
aws cloudformation deploy \
  --template-file deploy/aws/cloudformation-ecs.yaml \
  --stack-name production-astraeus \
  --parameter-overrides \
    EnvironmentName=production \
    ContainerImage=your-ecr-uri:latest \
  --capabilities CAPABILITY_IAM
```

### Option 2: Terraform

Use Terraform for infrastructure:

```bash
cd deploy/aws
terraform init
terraform plan -var="environment=production"
terraform apply
```

### Option 3: Docker Compose (Local/Development)

Run locally with Docker Compose:

```bash
# Development mode
docker-compose up -d

# Access dashboard
open http://localhost:8050

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📦 Docker Images

### Building Images

```bash
# Development image (includes all dependencies)
docker build -t astraeus:dev --target development .

# Production image (minimal dependencies)
docker build -t astraeus:prod --target production .

# Dashboard image
docker build -t astraeus:dashboard --target dashboard .

# Worker image
docker build -t astraeus:worker --target worker .
```

### Pushing to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag astraeus:prod \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/astraeus-apertura:latest

docker push \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/astraeus-apertura:latest
```

## 🔄 CI/CD Pipeline

### GitHub Actions

Automated deployment on push:

```yaml
# .github/workflows/deploy.yml is configured for:
- main branch → production
- staging branch → staging
- pull requests → test only
```

Required GitHub Secrets:
- `AWS_ROLE_TO_ASSUME`: IAM role ARN for OIDC
- `AWS_REGION`: AWS region

### Manual Deployment

```bash
# Deploy specific environment
export ENVIRONMENT=staging
./deploy/deploy.sh

# Deploy with specific image tag
export IMAGE_TAG=v1.2.3
./deploy/deploy.sh
```

## 🔙 Rollback

If something goes wrong:

```bash
# Quick rollback to previous version
./deploy/rollback.sh

# Or manually
aws ecs update-service \
  --cluster production-astraeus-cluster \
  --service production-astraeus-service \
  --task-definition previous-task-def-arn \
  --force-new-deployment
```

## 📊 Monitoring

### Health Checks

```bash
# Health endpoint
curl http://your-alb-url/_health

# Readiness endpoint
curl http://your-alb-url/_ready

# Metrics endpoint
curl http://your-alb-url/_metrics
```

### CloudWatch Logs

```bash
# View logs
aws logs tail /ecs/production-astraeus --follow

# Search logs
aws logs filter-log-events \
  --log-group-name /ecs/production-astraeus \
  --filter-pattern "ERROR"
```

### CloudWatch Metrics

Key metrics to monitor:
- `ECSServiceAverageCPUUtilization`
- `ECSServiceAverageMemoryUtilization`
- `TargetResponseTime`
- `HealthyHostCount`
- `UnHealthyHostCount`

### Alarms

Set up CloudWatch Alarms:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name astraeus-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

## 🔐 Security Best Practices

### 1. API Keys Management

Store sensitive data in AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
  --name astraeus/anthropic-api-key \
  --secret-string "your-api-key"

# Update secret
aws secretsmanager update-secret \
  --secret-id astraeus/anthropic-api-key \
  --secret-string "new-api-key"
```

### 2. IAM Roles

Use least privilege principle:
- ECS Task Execution Role: Only ECR and CloudWatch access
- ECS Task Role: Only S3 and specific AWS services needed

### 3. Network Security

- Private subnets for ECS tasks
- ALB in public subnets
- Security groups restrict traffic
- VPC endpoints for AWS services

### 4. Container Security

- Non-root user in containers
- Read-only root filesystem where possible
- Regular security scans
- Minimal base images

## 🔧 Configuration

### Environment Variables

Available environment variables:

```bash
# Required
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...

# Optional
NOTION_API_KEY=secret_...
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
LOG_LEVEL=INFO
WORKER_THREADS=8
DASHBOARD_PORT=8050
```

### Resource Limits

Adjust CPU/memory in `cloudformation-ecs.yaml`:

```yaml
Parameters:
  ContainerCpu:
    Default: 2048  # 2 vCPUs
  ContainerMemory:
    Default: 4096  # 4 GB
```

### Auto Scaling

Configure auto scaling:

```yaml
ServiceScalingPolicy:
  TargetValue: 70.0  # Target CPU utilization
  MinCapacity: 2
  MaxCapacity: 10
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check service events
aws ecs describe-services \
  --cluster production-astraeus-cluster \
  --services production-astraeus-service \
  --query 'services[0].events[0:5]'

# Check task logs
aws logs tail /ecs/production-astraeus --follow
```

### High Memory Usage

```bash
# Check task memory
aws ecs describe-tasks \
  --cluster production-astraeus-cluster \
  --tasks task-id \
  --query 'tasks[0].containers[0].memory'

# Increase memory limit
# Edit cloudformation-ecs.yaml and redeploy
```

### Connection Timeouts

```bash
# Check security groups
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:...
```

## 📝 Maintenance

### Updating Dependencies

```bash
# Update requirements.txt
pip list --outdated
pip install -U package-name

# Rebuild and deploy
./deploy/deploy.sh
```

### Database Migrations

```bash
# Run migrations
docker-compose run --rm dashboard python manage.py migrate

# Or in ECS
aws ecs run-task \
  --cluster production-astraeus-cluster \
  --task-definition migration-task \
  --launch-type FARGATE
```

### Backup and Recovery

```bash
# Backup S3 data
aws s3 sync s3://astraeus-production-data ./backup/

# Backup RDS (if using)
aws rds create-db-snapshot \
  --db-snapshot-identifier astraeus-snapshot-$(date +%Y%m%d)
```

## 💰 Cost Optimization

### Use Fargate Spot

Save up to 70% with Spot capacity:

```yaml
DefaultCapacityProviderStrategy:
  - CapacityProvider: FARGATE
    Weight: 1
  - CapacityProvider: FARGATE_SPOT
    Weight: 4
```

### Auto Scaling

Scale down during off-peak hours:

```python
# Use scheduled scaling
aws application-autoscaling put-scheduled-action \
  --scheduled-action-name scale-down-night \
  --resource-id service/cluster/service \
  --schedule "cron(0 22 * * ? *)" \
  --scalable-target-action MinCapacity=1,MaxCapacity=2
```

### Reserved Capacity

For predictable workloads, use Savings Plans.

## 🆘 Support

- **Documentation**: See README.md
- **Issues**: GitHub Issues
- **Security**: security@example.com

## 📚 Additional Resources

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [Terraform AWS Modules](https://registry.terraform.io/namespaces/terraform-aws-modules)
- [GitHub Actions AWS](https://github.com/aws-actions)

---

**Last Updated**: 2025-01-17
**Version**: 1.0.0
