[![Build & Test Workflow](https://github.com/aws-samples/aws-serverless-developer-experience-workshop-python/actions/workflows/build.yml/badge.svg)](https://github.com/aws-samples/aws-serverless-developer-experience-workshop-python/actions/workflows/build.yml)

# AWS Serverless Developer Experience workshop reference architecture (Python)

<img src="./docs/workshop_logo.png" alt="AWS Serverless Developer Experience Workshop Reference Architecture" width="80%" />

This repository contains the Python reference architecture for the AWS Serverless Developer Experience workshop.

The AWS Serverless Developer Experience Workshop is a comprehensive, hands-on training program designed to equip developers with practical serverless development skills using the [**AWS Serverless Application Model (AWS SAM)**](https://aws.amazon.com/serverless/sam/) and **AWS SAM CLI**.

The workshop employs a practical, code-centric approach, emphasizing direct implementation and real-world scenario exploration to ensure you develop serverless development skills across several critical areas including distributed event-driven architectures, messaging patterns, orchestration, and observability. You will explore open-source tools, [Powertools for AWS](https://powertools.aws.dev/), and simplified CI/CD deployments with AWS SAM Pipelines. By the end, you will be familiar with serverless developer workflows, microservice composition using AWS SAM, serverless development best practices, and applied event-driven architectures.

The 6-8 hour workshop assumes your practical development skills in Python, TypeScript, Java, or .NET, and familiarity with [Amazon API Gateway](https://aws.amazon.com/apigateway/), [AWS Lambda](https://aws.amazon.com/lambda/), [Amazon EventBridge](https://aws.amazon.com/eventbridge/), [AWS Step Functions](https://aws.amazon.com/step-functions/), and [Amazon DynamoDB](https://aws.amazon.com/dynamodb/).

## Introducing the Unicorn Properties architecture

![AWS Serverless Developer Experience Workshop Reference Architecture](./docs/architecture.png)

Real estate company **Unicorn Properties** needs to manage publishing of new property listings and sale contracts linked to individual properties, and provide a way for customers to view approved listings. They adopted a serverless, event-driven architecture with two primary domains: **Contracts** (managed by Contracts Service) and **Properties** (managed by Web and Approvals Services).

**Unicorn Contracts** (using the `Unicorn.Contracts` namespace) service manages contractual relationships between property sellers and Unicorn Approvals, defining properties for sale, terms, and engagement costs.

**Unicorn Approvals** (using the `Unicorn.Approvals` namespace) service approves property listings by implementing a workflow that checks for contract existence, content and image safety, and contract approval before publishing.

**Unicorn Web** (using the `Unicorn.Web` namespace) manages property listing details (address, sale price, description, photos) to be published on the website, with only approved listings visible to the public.

## Credits

This workshop introduces you to some open-source tools that can help you build serverless applications. This is not an exhaustive list, but a small selection of what you will be using in the workshop.

Many thanks to all the AWS teams and community builders who have contributed to this list:

| Tools                    | Description                                                                                                                        | Download / Installation Instructions           |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| cfn-lint                 | Validate AWS CloudFormation yaml/json templates against the AWS CloudFormation Resource Specification and additional checks.       | https://github.com/aws-cloudformation/cfn-lint |
| cfn-lint-serverless      | Compilation of rules to validate infrastructure-as-code templates against recommended practices for serverless applications.       | https://github.com/awslabs/serverless-rules    |
| @mhlabs/iam-policies-cli | CLI for generating AWS IAM policy documents or SAM policy templates based on the JSON definition used in the AWS Policy Generator. | https://github.com/mhlabs/iam-policies-cli     |
| @mhlabs/evb-cli          | Pattern generator and debugging tool for Amazon EventBridge                                                                        | https://github.com/mhlabs/evb-cli              |
