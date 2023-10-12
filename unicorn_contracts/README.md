# Developing Unicorn Contracts

![Contracts Service Architecture](https://static.us-east-1.prod.workshops.aws/public/ba5300cf-a325-4124-83bf-5789cc30b8ff/static/images/architecture-contracts.png)

## Architecture overview

Unicorn Contract manages the contractual relationship between the customers and the Unicorn Properties agency. It's primary function is to allow Unicorn Properties agents to create a new contract for a property listing, and to have the contract approved once it's ready.

The architecture is fairly straight forward. An API exposes the create contract and update contract methods. This information is recorded in a Amazon DynamoDB table which will contain all latest information about the contract and it's status.

Each time a new contract is created or updated, Unicorn Contracts publishes a `ContractStatusChanged` event to Amazon EventBridge signalling changes to the contract status. These events are consumed by **Unicorn Properties**, so it can track changes to contracts, without needing to take a direct dependency on Unicorn Contracts and it's database.

Here is an example of an event that is published to EventBridge:

```json
{
  "version": "0",
  "account": "123456789012",
  "region": "us-east-1",
  "detail-type": "ContractStatusChanged",
  "source": "unicorn.contracts",
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
