# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
import os

import boto3
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import correlation_paths
from botocore.exceptions import ClientError

from contracts_service.contract_status import ContractStatus
from contracts_service.exceptions import (ContractNotFoundException,
                                  EventValidationException)
from contracts_service.helper import get_current_date, get_event_body, publish_event, validate_event, get_env

# Initialise Environment variables
SERVICE_NAMESPACE = get_env("SERVICE_NAMESPACE")
DYNAMODB_TABLE = get_env("DYNAMODB_TABLE")

# Initialise PowerTools
logger: Logger = Logger()
tracer: Tracer = Tracer()
metrics: Metrics = Metrics()

# Initialise boto3 clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)  # type: ignore


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST, log_event=True)  # type: ignore
@metrics.log_metrics(capture_cold_start_metric=True)  # type: ignore
@tracer.capture_method
def lambda_handler(event, context):
    """Lambda handler for updating contract information

    Parameters
    ----------
    event : dict
        Amazon API Gateway event
    context : dict
        AWS Lambda context

    Returns
    -------
    dict
        HTTP response
    """

    # Get contract and property details from the event
    try:
        event_json = validate_event(event, {"property_id"})
    except EventValidationException as ex:
        return ex.apigw_return

    #  Load existing contract
    try:
        existing_contract = get_existing_contract(event_json["property_id"])
        logger.info({"Found existing contract": existing_contract })
    except ContractNotFoundException  as ex:
        logger.info({"Contract not found!"})
        return ex.apigw_return

    #  Set current date
    current_date = get_current_date(context.aws_request_id)

    # define contract with approved status
    contract = {
        "contract_id": existing_contract['contract_id'],
        "property_id": existing_contract["property_id"],
        "contract_last_modified_on": current_date,
        "contract_status": ContractStatus.APPROVED.name,
    }

    # Update DDB entry
    update_contract(contract)

    # Annotate trace with contract status
    tracer.put_annotation(key="ContractStatus", value=contract["contract_status"])

    # Publish ContractStatusChanged event
    publish_event(contract, context.aws_request_id)

    return {
        "statusCode": 200,
        "body": json.dumps(contract)
    }

@tracer.capture_method
def update_contract(contract) -> dict:
    """Update contract inside DynamoDB table

    Args:
        contract (dict): _description_

    Returns:
        dict: _description_
    """

    logger.info(msg={"Updating contract": contract})

    try:
        response = table.update_item(
                TableName=DYNAMODB_TABLE,
                Key={
                    'property_id': contract['property_id'],
                },
                UpdateExpression="set contract_status=:t, modified_date=:m",
                ExpressionAttributeValues={
                    ':t': contract['contract_status'],
                    ':m': contract['contract_last_modified_on']
                },
                ReturnValues="UPDATED_NEW"
        )

        return response["Attributes"]
        
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.exception("Error updating Contract status.")
        raise error


@tracer.capture_method
def get_existing_contract(property_id: str) -> dict:
    """Returns Contract for a specified property

    Parameters
    ----------
    property_id : str
        Property ID

    Returns
    -------
    dict
        Contract info
    """

    try:
        response = table.get_item(
            Key={
                'property_id': property_id
            }
        )
        return response["Item"]

    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.exception("Error getting contract.")
            raise ContractNotFoundException() from error
        raise error
    except KeyError as _:
        raise ContractNotFoundException() from _
