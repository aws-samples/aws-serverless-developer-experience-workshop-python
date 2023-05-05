# Developing Unicorn Properties

![Properties Approval Architecture](https://static.us-east-1.prod.workshops.aws/public/fd291886-89c4-4336-b21b-5747484b495d/static/images/architecture-properties.png)

## Architecture overview

Unicorn Properties is primarily responsible for approving property listings for Unicorn Web.

A core component of Unicorn Properties is the approvals workflow. The approvals workflow is implemented using an AWS Step Functions state machine. At a high level, the workflow will:

* Check whether or not it has any contract information for the property it needs to approve. If there is no contract information, the approval process cannot be completed.
* Ensure the sentiment of the property description is positive and that there no unsafe images. All checks must pass for the listing to be made public.
* Ensure that the contract is in an APPROVED state before it can approve the listing. This accounts for a situation where the property listings are created before the contract has been signed and the services for Unicorn Properties are paid for.
* Publish the result of the workflow via the `PublicationEvaluationCompleted` event.

The workflow is initiated by a request made by an Unicorn Properties **agent** to have the property approved for publication. Once they have created a property listing (added property details and photos), they initiate the request in Unicorn Web, which generates a `PublicationApprovalRequested` event. This event contains the property information which the workflow processes.

In order process the approvals workflow successfully, the properties service needs to know the current status of a contract. To remain fully decoupled from the **Contracts Service**, it maintains a local copy of contract status by consuming the `ContractStatusChanged` event. This is eliminates the need for the Contracts service to expose an API that gives other services access to its database, and allows the Properties service to function autonomously.

When the workflow is paused to check to see whether or not the contract is in an approved state, the `WaitForContractApproval` state will update a contract status for a specified property with its task token. This initiates a stream event on the DynamoDB table. The Property approvals sync function handles DynamoDB stream events. It determines whether or not to pass AWS Step Function task token back to the state machine based on the contract state.

If workflow is completed successfully, it will emit a `PublicationEvaluationCompleted` event, with an evaluation result of `APPROVED` or `DECLINED`. This is what the Property Web will listen to in order to make the list available for publication.
