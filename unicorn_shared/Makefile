# Makefile for Unicorn Shared Infrastructure

# Variables
STAGE ?= local
REGION ?= ap-southeast-2

.PHONY: help deploy-namespaces deploy-images-local deploy-images-dev deploy-images-prod deploy-images deploy delete-namespaces delete-images-local delete-images-dev delete-images-prod delete-images delete list-parameters

help: ## Show available commands
	@echo "Unicorn Shared Infrastructure"
	@echo ""
	@echo "Usage: make [target] [STAGE=local|dev|prod] [REGION=ap-southeast-2]"
	@echo ""
	@echo "Available targets:"
	@echo "  help                      Show available commands"
	@echo "  deploy-namespaces         Deploy global Unicorn Properties namespaces for all stages"
	@echo "  deploy-images-local       Deploy shared images stack for local environment"
	@echo "  deploy-images-dev         Deploy shared images stack for dev environment"
	@echo "  deploy-images-prod        Deploy shared images stack for prod environment"
	@echo "  deploy-images             Deploy shared images stack for all environments"
	@echo "  deploy                    Deploy all shared infrastructure"
	@echo "  list-parameters           List all parameters in the Unicorn Properties namespace"
	@echo "  delete-namespaces         Delete Unicorn Properties namespaces"
	@echo "  delete-images-local       Delete shared images stack for local environment"
	@echo "  delete-images-dev         Delete shared images stack for dev environment"
	@echo "  delete-images-prod        Delete shared images stack for prod environment"
	@echo "  delete-images             Delete all shared images stacks"
	@echo "  delete                    Delete all shared infrastructure"

deploy-namespaces: ## Deploy global Unicorn Properties namespaces for all stages
	@echo "Deploying global namespaces..."
	@aws cloudformation create-stack \
		--stack-name uni-prop-namespaces \
		--template-body file://uni-prop-namespaces.yaml \
		--capabilities CAPABILITY_AUTO_EXPAND \
		--region $(REGION) || \
	aws cloudformation update-stack \
		--stack-name uni-prop-namespaces \
		--template-body file://uni-prop-namespaces.yaml \
		--capabilities CAPABILITY_AUTO_EXPAND \
		--region $(REGION) || true

deploy-images-local: ## Deploy shared images stack for local environment
	@echo "Deploying shared images stack for local environment..."
	@if ! aws cloudformation describe-stacks --stack-name "uni-prop-local-images" --region $(REGION) >/dev/null 2>&1; then \
		echo "Creating shared images stack for local environment"; \
		aws cloudformation create-stack \
			--stack-name "uni-prop-local-images" \
			--template-body file://uni-prop-images.yaml \
			--parameters ParameterKey=Stage,ParameterValue=local \
			--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
			--region $(REGION) || echo "Stack creation failed for local!"; \
	else \
		echo "Stack uni-prop-local-images already exists, skipping..."; \
	fi

deploy-images-dev: ## Deploy shared images stack for dev environment
	@echo "Deploying shared images stack for dev environment..."
	@if ! aws cloudformation describe-stacks --stack-name "uni-prop-dev-images" --region $(REGION) >/dev/null 2>&1; then \
		echo "Creating shared images stack for dev environment"; \
		aws cloudformation create-stack \
			--stack-name "uni-prop-dev-images" \
			--template-body file://uni-prop-images.yaml \
			--parameters ParameterKey=Stage,ParameterValue=dev \
			--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
			--region $(REGION) || echo "Stack creation failed for dev!"; \
	else \
		echo "Stack uni-prop-dev-images already exists, skipping..."; \
	fi

deploy-images-prod: ## Deploy shared images stack for prod environment
	@echo "Deploying shared images stack for prod environment..."
	@if ! aws cloudformation describe-stacks --stack-name "uni-prop-prod-images" --region $(REGION) >/dev/null 2>&1; then \
		echo "Creating shared images stack for prod environment"; \
		aws cloudformation create-stack \
			--stack-name "uni-prop-prod-images" \
			--template-body file://uni-prop-images.yaml \
			--parameters ParameterKey=Stage,ParameterValue=prod \
			--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
			--region $(REGION) || echo "Stack creation failed for prod!"; \
	else \
		echo "Stack uni-prop-prod-images already exists, skipping..."; \
	fi

deploy-images: deploy-images-local deploy-images-dev deploy-images-prod ## Deploy shared images stack for all environments

deploy: deploy-namespaces deploy-images ## Deploy all shared infrastructure

list-parameters: ## List all parameters in the Unicorn Properties namespace
	@echo "Listing all Unicorn Properties parameters..."
	@aws ssm get-parameters-by-path \
		--path "/uni-prop" \
		--recursive \
		--with-decryption \
		--query 'Parameters[*].[Name,Value,Type]' \
		--output table \
		--region $(REGION)

delete-namespaces: ## Delete Unicorn Properties namespaces
	@echo "Deleting global namespaces..."
	@aws cloudformation delete-stack \
		--stack-name uni-prop-namespaces \
		--region $(REGION) || true

delete-images-local: ## Delete shared images stack for local environment
	@echo "Deleting shared images stack for local environment..."
	@if aws cloudformation describe-stacks --stack-name "uni-prop-local-images" --region $(REGION) >/dev/null 2>&1; then \
		aws cloudformation delete-stack \
			--stack-name "uni-prop-local-images" \
			--region $(REGION); \
	else \
		echo "Stack uni-prop-local-images does not exist, skipping..."; \
	fi

delete-images-dev: ## Delete shared images stack for dev environment
	@echo "Deleting shared images stack for dev environment..."
	@if aws cloudformation describe-stacks --stack-name "uni-prop-dev-images" --region $(REGION) >/dev/null 2>&1; then \
		aws cloudformation delete-stack \
			--stack-name "uni-prop-dev-images" \
			--region $(REGION); \
	else \
		echo "Stack uni-prop-dev-images does not exist, skipping..."; \
	fi

delete-images-prod: ## Delete shared images stack for prod environment
	@echo "Deleting shared images stack for prod environment..."
	@if aws cloudformation describe-stacks --stack-name "uni-prop-prod-images" --region $(REGION) >/dev/null 2>&1; then \
		aws cloudformation delete-stack \
			--stack-name "uni-prop-prod-images" \
			--region $(REGION); \
	else \
		echo "Stack uni-prop-prod-images does not exist, skipping..."; \
	fi

delete-images: delete-images-prod delete-images-dev delete-images-local ## Delete all shared images stacks

delete: delete-images delete-namespaces ## Delete all shared infrastructure