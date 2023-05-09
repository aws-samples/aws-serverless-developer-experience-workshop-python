deps:
	poetry install

build:
	# cfn-lint template.yaml -a cfn_lint_serverless.rules
	poetry export -f requirements.txt --without-hashes --output src/approvals_service/requirements.txt
	poetry export -f requirements.txt --without-hashes --output src/search_service/requirements.txt
	sam build -c

deploy: build
	sam deploy --no-confirm-changeset

test: unit-test

unit-test: deps
	poetry run pytest tests/unit/

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
