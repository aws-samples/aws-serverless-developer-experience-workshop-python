# SAM Templates Documentation

This directory contains AWS SAM (Serverless Application Model) templates for the Unicorn Web Service, part of the AWS Serverless Developer Experience workshop. The templates are organized to separate domain-level resources from service-specific resources and event subscriptions.

## Template Overview

### 1. `web-service.yaml` - Main Service Template

**Purpose**: Contains the core Unicorn Web Service infrastructure including API Gateway, Lambda functions, DynamoDB table, SQS queues, and EventBridge integration for property management and publication workflows.

**Key Resources**:

- **Lambda Functions**:

  - `SearchFunction`: Handles property search and details requests from the API Gateway
  - `RequestApprovalFunction`: Processes queued API requests to approve properties from the ingest queue
  - `PublicationEvaluationEventHandlerFunction`: Responds to PublicationEvaluationCompleted events from the Approvals service

- **API Gateway REST API** (`UnicornWebApi`): RESTful API for property management with endpoints for:

  - Property search by city and street
  - Property details retrieval
  - Publication approval requests

- **DynamoDB Table** (`PropertiesTable`): Stores property details with composite primary key (PK, SK)

- **SQS Queues**:

  - `UnicornWebIngestQueue`: Queues API Gateway requests for async processing
  - `UnicornWebIngestDLQ`: Dead letter queue for failed ingest processing
  - `PublicationEvaluationEventHandlerDLQ`: Dead letter queue for failed event processing

- **EventBridge Components**:
  - `UnicornWebEventBus`: Central event bus for web service events
  - `UnicornWebCatchAllRule`: Development rule for capturing all events for debugging
  - `UnicornWebCatchAllLogGroup`: CloudWatch log group for event debugging

**Notable Features**:

- RESTful API with OpenAPI 3.0 specification
- Event-driven architecture with EventBridge integration
- Async request processing via SQS queues
- Comprehensive error handling with multiple DLQ strategies
- Environment-specific configuration and logging levels
- API Gateway integration with both Lambda and SQS

**Dependencies**: Requires domain resources to be deployed first for EventBridge bus and SSM parameters.

### 2. `api.yaml` - OpenAPI Specification

**Purpose**: Defines the RESTful API specification for the Unicorn Web Service using OpenAPI 3.0.

**Key Endpoints**:

- **POST /request_approval**: Submits property publication approval requests
- **GET /search/{country}/{city}**: Searches properties by city
- **GET /search/{country}/{city}/{street}**: Searches properties by street
- **GET /properties/{country}/{city}/{street}/{number}**: Retrieves detailed property information

**Integration Features**:

- API Gateway integration with SQS for async request processing
- Lambda proxy integration for search and property details
- Request validation and response schemas
- Comprehensive data models for properties, addresses, and offers

### 3. `domain.yaml` - Domain Resources Template

**Purpose**: Creates shared domain-level infrastructure that can be used by multiple services within the Unicorn Web domain.

**Key Resources**:

- **EventBridge Event Bus** (`WebEventBus`): Central event bus for web service events
- **SSM Parameters**: Store event bus name, ARN, and schema registry information for cross-service access
- **Event Bus Logging**: Complete logging setup with delivery sources, destinations, and delivery configurations
- **Schema Registry** (`WebSchemaRegistry`): Event schema management for web service events
- **Event Bus Policies**: Access control for creating rules and publishing events
- **EventBridge Role** (`WebEventBridgeRole`): IAM role for cross-service event routing

**Notable Features**:

- Configurable logging levels based on stage (INFO for dev/local, ERROR for prod)
- Proper deletion policies for all logging resources to ensure clean stack deletion
- Cross-service event bus policy restricting rule creation to specific sources
- Exported EventBridge role for use in subscription templates
- Comprehensive event bus logging with delivery sources and destinations

**Note**: This template provides the foundation for event-driven integrations for all Unicorn Web services. It needs to be deployed before any other services.

