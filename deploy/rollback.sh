#!/bin/bash
# Rollback to previous ECS task definition
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT="${ENVIRONMENT:-production}"
ECS_CLUSTER="${ENVIRONMENT}-astraeus-cluster"
ECS_SERVICE="${ENVIRONMENT}-astraeus-service"

echo -e "${YELLOW}Rolling back ${ECS_SERVICE}...${NC}"

# Get current task definition
CURRENT_TASK_DEF=$(aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --query 'services[0].taskDefinition' --output text)

# Get task family
TASK_FAMILY=$(aws ecs describe-task-definition --task-definition ${CURRENT_TASK_DEF} --query 'taskDefinition.family' --output text)

# List recent task definitions
echo "Recent task definitions:"
aws ecs list-task-definitions --family-prefix ${TASK_FAMILY} --sort DESC --max-items 5 --query 'taskDefinitionArns' --output table

# Get previous task definition (one before current)
PREVIOUS_TASK_DEF=$(aws ecs list-task-definitions --family-prefix ${TASK_FAMILY} --sort DESC --max-items 2 --query 'taskDefinitionArns[1]' --output text)

if [ -z "${PREVIOUS_TASK_DEF}" ] || [ "${PREVIOUS_TASK_DEF}" == "None" ]; then
    echo -e "${RED}ERROR: No previous task definition found${NC}"
    exit 1
fi

echo ""
echo "Current: ${CURRENT_TASK_DEF}"
echo "Rolling back to: ${PREVIOUS_TASK_DEF}"
echo ""

read -p "Continue with rollback? (yes/no) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 1
fi

# Update service
aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} --task-definition ${PREVIOUS_TASK_DEF} --force-new-deployment > /dev/null

echo -e "${GREEN}✓ Rollback initiated${NC}"
echo ""
echo "Waiting for service to stabilize..."
aws ecs wait services-stable --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE}

echo -e "${GREEN}✓ Rollback completed successfully${NC}"
