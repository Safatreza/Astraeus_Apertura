#!/bin/bash
# Setup AWS infrastructure using CloudFormation
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT="${ENVIRONMENT:-production}"
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${ENVIRONMENT}-astraeus-infrastructure"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Infrastructure Setup${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Create ECR repository
echo -e "${YELLOW}Creating ECR repository...${NC}"
aws ecr create-repository --repository-name astraeus-apertura --region ${AWS_REGION} 2>/dev/null || echo "Repository already exists"

# Create secrets in Secrets Manager
echo -e "${YELLOW}Setting up secrets...${NC}"

if [ ! -z "${ANTHROPIC_API_KEY}" ]; then
    aws secretsmanager create-secret --name astraeus/anthropic-api-key --secret-string "${ANTHROPIC_API_KEY}" --region ${AWS_REGION} 2>/dev/null || \
    aws secretsmanager update-secret --secret-id astraeus/anthropic-api-key --secret-string "${ANTHROPIC_API_KEY}" --region ${AWS_REGION}
    echo "✓ Anthropic API key configured"
fi

if [ ! -z "${OPENAI_API_KEY}" ]; then
    aws secretsmanager create-secret --name astraeus/openai-api-key --secret-string "${OPENAI_API_KEY}" --region ${AWS_REGION} 2>/dev/null || \
    aws secretsmanager update-secret --secret-id astraeus/openai-api-key --secret-string "${OPENAI_API_KEY}" --region ${AWS_REGION}
    echo "✓ OpenAI API key configured"
fi

if [ ! -z "${NOTION_API_KEY}" ]; then
    aws secretsmanager create-secret --name astraeus/notion-api-key --secret-string "${NOTION_API_KEY}" --region ${AWS_REGION} 2>/dev/null || \
    aws secretsmanager update-secret --secret-id astraeus/notion-api-key --secret-string "${NOTION_API_KEY}" --region ${AWS_REGION}
    echo "✓ Notion API key configured"
fi

echo ""

# Get AWS account ID for image URI
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CONTAINER_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/astraeus-apertura:${ENVIRONMENT}-latest"

# Deploy CloudFormation stack
echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"
echo "Stack Name: ${STACK_NAME}"
echo ""

aws cloudformation deploy \
  --template-file deploy/aws/cloudformation-ecs.yaml \
  --stack-name ${STACK_NAME} \
  --parameter-overrides \
    EnvironmentName=${ENVIRONMENT} \
    ContainerImage=${CONTAINER_IMAGE} \
  --capabilities CAPABILITY_IAM \
  --region ${AWS_REGION}

echo ""
echo -e "${GREEN}✓ Infrastructure setup complete${NC}"
echo ""

# Get stack outputs
echo -e "${YELLOW}Stack Outputs:${NC}"
aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs' --output table

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Next Steps:${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "1. Build and push your Docker image:"
echo "   ./deploy/deploy.sh"
echo ""
echo "2. Access your application at the Load Balancer URL shown above"
echo ""
