#### Global Variables
stackName		:= $(shell yq -oy '.default.global.parameters.stack_name' samconfig.yaml)


#### Test Variables
apiUrl			= $(call cf_output,$(stackName),ApiUrl)
ddbPropertyId 	= $(call get_ddb_key,create_contract_valid_payload_1)


#### Build/Deploy Tasks
ci: clean build deploy

build:
	sam validate --lint
	cfn-lint template.yaml -a cfn_lint_serverless.rules
	poetry export --without-hashes --format=requirements.txt --output=src/requirements.txt
	sam build -c $(DOCKER_OPTS)

deps:
	poetry install

deploy: deps build
	sam deploy

#### Tests
test: unit-test integration-test

unit-test:
	poetry run pytest tests/unit/

integration-test: deps
	poetry run pytest tests/integration/

curl-test: clean-tests
	$(call runif,CREATE CONTRACT)
	$(call mcurl,POST,create_contract_valid_payload_1)

	$(call runif,Query DDB)
	$(call ddb_get,$(ddbPropertyId))

	$(call runif,UPDATE CONTRACT)
	$(call mcurl,PUT,update_existing_contract_valid_payload_1)

	$(call runif,Query DDB)
	$(call ddb_get,$(ddbPropertyId))

	$(call runif,Delete DDB Items)
	$(MAKE) clean-tests

	@echo "[DONE]"


clean-tests:
	$(call ddb_delete,$(ddbPropertyId)) || true


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
	poetry export --without-hashes --format=requirements.txt --output=src/requirements.txt --with dev
	poetry run pip install -r src/requirements.txt
	poetry install -n


#### Helper Functions
define runif
	@echo
	@echo "Run $(1) now?"
	@read
	@echo "Running $(1)"
endef

define ddb_get
	@aws dynamodb get-item \
		--table-name $(call cf_output,$(stackName),ContractsTableName) \
		--key 		'$(1)' \
	| jq -f tests/integration/transformations/ddb_contract.jq
endef

define ddb_delete
	aws dynamodb delete-item \
		--table-name $(call cf_output,$(stackName),ContractsTableName) \
		--key 		'$(1)'
endef

define mcurl
	curl -X $(1) -H "Content-type: application/json" -d @$(call payload,$(2)) $(apiUrl)contract
endef

define get_ddb_key
$(shell jq '. | {property_id:{S:.property_id}}' $(call payload,$(1)) | tr -d ' ')
endef

define payload
tests/integration/events/$(1).json
endef

define cf_output
	$(shell aws cloudformation describe-stacks \
		--output text \
		--stack-name $(1) \
		--query 'Stacks[0].Outputs[?OutputKey==`$(2)`].OutputValue')
endef
