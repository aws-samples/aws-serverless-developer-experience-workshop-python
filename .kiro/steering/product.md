# Unicorn Properties - Product Overview

## What is Unicorn Properties?

Unicorn Properties is a serverless, event-driven real estate management platform that handles property listings, contracts, and approvals. It is built as a reference architecture for the AWS Serverless Developer Experience workshop.

## Business Domain

The platform manages three core domains, each implemented as an independent microservice:

- **Contracts** (`Unicorn.Contracts`) - Manages contractual relationships between property sellers and Unicorn Properties, including property definitions, terms, and engagement costs
- **Approvals** (`Unicorn.Approvals`) - Implements the approval workflow that validates contract existence, content safety, image safety, and contract approval status before a listing can be published
- **Web** (`Unicorn.Web`) - Manages property listing details (address, price, description, photos) for the public website, displaying only approved listings

## Key Features

- Event-driven architecture using Amazon EventBridge
- Serverless compute with AWS Lambda
- Property listing management and search
- Automated approval workflows using AWS Step Functions
- Content and image validation using AWS AI services
- Real-time contract status tracking

## Architecture Pattern

The system follows a microservices architecture where each service:

- Owns its domain: a dedicated EventBridge event bus, schema registry, and event subscriptions
- Uses DynamoDB for data persistence
- Communicates with other services asynchronously through events, never direct API calls
- Maintains clear service boundaries with well-defined APIs and published event contracts
