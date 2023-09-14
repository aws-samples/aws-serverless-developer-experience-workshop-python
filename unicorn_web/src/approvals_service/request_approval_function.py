# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from typing import Tuple
import os
import re
import json

import boto3
from botocore.exceptions import ClientError

from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.metrics import Metrics, MetricUnit
from aws_lambda_powertools.utilities.data_classes import event_source, SQSEvent
from aws_lambda_powertools.utilities.typing import LambdaContext


# Initialise Environment variables
if (SERVICE_NAMESPACE := os.environ.get('SERVICE_NAMESPACE')) is None:
    raise EnvironmentError('SERVICE_NAMESPACE environment variable is undefined')
if (DYNAMODB_TABLE := os.environ.get('DYNAMODB_TABLE')) is None:
    raise EnvironmentError('DYNAMODB_TABLE environment variable is undefined')
if (EVENT_BUS := os.environ.get('EVENT_BUS')) is None:
    raise EnvironmentError('EVENT_BUS environment variable is undefined')

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


@tracer.capture_method
def publish_event(detail_type, resources, detail):
    try:
        entry = {'EventBusName': EVENT_BUS,
                 'Source': SERVICE_NAMESPACE,
                 'DetailType': detail_type,
                 'Resources': resources,
                 'Detail': json.dumps(detail)}
        logger.info(entry)

        response = event_bridge.put_events(Entries=[entry])
        logger.info(response)
    except ClientError as e:
        error_msg = f"Unable to send event to Event Bus: {e}"
        logger.error(error_msg)
        raise Exception(error_msg)

    failed_count = response['FailedEntryCount']

    if failed_count > 0:
        error_msg = f"Error sending requests to Event Bus; {failed_count} message(s) failed"
        logger.error(error_msg)
        raise Exception(error_msg)

    entry_count = len(response['Entries'])
    logger.info(f"Sent event to EventBridge; {failed_count} records failed; {entry_count} entries received")
    return response


@tracer.capture_method
def get_property(pk: str, sk: str) -> dict:
    response = table.get_item(
        Key={ 'PK': pk, 'SK': sk },
        AttributesToGet=['currency', 'status', 'listprice', 'contract', 
                         'country', 'city', 'number', 'images',
                         'description', 'street']
    )
    if 'Item' not in response:
        logger.info(f"No item found in table {DYNAMODB_TABLE} with PK {pk} and SK {sk}")
        return dict()

    return response['Item']


@tracer.capture_method
def get_keys_for_property(property_id: str) -> Tuple[str, str]:
    # Validate Property ID
    if not re.fullmatch(EXPRESSION, property_id):
        error_msg = f"Invalid property id '{property_id}'; must conform to regular expression: {EXPRESSION}"
        logger.error(error_msg)
        return '', ''

    # Extract components from property_id
    country, city, street, number = property_id.split('/')

    # Construct DDB PK & SK keys for this property
    pk_details = f"{country}#{city}".replace(' ', '-').lower()
    pk = f"PROPERTY#{pk_details}"
    sk = f"{street}#{str(number)}".replace(' ', '-').lower()
    return pk, sk


@tracer.capture_method
def request_approval(raw_data: dict):
    property_id = raw_data['property_id']

    # Validate property_id, parse it and extract DynamoDB PK/SK values
    pk, sk = get_keys_for_property(property_id=property_id)
    # Get property details from database
    item = get_property(pk=pk, sk=sk)

    if (status := item.pop('status')) in [ 'APPROVED' ]:
        logger.info(f"Property '{property_id}' is already {status}; no action taken")
        return

    item['property_id'] = property_id
    item['address'] = {
        'country': item.pop('country'),
        'city': item.pop('city'),
        'street': item.pop('street'),
        'number': int(item.pop('number')),
    }
    item['status'] = TARGET_STATE
    item['listprice'] = int(item['listprice'])

    metrics.add_metric(name='ApprovalsRequested', unit=MetricUnit.Count, value=1)
    publish_event(detail_type='PublicationApprovalRequested', resources=[property_id], detail=item)


@metrics.log_metrics(capture_cold_start_metric=True) # type: ignore
@logger.inject_lambda_context
@tracer.capture_method
@event_source(data_class=SQSEvent)
def lambda_handler(event: SQSEvent, context: LambdaContext):
    # Multiple records can be delivered in a single event
    for record in event.records:
        request_approval(record.json_body)
