#!/bin/bash
# Deployment script for Astraeus Apertura
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${ENVIRONMENT:-production}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="astraeus-apertura"
ECS_CLUSTER="${ENVIRONMENT}-astraeus-cluster"
ECS_SERVICE="${ENVIRONMENT}-astraeus-service"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Astraeus Apertura Deployment${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Environment: ${ENVIRONMENT}"
echo "AWS Region: ${AWS_REGION}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo "AWS Account: ${AWS_ACCOUNT_ID}"
echo "ECR URI: ${ECR_URI}"
echo ""

# Login to ECR
echo -e "${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
echo -e "${GREEN}✓ Logged in to ECR${NC}"
echo ""

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
IMAGE_TAG="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
docker build -t ${ECR_REPOSITORY}:${IMAGE_TAG} -t ${ECR_REPOSITORY}:${ENVIRONMENT}-latest --target production .
echo -e "${GREEN}✓ Docker image built${NC}"
echo ""

# Tag and push to ECR
echo -e "${YELLOW}Pushing image to ECR...${NC}"
docker tag ${ECR_REPOSITORY}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}
docker tag ${ECR_REPOSITORY}:${ENVIRONMENT}-latest ${ECR_URI}:${ENVIRONMENT}-latest

docker push ${ECR_URI}:${IMAGE_TAG}
docker push ${ECR_URI}:${ENVIRONMENT}-latest
echo -e "${GREEN}✓ Image pushed to ECR${NC}"
echo ""

# Update ECS service
echo -e "${YELLOW}Updating ECS service...${NC}"

# Get current task definition
TASK_DEFINITION=$(aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --query 'services[0].taskDefinition' --output text)

if [ "${TASK_DEFINITION}" == "None" ] || [ -z "${TASK_DEFINITION}" ]; then
    echo -e "${YELLOW}No existing service found. Please deploy infrastructure first using CloudFormation or Terraform.${NC}"
    exit 1
fi

# Register new task definition with updated image
TASK_FAMILY=$(aws ecs describe-task-definition --task-definition ${TASK_DEFINITION} --query 'taskDefinition.family' --output text)

NEW_TASK_DEF=$(aws ecs describe-task-definition --task-definition ${TASK_DEFINITION} --query 'taskDefinition' | \
  jq --arg IMAGE "${ECR_URI}:${IMAGE_TAG}" \
  '.containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)')

NEW_TASK_ARN=$(echo $NEW_TASK_DEF | aws ecs register-task-definition --cli-input-json file:///dev/stdin --query 'taskDefinition.taskDefinitionArn' --output text)

echo "New task definition: ${NEW_TASK_ARN}"

# Update service
aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} --task-definition ${NEW_TASK_ARN} --force-new-deployment > /dev/null

echo -e "${GREEN}✓ ECS service updated${NC}"
echo ""

# Wait for deployment
echo -e "${YELLOW}Waiting for deployment to complete...${NC}"
aws ecs wait services-stable --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE}

echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo ""

# Get service URL
ALB_DNS=$(aws elbv2 describe-load-balancers --query "LoadBalancers[?contains(LoadBalancerName, 'astraeus')].DNSName" --output text)

if [ ! -z "${ALB_DNS}" ]; then
    echo -e "${GREEN}Application URL: http://${ALB_DNS}${NC}"
fi

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}================================${NC}"