### 4. `schema-registry/PublicationApprovalRequested-schema.yaml` - Event Schema Template

**Purpose**: Defines the event schema for `PublicationApprovalRequested` events in the EventBridge Schema Registry.

**Key Resources**:

- **PublicationEvaluationCompleted** (`AWS::EventSchemas::Schema`): OpenAPI 3.0 schema definition for publication approval request events

**Schema Structure**:

- **Event Source**: Retrieved from SSM parameter (unicorn-web namespace)
- **Detail Type**: `PublicationApprovalRequested`
- **Required Fields**:
  - `property_id`: Unique identifier for the property
  - `address`: Property address details (country, city, street, number)
  - `description`: Property description
  - `images`: Array of property image URLs
  - `listprice`: Property listing price
  - `currency`: Price currency
  - `contract`: Contract type
  - `status`: Property status

**Integration**:

- Uses SSM parameter resolution to get the schema registry name from domain template
- Follows AWS EventBridge event envelope structure
- Enables code generation for strongly-typed event handling

### 5. `subscriptions/` - Event Subscription Templates

**Purpose**: Manages cross-service event subscriptions by creating EventBridge rules that route events between different service event buses.

#### 5.1 `unicorn-approvals-subscriptions.yaml`

**Key Resources**:

- **PublicationEvaluationCompletedSubscriptionRule**: EventBridge rule that subscribes to PublicationEvaluationCompleted events from the Unicorn Approvals service and forwards them to the Unicorn Web event bus for processing publication approval results

**Event Flow**:

- Listens to: Unicorn Approvals Event Bus
- Event Type: `PublicationEvaluationCompleted`
- Routes to: Unicorn Web Event Bus

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
   --stack-name uni-prop-local-web-domain \
   --parameter-overrides Stage=local \
   --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
   --region ap-southeast-2 \
   --resolve-s3
   ```

2. **Deploy Main Service Template**:

   ```bash
   sam deploy \
   --template-file ./infrastructure/web-service.yaml \
   --stack-name uni-prop-local-web-service \
   --parameter-overrides Stage=local \
   --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
   --region ap-southeast-2 \
   --resolve-s3
   ```

3. **Deploy Event Schema** (For schema governance):

   ```bash
   sam deploy \
      --template-file ./infrastructure/schema-registry/PublicationApprovalRequested-schema.yaml \
      --stack-name uni-prop-local-web-publication-approval-requested-schema \
      --parameter-overrides Stage=local \
      --capabilities CAPABILITY_IAM \
      --region ap-southeast-2 \
      --resolve-s3
   ```

4. **Deploy Event Subscriptions**:

   ```bash
   # Deploy Approvals subscriptions
   sam deploy \
      --template-file ./infrastructure/subscriptions/unicorn-approvals-subscriptions.yaml \
      --stack-name uni-prop-local-web-approvals-subscriptions \
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
  - `/uni-prop/UnicornWebNamespace`
  - `/uni-prop/UnicornApprovalsNamespace` (for subscriptions)

### Cross-Template Dependencies

- Subscription templates depend on SSM parameters created by `domain.yaml`
- `PublicationApprovalRequested-schema.yaml` depends on schema registry created by `domain.yaml`
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

The Web service follows an event-driven architecture pattern:

- **Domain Events**: Publishes `PublicationApprovalRequested` events
- **Event Subscriptions**: Consumes `PublicationEvaluationCompleted` events from Approvals service
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

The Web service acts as both an event producer and consumer:

- **Produces**: `PublicationApprovalRequested` events for the Approvals service
- **Consumes**: `PublicationEvaluationCompleted` events from Approvals service
- **API Gateway**: Provides RESTful endpoints for property search and publication requests
- **Async Processing**: Uses SQS queues for decoupling API requests from business logic

This design enables loose coupling between services while maintaining clear event ownership and subscription management.
