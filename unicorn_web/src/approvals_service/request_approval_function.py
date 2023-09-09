# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import re
import json

import boto3
from botocore.exceptions import ClientError

# import aws_lambda_powertools.event_handler.exceptions
from aws_lambda_powertools.logging import Logger, correlation_paths
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.metrics import Metrics, MetricUnit
from aws_lambda_powertools.event_handler import content_types
from aws_lambda_powertools.event_handler.api_gateway import ApiGatewayResolver, Response
from aws_lambda_powertools.event_handler.exceptions import NotFoundError, InternalServerError, BadRequestError


# Initialise Environment variables
if (SERVICE_NAMESPACE := os.environ.get('SERVICE_NAMESPACE')) is None:
    raise InternalServerError('SERVICE_NAMESPACE environment variable is undefined')
if (DYNAMODB_TABLE := os.environ.get('DYNAMODB_TABLE')) is None:
    raise InternalServerError('DYNAMODB_TABLE environment variable is undefined')
if (EVENT_BUS := os.environ.get('EVENT_BUS')) is None:
    raise InternalServerError('EVENT_BUS environment variable is undefined')

EXPRESSION = r"[a-z-]+\/[a-z-]+\/[a-z][a-z0-9-]*\/[0-9-]+"
TARGET_STATE = 'PENDING'

# Initialise PowerTools
logger: Logger = Logger()
tracer: Tracer = Tracer()
metrics: Metrics = Metrics()

# Initialise boto3 clients
event_bridge = boto3.client('events')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)  # type: ignore

app = ApiGatewayResolver()


@app.post('/request_approval')
@tracer.capture_method
def request_approval():
    """Emits event that user requested a property approval

    Returns
    -------
    Confirmation that the event was emitted successfully
    """
    logger.info('Call to request_approval')

    try:
        raw_data = app.current_event.json_body
    except json.JSONDecodeError as e:
        error_msg = f"Unable to parse event input as JSON: {e}"
        logger.error(error_msg)
        raise BadRequestError(error_msg)

    property_id = raw_data['property_id']

    if not re.fullmatch(EXPRESSION, property_id):
        error_msg = f"Input invalid; must conform to regular expression: {EXPRESSION}"
        logger.error(error_msg)
        raise BadRequestError(error_msg)

    country, city, street, number = property_id.split('/')

    pk_details = f"{country}#{city}".replace(' ', '-').lower()
    pk = f"PROPERTY#{pk_details}"
    sk = f"{street}#{str(number)}".replace(' ', '-').lower()

    response = table.get_item(
        Key={
            'PK': pk,
            'SK': sk
        },
        AttributesToGet=['currency', 'status', 'listprice', 'contract', 'country', 'city', 'number', 'images',
                         'description', 'street']
    )
    if 'Item' not in response:
        logger.info(f"No item found in table {DYNAMODB_TABLE} with PK {pk} and SK {sk}")
        raise NotFoundError(f"No property found in database with the requested property id")

    item = response['Item']

    status = item.pop('status')

    if status in [ 'APPROVED', 'DECLINED', 'PENDING' ]:
        return {'result': f"Property is already {status}; no action taken" }

    item['property_id'] = property_id
    item['address'] = {
        'country': item.pop('country'),
        'city': item.pop('city'),
        'street': item.pop('street'),
        'number': int(item.pop('number')),
    }
    item['status'] = TARGET_STATE
    item['listprice'] = int(item['listprice'])

    try:
        event_bridge_response = event_bridge.put_events(
            Entries=[
                {
                    'Source': SERVICE_NAMESPACE,
                    'DetailType': 'PublicationApprovalRequested',
                    'Resources': [property_id],
                    'Detail': json.dumps(item),
                    'EventBusName': EVENT_BUS,
                },
            ]
        )
    except ClientError as e:
        error_msg = f"Unable to send event to Event Bus: {e}"
        logger.error(error_msg)
        raise InternalServerError(error_msg)

    failed_count = event_bridge_response['FailedEntryCount']

    if failed_count > 0:
        error_msg = f"Error sending requests to Event Bus; {failed_count} message(s) failed"
        logger.error(error_msg)
        raise InternalServerError(error_msg)

    entry_count = len(event_bridge_response['Entries'])
    logger.info(f"Sent event to EventBridge; {failed_count} records failed; {entry_count} entries received")

    metrics.add_metric(name='ApprovalsRequested', unit=MetricUnit.Count, value=1)
    logger.info(f"Storing new property in DynamoDB with PK {pk} and SK {sk}")
    dynamodb_response = table.update_item(
        Key={
            'PK': pk,
            'SK': sk,
        },
        AttributeUpdates={
            'status': {
                'Value': TARGET_STATE,
                'Action': 'PUT',
            }
        },
    )
    http_status_code = dynamodb_response['ResponseMetadata']['HTTPStatusCode']
    logger.info(f"Stored item in DynamoDB; responded with status code {http_status_code}")

    return {'result': 'Approval Requested'}


@app.exception_handler(ClientError)
def handle_service_error(ex: ClientError):
    """Handles any error coming from a remote service request made through Boto3 (ClientError)

    Parameters
    ----------
    ex : Boto3 error occuring during an AWS API call anywhere in this Lambda function

    Returns
    -------
    Specific HTTP error code to be returned to the client as well as a friendly error message
    """
    error_code = ex.response['Error']['Code']
    http_status_code = ex.response['ResponseMetadata']['HTTPStatusCode']
    error_message = ex.response['Error']['Message']
    logger.exception(f"EXCEPTION {error_code} ({http_status_code}): {error_message}")
    return Response(
        status_code=http_status_code,
        content_type=content_types.TEXT_PLAIN,
        body=error_code
    )


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)  # type: ignore
@tracer.capture_lambda_handler  # type: ignore
@metrics.log_metrics
def lambda_handler(event, context):
    """Main entry point for PropertyWeb lambda function

    Parameters
    ----------
    event : API Gateway Lambda Proxy Request
        The event passed to the function.
    context : AWS Lambda Context
        The context for the Lambda function.

    Returns
    -------
    API Gateway Lambda Proxy Response
        HTTP response object with Contract and Property ID
    """
    logger.info(event)
    return app.resolve(event, context)
