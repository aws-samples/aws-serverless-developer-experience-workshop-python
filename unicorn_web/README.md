# Developing Unicorn Web

![Properties Web Architecture](https://static.us-east-1.prod.workshops.aws/public/f273b5fc-17cd-406b-9e63-1d331b00589d/static/images/architecture-properties-web.png)

## Architecture Overview

Unicorn Web lets customers search for and view property listings. The Web API also allows Unicorn Properties agents to request approval for specific properties that they want to publish so they may be returned in customer searches results. These requests are sent to the Unicorn Approvals service for validation.

Lambda functions handle API Gateway requests to:

- Search approved property listings: The **Search function** retrieves property listings marked as APPROVED from the DynamoDB table using multiple search patterns.

- Request property listing approval: The **Approval function** sends an EventBridge event requesting approval for a property listing specified in the payload.

- Process approved listings: The **Publication Evaluation Event Handler function** processes `PublicationEvaluationCompleted` events from the Unicorn Approvals service and writes the evaluation result to the DynamoDB table.

### Testing the APIs

```bash
export API=`aws cloudformation describe-stacks --stack-name uni-prop-local-web --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text`

curl --location --request POST "${API}request_approval" \
--header 'Content-Type: application/json' \
--data-raw '{"PropertyId": "usa/anytown/main-street/111"}'


curl -X POST ${API_URL}request_approval \
    -H 'Content-Type: application/json' \
    -d '{"PropertyId":"usa/anytown/main-street/111"}' | jq
```
