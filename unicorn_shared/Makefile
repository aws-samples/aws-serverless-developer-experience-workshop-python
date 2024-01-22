.ONESHELL:

ENVIRONMENTS = local dev prod

.PHONY: deploy-namespaces deploy-images delete-namespaces delete-images

deploy-namespaces:  ## Deploys global Unicorn Properties namespaces for all Stages
	aws cloudformation create-stack --stack-name uni-prop-namespaces --template-body file://uni-prop-namespaces.yaml --capabilities CAPABILITY_AUTO_EXPAND

deploy-images:  	## Deploys shared images stack for local dev prod stages
	@for env in $(ENVIRONMENTS); do \
		stage=$$env; \
		if ! aws cloudformation describe-stacks --stack-name "uni-prop-$$env-images" >/dev/null 2>&1; then \
			echo "Creating shared images stack for $$env environment"; \
			aws cloudformation create-stack \
				--stack-name "uni-prop-$$env-images" \
				--template-body file://uni-prop-images.yaml \
				--parameters ParameterKey=Stage,ParameterValue=$$stage \
				--capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND || echo "Stack creation failed!"; \
		fi; \
	done

delete-namespaces: ## Depletes Unicorn Properties namespaces
	aws cloudformation delete-stack --stack-name uni-prop-namespaces

delete-images: ## Deletes all shared images stacks
	@for env in $(ENVIRONMENTS); do \
			stage=$$env; \
			if aws cloudformation describe-stacks --stack-name "uni-prop-$$env-images" >/dev/null 2>&1; then \
				echo "Deleting shared images stack for $$env environment"; \
				aws cloudformation delete-stack \
					--stack-name "uni-prop-$$env-images"; \
			fi; \
		done
