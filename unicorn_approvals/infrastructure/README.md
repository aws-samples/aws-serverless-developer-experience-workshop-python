# SAM Templates Documentation

This directory contains AWS SAM (Serverless Application Model) templates for the Unicorn Approvals Service, part of the AWS Serverless Developer Experience workshop. The templates are organized to separate domain-level resources from service-specific resources and event subscriptions.

## Template Overview

### 1. `approvals-service.yaml` - Main Service Template

**Purpose**: Contains the core Unicorn Approvals Service infrastructure including Lambda functions, Step Functions workflow, DynamoDB table, and messaging components.

**Key Resources**:

- **Lambda Functions**:

  - `ContractStatusChangedHandlerFunction`: Processes contract status change events from the Contracts service
  - `PropertiesApprovalSyncFunction`: DynamoDB stream processor that resumes paused Step Functions executions
  - `WaitForContractApprovalFunction`: Implements the "wait for approval" pattern for Step Functions

- **Step Functions State Machine** (`ApprovalStateMachine`): Orchestrates the property approval workflow including:

  - Content validation
  - Image analysis using Amazon Rekognition
  - Text analysis using Amazon Comprehend
  - Contract approval coordination

- **DynamoDB Table** (`ContractStatusTable`): Central state store for contract approval status and Step Functions task tokens with DynamoDB Streams enabled

- **SQS Dead Letter Queues**:

  - `ApprovalsEventBusRuleDLQ`: Captures EventBridge rule delivery failures
  - `ApprovalsServiceDLQ`: Captures Lambda function invocation failures

- **EventBridge Components**:
  - `UnicornApprovalsCatchAllRule`: Development rule for capturing all events for debugging
  - `UnicornApprovalsCatchAllLogGroup`: CloudWatch log group for event debugging

**Notable Features**:

- Event-driven architecture with EventBridge integration
- Step Functions workflow orchestration with pause/resume capabilities
- DynamoDB Streams for real-time state synchronization
- Comprehensive error handling with multiple DLQ strategies
- AWS AI services integration (Rekognition, Comprehend)
- Environment-specific configuration and logging levels

**Dependencies**: Requires domain resources to be deployed first for EventBridge bus and SSM parameters.

### 2. `domain.yaml` - Domain Resources Template

**Purpose**: Creates shared domain-level infrastructure that can be used by multiple services within the Unicorn Approvals domain.

**Key Resources**:

- **EventBridge Event Bus** (`UnicornApprovalsEventBus`): Central event bus for approval-related events
- **SSM Parameters**: Store event bus name, ARN, and schema registry information for cross-service access
- **Event Bus Logging**: Complete logging setup with delivery sources, destinations, and delivery configurations
- **Schema Registry** (`UnicornApprovalsSchemaRegistry`): Event schema management for approval events
- **Event Bus Policies**: Access control for creating rules and publishing events
- **EventBridge Role** (`UnicornApprovalsEventBridgeRole`): IAM role for cross-service event routing

**Notable Features**:

- Configurable logging levels based on stage (INFO for dev/local, ERROR for prod)
- Proper deletion policies for all logging resources to ensure clean stack deletion
- Cross-service event bus policy restricting rule creation to specific sources
- Exported EventBridge role for use in subscription templates
- Comprehensive event bus logging with delivery sources an

**Note**: This template provides the foundation for event-driven integrations for all Unicorn Approval services. It needs to be deployed before any other services.

### 3. `schema-registry/PublicationEvaluationCompleted-schema.yaml` - Event Schema Template

**Purpose**: Defines the event schema for `PublicationEvaluationCompleted` events in the EventBridge Schema Registry.

**Key Resources**:

- **PublicationEvaluationCompleted** (`AWS::EventSchemas::Schema`): OpenAPI 3.0 schema definition for publication evaluation completion events

**Schema Structure**:

- **Event Source**: Retrieved from SSM parameter (unicorn-approvals namespace)
- **Detail Type**: `PublicationEvaluationCompleted`
- **Required Fields**:
  - `PropertyId`: Unique identifier for the property
  - `EvaluationResult`: Result of the publication evaluation

**Integration**:

- Uses SSM parameter resolution to get the schema registry name from domain template
- Follows AWS EventBridge event envelope structure
- Enables code generation for strongly-typed event handling

### 4. `subscriptions/` - Event Subscription Templates

**Purpose**: Manages cross-service event subscriptions by creating EventBridge rules that route events between different service event buses.

#### 4.1 `unicorn-contracts-subscriptions.yaml`

**Key Resources**:

- **ContractStatusChangedSubscriptionRule**: EventBridge rule that subscribes to ContractStatusChanged events from the Unicorn Contracts service and forwards them to the Unicorn Approvals event bus for processing approval workflows

**Event Flow**:

- Listens to: Unicorn Contracts Event Bus
- Event Type: `ContractStatusChanged`
- Routes to: Unicorn Approvals Event Bus

#### 4.2 `unicorn-web-subscriptions.yaml`

**Key Resources**:

- **PublicationApprovalRequestedSubscriptionRule**: Routes `PublicationApprovalRequested` events from the Unicorn Web service to the Approvals service and triggers the Approval workflow

**Event Flow**:

