stackName := uni-prop-local-properties

build:
	cfn-lint template.yaml -a cfn_lint_serverless.rules
	poetry export --without-hashes --format=requirements.txt --output=src/requirements.txt
	sam build -c

deps:
	poetry install

deploy: build
	sam deploy --no-confirm-changeset

sync:
	sam sync --stack-name $(stackName) --watch

test: unit-test

unit-test: deps
	poetry run pytest tests/unit/

logs:
	sam logs --stack-name $(stackName) -t

clean:
	find . -type d -name __pycache__ -exec rm -rf {} \; 2>/dev/null || true
	find . -type f -name requirements.txt -exec rm -f {} \; 2>/dev/null || true
	rm -rf .pytest_cache/ .aws-sam/ htmlcov/ .coverage || true

delete:
	sam delete --stack-name $(stackName) --no-prompts
