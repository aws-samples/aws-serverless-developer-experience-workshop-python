# Developing Unicorn Web

![Properties Web Architecture](https://static.us-east-1.prod.workshops.aws/public/fd291886-89c4-4336-b21b-5747484b495d/static/images/architecture-properties-web.png)

## Architecture Overview

Unicorn Web is primarily responsible for allowing customers to search and view property listings. It also supports ability for agents to request approval for specific property. Those approval requests are sent to Property service for validation, before Properties table is updated with approval evaluation results.

A core component of Unicorn Web are the Lambda functions which are responsible with completing API Gateway requests to:

- search approved property listings
This function interacts with DynamoDB table to retrieve property listings marked as `APPROVED`. The API Gateway implementation and lambda code support multiple types of search patterns, and allow searching by city, street, or house number.

- request approval of property listing
This function sends an event to EventBridge requesting an approval for a property listing specified in the payload sent from client

- publication approved function
There is also a lambda function responsible for receiving any "Approval Evaluation Completed" events from EventBridge. This function writes the evaluation result to DynamoDB table.
