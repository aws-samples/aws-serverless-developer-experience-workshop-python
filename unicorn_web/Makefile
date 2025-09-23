# Makefile for Unicorn Web Service Infrastructure

# Variables
STAGE ?= local
REGION ?= ap-southeast-2
STACK_PREFIX = uni-prop-$(STAGE)

.PHONY: help build deploy deploy-domain deploy-schema deploy-subscriptions deploy-web-service test lint clean delete

help: ## Show available commands
	@echo "Unicorn Web Service Infrastructure"
	@echo ""
	@echo "Usage: make [target] [STAGE=local|dev|prod] [REGION=ap-southeast-2]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

build: ## Build the application
	@echo "Building .NET application..."
	@dotnet restore PublicationManagerService/PublicationManagerService.csproj
	@dotnet restore SearchService/SearchService.csproj
	@dotnet build PublicationManagerService/PublicationManagerService.csproj
	@dotnet build SearchService/SearchService.csproj
	@sam build --template-file iac/web-service.yaml

deploy-domain: ## Deploy domain resources (EventBridge, Schema Registry)
	@echo "Deploying domain resources..."
	@sam deploy \
		--template-file iac/domain.yaml \
		--stack-name $(STACK_PREFIX)-web-domain \
		--parameter-overrides Stage=$(STAGE) \
		--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
		--region $(REGION) \
		--resolve-s3 \
		--no-confirm-changeset \
		--no-fail-on-empty-changeset

deploy-schema: ## Deploy event schema
	@echo "Deploying event schema..."
	@sam deploy \
		--template-file iac/schema-registry/PublicationApprovalRequested-schema.yaml \
		--stack-name $(STACK_PREFIX)-web-schema-PublicationApprovalRequested \
		--parameter-overrides Stage=$(STAGE) \
		--capabilities CAPABILITY_IAM \
		--region $(REGION) \
		--resolve-s3 \
		--no-confirm-changeset \
		--no-fail-on-empty-changeset

deploy-subscriptions: ## Deploy event subscriptions
	@echo "Deploying event subscriptions..."
	@sam deploy \
		--template-file iac/subscriptions/unicorn-approvals-subscriptions.yaml \
		--stack-name $(STACK_PREFIX)-web-subscriptions-approvals \
		--parameter-overrides Stage=$(STAGE) \
		--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
		--region $(REGION) \
		--resolve-s3 \
		--no-confirm-changeset \
		--no-fail-on-empty-changeset

deploy-web-service: build ## Deploy web service
	@echo "Deploying web service..."
	@sam deploy \
		--template-file iac/web-service.yaml \
		--stack-name $(STACK_PREFIX)-web-service \
		--parameter-overrides Stage=$(STAGE) \
		--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
		--region $(REGION) \
		--resolve-s3 \
		--no-confirm-changeset \
		--no-fail-on-empty-changeset

deploy: deploy-domain deploy-schema deploy-subscriptions deploy-web-service ## Deploy all infrastructure and application

test: ## Run tests
	@echo "Running tests..."
	@dotnet test PublicationManagerService.Test/PublicationManagerService.Tests.csproj
	@dotnet test SearchService.Test/SearchService.Tests.csproj

lint: ## Lint CloudFormation templates
	@echo "Linting CloudFormation templates..."
	@cfn-lint iac/web-service.yaml -a cfn_lint_serverless.rules
	@cfn-lint iac/domain.yaml
	@cfn-lint iac/schema-registry/PublicationApprovalRequested-schema.yaml
	@cfn-lint iac/subscriptions/unicorn-approvals-subscriptions.yaml

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@rm -rf .aws-sam/
	@dotnet clean

delete: ## Delete all stacks
	@echo "Deleting stacks in reverse order..."
	@aws cloudformation delete-stack --stack-name $(STACK_PREFIX)-web-service --region $(REGION) || true
	@aws cloudformation delete-stack --stack-name $(STACK_PREFIX)-web-subscriptions-approvals --region $(REGION) || true
	@aws cloudformation delete-stack --stack-name $(STACK_PREFIX)-web-schema-PublicationApprovalRequested --region $(REGION) || true
	@echo "Waiting for service, subscriptions, and schema stacks to be deleted..."
	@aws cloudformation wait stack-delete-complete --stack-name $(STACK_PREFIX)-web-service --region $(REGION) || true
	@aws cloudformation wait stack-delete-complete --stack-name $(STACK_PREFIX)-web-subscriptions-approvals --region $(REGION) || true
	@aws cloudformation wait stack-delete-complete --stack-name $(STACK_PREFIX)-web-schema-PublicationApprovalRequested --region $(REGION) || true
	@aws cloudformation delete-stack --stack-name $(STACK_PREFIX)-web-domain --region $(REGION) || true