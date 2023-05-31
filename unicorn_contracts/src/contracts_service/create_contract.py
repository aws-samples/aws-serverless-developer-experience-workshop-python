# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import os
import uuid

import boto3
from aws_lambda_powertools.logging import Logger, correlation_paths
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.tracing import Tracer

from contracts_service.contract_status import ContractStatus
from contracts_service.exceptions import EventValidationException
from contracts_service.helper import get_stable_date, get_event_body, validate_event, publish_event, get_env

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
event_bridge = boto3.client("events")


@metrics.log_metrics(capture_cold_start_metric=True)  # type: ignore
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True)  # type: ignore
@tracer.capture_method
def lambda_handler(event, context):
    """Lambda handler for new_contract.

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
    # Get contract and property details from the event
    try:
        event_json = validate_event(event)
    except EventValidationException as ex:
        return ex.apigw_return

    # Create new Contract
    current_date: str = get_stable_date(context.aws_request_id)

    contract = {
        "property_id": event_json["property_id"],  # PK
        "contact_created": current_date,
        "contract_last_modified_on": current_date,
        "contract_id": str(uuid.uuid4()),
        "address": event_json["address"],
        "seller_name": event_json["seller_name"],
        "contract_status": ContractStatus.DRAFT.name,
    }

    # create entry in DDB for new contract
    create_contract(contract)

    # Annotate trace with contract status
    tracer.put_annotation(key="ContractStatus", value=contract["contract_status"])

    # Publish ContractStatusChanged event
    publish_event(contract, context.aws_request_id)

    # return generated contract ID back to user:
    return {
        "statusCode": 200,
        "body": json.dumps(contract)
    }


@tracer.capture_method
def create_contract(contract) -> dict:
    """Create contract inside DynamoDB table

    Parameters
    ----------
        contract (dict): _description_

    Returns
    -------
    dict
        DynamoDB put Item response
    """
    # TODO: create entry in DDB for new contract
    return table.put_item(Item=contract,)


@tracer.capture_method
def validate_event(event):
    """Validates the body of the API Gateway event

    Parameters
    ----------
    event : dict
        API Gateway event

    Returns
    -------
    dict
        The body of the API

    Raises
    ------
    EventValidationException
        The ``Raises`` section is a list of all exceptions
        that are relevant to the interface.
    """

    try:
        event_json = get_event_body(event)
    except Exception as ex:
        logger.exception(ex)
        raise EventValidationException() from ex

    for i in ["property_id", "address", "seller_name"]:
        if i not in event_json.keys():
            raise EventValidationException()

    return event_json
