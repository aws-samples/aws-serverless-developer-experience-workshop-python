#### Global Variables
stackName		:= $(shell yq -oy '.default.global.parameters.stack_name' samconfig.yaml)


#### Test Variables
apiUrl			= $(call cf_output,$(stackName),ApiUrl)


#### Build/Deploy Tasks
deps:
	poetry install

build:
	swagger-cli validate api.yaml
	sam validate --lint
	cfn-lint template.yaml -a cfn_lint_serverless.rules
	poetry export -f requirements.txt --without-hashes --output src/approvals_service/requirements.txt
	poetry export -f requirements.txt --without-hashes --output src/search_service/requirements.txt
	sam build -c $(DOCKER_OPTS)

deploy: build
	sam deploy


#### Tests
test: unit-test integration-test

unit-test: deps
	poetry run pytest tests/unit/

integration-test: deps
	poetry run pytest tests/integration/

curl-test:
	$(call mcurl,GET,search/usa/anytown)
	$(call mcurl,GET,search/usa/anytown/main-street)
	$(call mcurl,GET,properties/usa/anytown/main-street/111)
	@echo "[DONE]"


#### Utilities
sync:
	sam sync --stack-name $(stackName) --watch

logs:
	sam logs --stack-name $(stackName) -t

clean:
	find . -type d -name __pycache__ -exec rm -rf {} \; 2>/dev/null || true
	find . -type f -name requirements.txt -exec rm -f {} \; 2>/dev/null || true
	rm -rf .pytest_cache/ .aws-sam/ htmlcov/ .coverage || true

delete:
	sam delete --no-prompts --region "$$(aws configure get region)"

# NOTE: [2023-05-09] This is a fix for installing Poetry dependencies in GitHub Actions
ci_init:
	poetry export --without-hashes --format=requirements.txt --output=src/requirements.txt --with dev
	poetry run pip install -r src/requirements.txt
	poetry install -n


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
