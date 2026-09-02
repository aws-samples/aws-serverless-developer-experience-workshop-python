# Technology Stack & Build System

## Runtime & Language

- **Python >= 3.13** (pinned in each service's `pyproject.toml`) - all Lambda functions
- **uv** - package and environment manager; each service has its own `pyproject.toml` and `uv.lock`
- **AWS SAM** - infrastructure as code, build, and deployment

## AWS Services

- **AWS Lambda** - serverless compute
- **Amazon DynamoDB** - NoSQL persistence with streams
- **Amazon EventBridge** - event bus, schema registry, and cross-service messaging
- **AWS Step Functions** - approval workflow orchestration
- **Amazon API Gateway** - REST API endpoints
- **Amazon SQS** - ingest queues and dead-letter queues
- **AWS X-Ray** - distributed tracing
- **Amazon CloudWatch** - logging, metrics, and monitoring

## Key Libraries & Frameworks

- **AWS Lambda Powertools for Python** (`aws-lambda-powertools[tracer]`) - structured logging, metrics, and tracing
- **boto3** and **aws-xray-sdk** - AWS service clients and tracing
- **pytest** with `pytest-cov` (80% coverage gate) and **moto** for AWS mocking
- **ruff** - linting and formatting (per-service `ruff.toml`)

## Build & Development Commands

### Make Targets (canonical interface)

Run from a service directory (e.g., `unicorn_contracts/`). Stages: `local` (default), `dev`, `prod`; default region `ap-southeast-2`.

```bash
make build STAGE=local      # uv sync, export requirements.txt, sam build
make deploy STAGE=local     # deploy-domain + deploy-schema + deploy-service
make deploy-domain          # Event bus, schema registry (infrastructure/domain.yaml)
make deploy-schema          # Event schema stack(s)
make deploy-service         # Lambda, API Gateway, DynamoDB (service template)
make test                   # Run all tests (pytest)
make unit-test              # Unit tests only
make format                 # ruff format + ruff check --fix
make lint                   # ruff check/format + cfn-lint on templates
make clean                  # Remove .aws-sam/, caches
make delete                 # Delete stacks in reverse dependency order
```

`unicorn_shared/` has its own targets: `deploy-namespaces`, `deploy-images` (per-stage variants), `deploy`, `list-parameters`, and reverse-order `delete` targets. Deploy shared namespaces before any service.

### Runtime Commands

Inside a service directory, the make targets invoke uv commands you can also run directly:

```bash
uv sync --dev               # Install dependencies (incl. dev extras)
uv run pytest               # All tests (config in pyproject.toml)
uv run pytest tests/unit -v # Unit tests only
uv run ruff check .         # Lint
uv run ruff format .        # Format
```

`make build` exports the locked dependencies to `src/requirements.txt` for SAM packaging — do not edit that file by hand.

### SAM Commands

```bash
sam build --cached --parallel                  # Build (config in samconfig.toml)
sam deploy --no-confirm-changeset              # Deploy current service
sam validate --lint                            # Validate templates
sam sync --watch                               # Rapid dev iteration
sam local start-api --warm-containers EAGER    # Local API
sam local start-lambda --warm-containers EAGER # Local Lambda endpoint
```

`samconfig.toml` in each `infrastructure/<service>-service/` directory sets stack name, cached/parallel builds, `disable_rollback` for dev iteration, and `Stage` parameter overrides.

## Environment Variables

Standard Lambda environment variables set in the SAM templates:

- `DYNAMODB_TABLE` - DynamoDB table name
- `SERVICE_NAMESPACE` - service identifier for event sources (from SSM namespace parameters)
- `POWERTOOLS_SERVICE_NAME`, `POWERTOOLS_METRICS_NAMESPACE` - Powertools identifiers
- `POWERTOOLS_LOG_LEVEL`, `POWERTOOLS_LOGGER_LOG_EVENT`, `POWERTOOLS_LOGGER_SAMPLE_RATE`, `POWERTOOLS_TRACE_DISABLED` - observability tuning (stage-mapped)
- `LOG_LEVEL` - application log level
