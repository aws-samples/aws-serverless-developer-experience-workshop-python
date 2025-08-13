# Developing Unicorn Approvals

![Properties Approval Architecture](https://static.us-east-1.prod.workshops.aws/public/f273b5fc-17cd-406b-9e63-1d331b00589d/static/images/architecture-approvals.png)

## Architecture overview

**Unicorn Approvals** uses an AWS Step Functions state machine to approve property listings for Unicorn Web. The workflow checks for contract information, description sentiment and safe images, and verifies the contract is approved before approving the listing. It publishes the result via the `PublicationEvaluationCompleted` event.

A Unicorn Properties agent initiates the workflow by requesting to approve a listing, generating a `PublicationApprovalRequested` event with property information. To decouple from the Contracts Service, the Approvals service maintains a local copy of contract status by consuming the ContractStatusChanged event.

The workflow checks the contract state. If the contract is in the WaitForContractApproval state, it updates the contract status for the property with its task token, triggering a DynamoDB stream event. The Property Approval Sync function handles these events and passes the task token back to the state machine based on the contract state.

If the workflow completes successfully, it emits a PublicationEvaluationCompleted event with an **approved** or **declined** evaluation result, which Unicorn Web listens to update its publication flag.

**Note:** Upon deleting the CloudFormation stack for this service, check if the `ApprovalStateMachine` StepFunction doesn't have any executions in `RUNNING` state. If there are, cancel those execution prior to deleting the CloudFormation stack.
