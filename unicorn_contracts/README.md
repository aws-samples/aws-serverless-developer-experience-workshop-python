# Developing Unicorn Contracts

![Contracts Service Architecture](https://static.us-east-1.prod.workshops.aws/public/f273b5fc-17cd-406b-9e63-1d331b00589d/static/images/architecture-contracts.png)

## Architecture overview

The **Unicorn Contracts** service manages contractual relationships between customers and Unicorn Properties agency. The service handles standard terms and conditions, property service rates, fees, and additional services.

Each property can have only one active contract. Properties use their address as a unique identifier instead of a GUID, which correlates across services.

For example: `usa/anytown/main-street/111`.

The contract workflow operates as follows:

1. Agents submit contract creation/update commands through the Contracts API
1. The API sends requests to Amazon SQS
1. A Contracts function processes the queue messages and updates Amazon DynamoDB
1. DynamoDB Streams captures contract changes
1. Amazon EventBridge Pipes transforms the DynamoDB records into ContractStatusChanged events
1. Unicorn Approvals consumes these events to track contract changes without direct database dependencies

An example of `ContractStatusChanged` event:

```json
{
  "version": "0",
  "account": "123456789012",
  "region": "us-east-1",
  "detail-type": "ContractStatusChanged",
  "source": "unicorn-contracts",
  "time": "2022-08-14T22:06:31Z",
  "id": "c071bfbf-83c4-49ca-a6ff-3df053957145",
  "resources": [],
  "detail": {
    "contract_updated_on": "10/08/2022 19:56:30",
    "ContractId": "617dda8c-e79b-406a-bc5b-3a4712f5e4d7",
    "PropertyId": "usa/anytown/main-street/111",
    "ContractStatus": "DRAFT"
  }
}
```

### Testing the APIs

```bash
export API=`aws cloudformation describe-stacks --stack-name uni-prop-local-contract --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text`

curl --location --request POST "${API}contract" \
--header 'Content-Type: application/json' \
--data-raw '{
"address": {
"country": "USA",
"city": "Anytown",
"street": "Main Street",
"number": 111
},
"seller_name": "John Doe",
"property_id": "usa/anytown/main-street/111"
}'


curl --location --request PUT "${API}contract" \
--header 'Content-Type: application/json' \
--data-raw '{"property_id": "usa/anytown/main-street/111"}' | jq
```
