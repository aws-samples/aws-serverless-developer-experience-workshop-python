# Makefile for Unicorn Contracts Service Infrastructure

# Variables
STAGE ?= local
REGION ?= ap-southeast-2
STACK_PREFIX = uni-prop-$(STAGE)

.PHONY: help build deploy deploy-domain deploy-schema deploy-service test lint format clean delete

help: ## Show available commands
	@echo "Unicorn Contracts Service Infrastructure"
	@echo ""
	@echo "Usage: make [target] [STAGE=local|dev|prod] [REGION=ap-southeast-2]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

build: ## Build the application
	@echo "Building Python application..."
	@uv sync --dev
	@sam build --template-file iac/contracts-service.yaml

deploy-domain: ## Deploy domain resources (EventBridge, Schema Registry)
	@echo "Deploying domain resources..."
	@sam deploy \
		--template-file iac/domain.yaml \
		--stack-name $(STACK_PREFIX)-contracts-domain \
		--parameter-overrides Stage=$(STAGE) \
		--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
		--region $(REGION) \
		--resolve-s3 \
		--no-confirm-changeset \
		--no-fail-on-empty-changeset

deploy-schema: ## Deploy event schema
	@echo "Deploying event schema..."
	@sam deploy \
		--template-file iac/schema-registry/ContractStatusChanged-schema.yaml \
		--stack-name $(STACK_PREFIX)-contracts-schema-ContractStatusChanged \
		--parameter-overrides Stage=$(STAGE) \
		--capabilities CAPABILITY_IAM \
		--region $(REGION) \
		--resolve-s3 \
		--no-confirm-changeset \
		--no-fail-on-empty-changeset

deploy-service: build ## Deploy service resources (Lambda, API Gateway, DynamoDB)
	@echo "Deploying service resources..."
	@sam deploy \
		--template-file iac/contracts-service.yaml \
		--stack-name $(STACK_PREFIX)-contracts-contracts-service \
		--parameter-overrides Stage=$(STAGE) \
		--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
		--region $(REGION) \
		--resolve-s3 \
		--no-confirm-changeset \
		--no-fail-on-empty-changeset

deploy: deploy-domain deploy-schema deploy-service ## Deploy all infrastructure and application

test: ## Run tests
	@echo "Running tests..."
	@uv run pytest

lint: ## Lint Python code and CloudFormation templates
	@echo "Linting Python code..."
	@uv run ruff check .
	@uv run ruff format --check .
	@echo "Linting CloudFormation templates..."
	@cfn-lint iac/contracts-service.yaml -a cfn_lint_serverless.rules
	@cfn-lint iac/domain.yaml
	@cfn-lint iac/schema-registry/ContractStatusChanged-schema.yaml

format: ## Format Python code
	@echo "Formatting Python code..."
	@uv run ruff format .
	@uv run ruff check --fix .

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@rm -rf .aws-sam/
	@rm -rf .pytest_cache/
	@rm -rf .ruff_cache/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

delete: ## Delete all stacks
	@echo "Deleting stacks in reverse order..."
	@aws cloudformation delete-stack --stack-name $(STACK_PREFIX)-contracts-contracts-service --region $(REGION) || true
	@aws cloudformation delete-stack --stack-name $(STACK_PREFIX)-contracts-schema-ContractStatusChanged --region $(REGION) || true
	@echo "Waiting for service and schema stacks to be deleted..."
	@aws cloudformation wait stack-delete-complete --stack-name $(STACK_PREFIX)-contracts-contracts-service --region $(REGION) || true
	@aws cloudformation wait stack-delete-complete --stack-name $(STACK_PREFIX)-contracts-schema-ContractStatusChanged --region $(REGION) || true
	@aws cloudformation delete-stack --stack-name $(STACK_PREFIX)-contracts-domain --region $(REGION) || true