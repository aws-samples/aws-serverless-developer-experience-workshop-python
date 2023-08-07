# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json

import boto3
from boto3.dynamodb.types import TypeDeserializer
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.event_handler.exceptions import InternalServerError


# Initialise Environment variables
if (SERVICE_NAMESPACE := os.environ.get("SERVICE_NAMESPACE")) is None:
    raise InternalServerError("SERVICE_NAMESPACE environment variable is undefined")
if (CONTRACT_STATUS_TABLE := os.environ.get("CONTRACT_STATUS_TABLE")) is None:
    raise InternalServerError("CONTRACT_STATUS_TABLE environment variable is undefined")

# Initialise PowerTools
logger: Logger = Logger()
tracer: Tracer = Tracer()
metrics: Metrics = Metrics()

# Initialise boto3 clients
sfn = boto3.client('stepfunctions')


@metrics.log_metrics(capture_cold_start_metric=True)  # type: ignore
@logger.inject_lambda_context(log_event=True)  # type: ignore
@tracer.capture_method
def lambda_handler(event, context):
    """Functions processes DynamoDB Stream to detect changes in the contract status
    and syncs AWS Step Function task token based on the existence of contract service and
    it's status.

    Parameters
    ----------
    event: dict, required
        DynamoDB stream

    context: object
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
        The same input event file
    """

    for record in event["Records"]:
        # Deserialize new image in record
        new_image = ddb_deserialize(record["dynamodb"]["NewImage"])

        # Deserialize old image in record, default to empty dict if it doesn't exist
        old_image = ddb_deserialize(record["dynamodb"].get("OldImage", {}))

        # Merge old image with new image
        property_contract_status = {**old_image, **new_image}

        # If we have both tokens, check what the property status is. If it's 
        if "sfn_wait_approved_task_token" not in property_contract_status:
            return

        if property_contract_status["contract_status"] != "APPROVED":
            logger.info({"Contract status for property is not APPROVED":
                property_contract_status["property_id"]})
            return

        logger.info({"Contract status for property is APPROVED":
            property_contract_status["property_id"]})

        result = task_successful(property_contract_status["sfn_wait_approved_task_token"], property_contract_status)
        return result



def task_successful(task_token: str, contract_status: dict):
    """Send the token for a specified contract status back to Step Functions to continue workflow execution.

    Parameters
    ----------
    task_token : str
        State machine task token

    contract_status : dict
        Contract Status object to return to statemachine.
    """
    output = {'Payload': contract_status}
    return sfn.send_task_success(taskToken=task_token, output=json.dumps(output))


def ddb_deserialize(dynamo_image: dict) -> dict:
    """Converts the DynamoDB stream object to json dict

    Parameters
    ----------
    dynamo_image : dict
        DynamoDB image

    Returns
    -------
    dict

    """
    if dynamo_image is None:
        return {}

    deserializer = TypeDeserializer()
    return {
        k: deserializer.deserialize(v)
        for k, v in dynamo_image.items()
    }
    