- Listens to: Unicorn Web Event Bus
- Event Type: `PublicationApprovalRequested`
- Routes to: Unicorn Approvals Event Bus

## Template Parameters

All templates accept a `Stage` parameter with allowed values:

- `local`: Development environment (3-day log retention)
- `dev`: Development environment (3-day log retention)
- `prod`: Production environment (14-day log retention, reduced logging)

## Deployment Order

1. **Deploy Domain Resources First**:

   ```bash
   sam deploy \
   --template-file ./infrastructure/domain.yaml \
   --stack-name uni-prop-local-approvals-domain \
   --parameter-overrides Stage=local \
   --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
   --region ap-southeast-2 \
   --resolve-s3
   ```

2. **Deploy Main Service Template**:

   ```bash
   sam deploy \
   --template-file ./infrastructure/approvals-service.yaml \
   --stack-name uni-prop-local-approvals-service \
   --parameter-overrides Stage=local \
   --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
   --region ap-southeast-2 \
   --resolve-s3
   ```

3. **Deploy Event Schema** (For schema governance):

   ```bash
   sam deploy \
      --template-file ./infrastructure/schema-registry/PublicationEvaluationCompleted-schema.yaml \
      --stack-name uni-prop-local-approvals-publication-evaluation-completed-schema \
      --parameter-overrides Stage=local \
      --capabilities CAPABILITY_IAM \
      --region ap-southeast-2 \
      --resolve-s3
   ```

4. **Deploy Event Subscriptions**:

   ```bash
   # Deploy Contracts subscriptions
   sam deploy \
      --template-file ./infrastructure/subscriptions/unicorn-contracts-subscriptions.yaml \
      --stack-name uni-prop-local-approvals-contracts-subscriptions \
      --parameter-overrides Stage=local \
      --capabilities CAPABILITY_IAM \
      --region ap-southeast-2 \
      --resolve-s3

   # Deploy Web subscriptions
   sam deploy \
      --template-file ./infrastructure/subscriptions/unicorn-web-subscriptions.yaml \
      --stack-name uni-prop-local-approvals-web-subscriptions \
      --parameter-overrides Stage=local \
      --capabilities CAPABILITY_IAM \
      --region ap-southeast-2 \
      --resolve-s3
   ```

## Key Configuration Details

### Environment Variables (Global)

- `SERVICE_NAMESPACE`: Retrieved from SSM parameter
- Event bus ARNs and names shared via SSM parameters

### Security

- IAM roles follow least privilege principle
- Event bus policies restrict cross-service access
- EventBridge roles exported for subscription template reuse
- Schema registry policies control access to event schemas

### Monitoring & Logging

- CloudWatch log retention varies by stage
- EventBridge logging captures both INFO and ERROR events
- Comprehensive event bus logging with delivery sources and destinations

## Dependencies

### External Dependencies

- SSM Parameters:
  - `/uni-prop/UnicornApprovalsNamespace`
  - `/uni-prop/UnicornContractsNamespace` (for subscriptions)
  - `/uni-prop/UnicornWebNamespace` (for subscriptions)

### Cross-Template Dependencies

- Subscription templates depend on SSM parameters created by `domain.yaml`
- `PublicationEvaluationCompleted-schema.yaml` depends on schema registry created by `domain.yaml`
- Event bus ARNs and schema registry names are shared via SSM parameters between templates
- Subscription templates import EventBridge role from domain stack

## Best Practices Implemented

1. **Infrastructure as Code**: All resources defined declaratively
2. **Environment Separation**: Stage-based configuration
3. **Security**: Least privilege IAM, proper event bus policies
4. **Observability**: Comprehensive logging and event tracking
5. **Event-Driven Architecture**: Proper separation of concerns with dedicated subscription templates
6. **Schema Governance**: Centralized schema management with validation
7. **Clean Deletion**: Proper deletion policies for stateful resources
8. **Service Ownership**: Clear ownership model where consuming services own their subscription rules

## Event-Driven Architecture

The Approvals service follows an event-driven architecture pattern:

- **Domain Events**: Publishes `PublicationEvaluationCompleted` events
- **Event Subscriptions**: Consumes events from Contracts and Web services
- **Cross-Service Communication**: Uses EventBridge for loose coupling
- **Schema Governance**: Enforces event structure through schema registry

## Troubleshooting

### Common Issues

1. **SSM Parameter Dependencies**: Ensure domain template is deployed first
2. **Cross-Service Dependencies**: Verify other services' event buses exist before deploying subscriptions
3. **EventBridge Role**: Ensure domain stack is deployed before subscription stacks
4. **Schema Registry**: Verify schema registry exists before deploying schemas

### Monitoring

- Check CloudWatch logs for EventBridge rule execution
- Monitor event bus metrics for event processing
- Review schema registry for event validation errors
- Use EventBridge event replay for debugging failed events

## Configuration Files

- `samconfig.toml`: Contains default deployment configuration
- `README.md`: Deployment instructions and commands

## Architecture Notes

The Approvals service acts as both an event producer and consumer:

- **Produces**: `PublicationEvaluationCompleted` events for downstream services
- **Consumes**: `ContractStatusChanged` events from Contracts service
- **Consumes**: `PublicationApprovalRequested` events from Web service

This design enables loose coupling between services while maintaining clear event ownership and subscription management.
