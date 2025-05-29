#### Global Variables
stackName		:= $(shell yq -r '.default.global.parameters.stack_name' samconfig.toml)


#### Test Variables
apiUrl			= $(call cf_output,$(stackName),ApiUrl)



#### Build/Deploy Tasks
build:
	ruff format
	sam validate --lint
	cfn-lint template.yaml -a cfn_lint_serverless.rules
	uv export --no-hashes --format=requirements-txt --output-file=src/requirements.txt
	sam build -c $(DOCKER_OPTS)

deps:
	uv sync

deploy: deps build
	sam deploy


#### Tests
test: unit-test

unit-test:
	uv run pytest tests/unit/

curl-test:
	$(call mcurl,GET,search/usa/anytown)
	$(call mcurl,GET,search/usa/anytown/main-street)
	$(call mcurl,GET,properties/usa/anytown/main-street/111)
	@echo "[DONE]"


#### Utilities
sync:
	sam sync --stack-name $(stackName) --watch

logs:
	sam logs -t

clean:
	find . -type d -name __pycache__ -exec rm -rf {} \; 2>/dev/null || true
	find . -type f -name requirements.txt -exec rm -f {} \; 2>/dev/null || true
	rm -rf .pytest_cache/ .aws-sam/ || true

delete:
	sam delete --stack-name $(stackName) --no-prompts

# NOTE: [2023-05-09] This is a fix for installing Poetry dependencies in GitHub Actions
ci_init:
	uv venv
	uv export --no-hashes --format=requirements.txt --output-file=src/requirements.txt --extra=dev
	uv pip install -r src/requirements.txt


#### Helper Functions
define mcurl
	curl -s -X $(1) -H "Content-type: application/json" $(apiUrl)$(2) | jq
endef

define cf_output
	$(shell aws cloudformation describe-stacks \
		--output text \
		--stack-name $(1) \
		--query 'Stacks[0].Outputs[?OutputKey==`$(2)`].OutputValue')
endef
