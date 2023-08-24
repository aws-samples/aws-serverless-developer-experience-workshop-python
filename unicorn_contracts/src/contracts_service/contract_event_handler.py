# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os

import boto3
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.utilities.data_classes import event_source, SQSEvent
from aws_lambda_powertools.utilities.typing import LambdaContext

# from contracts_service.enums import ContractStatus


# Initialise Environment variables
if (SERVICE_NAMESPACE := os.environ.get("SERVICE_NAMESPACE")) is None:
    raise EnvironmentError("SERVICE_NAMESPACE environment variable is undefined")
if (DYNAMODB_TABLE := os.environ.get("DYNAMODB_TABLE")) is None:
    raise EnvironmentError("DYNAMODB_TABLE environment variable is undefined")

# Initialise PowerTools
logger: Logger = Logger()
tracer: Tracer = Tracer()
metrics: Metrics = Metrics()

# Initialise boto3 clients
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)  # type: ignore


@metrics.log_metrics(capture_cold_start_metric=True) # type: ignore
@logger.inject_lambda_context()
@tracer.capture_method
@event_source(data_class=SQSEvent)
def lambda_handler(event: SQSEvent, context: LambdaContext):
    # Multiple records can be delivered in a single event
    for record in event.records:
        match record.message_attributes.get('HttpMethod'):
            case 'POST':
                create_contract(record.json_body)
            case 'PUT':
                update_contract(record.json_body)
            case other:
                raise Exception(f'Unable to handle HttpMethod {other}')


@tracer.capture_method
def create_contract(contract: dict) -> None:
    """Create contract inside DynamoDB table

    Parameters
    ----------
        contract (dict): _description_

    Returns
    -------
    dict
        DynamoDB put Item response
    """
    logger.info(contract)

    # if contract id exists:
    #   if constract status is APPROVED | DRAFT:
    #     log message
    #     return
    # create with status = DRAFT
    # return

    # return table.put_item(Item=contract,)


@tracer.capture_method
def update_contract(contract: dict) -> None:
    """Update an existing contract inside DynamoDB table

    Parameters
    ----------
        contract (dict): _description_

    Returns
    -------
    dict
        DynamoDB put Item response
    """
    logger.info(contract)

    # if contract doesnt exist
    #   lod message
    #   return
    # if contract status in [ APPROVED | CANCELLED | CLOSED | EXPIRED ]
    #   close
    #   return
    # update contract status to APPROVED

    # return table.put_item(Item=contract,)
