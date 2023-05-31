# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import json
from datetime import datetime

import boto3
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging import Logger

from contracts_service.exceptions import EventValidationException, EventValidationException

# Initialise Environment variables
if (SERVICE_NAMESPACE := os.environ.get("SERVICE_NAMESPACE")) is None:
    raise EnvironmentError("SERVICE_NAMESPACE environment variable is undefined")

if (EVENT_BUS := os.environ.get("EVENT_BUS")) is None:
    raise EnvironmentError("EVENT_BUS environment variable is undefined")

# Initialise PowerTools
logger: Logger = Logger(service="helperFunc")
tracer: Tracer = Tracer(service="helperFunc")

# Initialise boto3 clients
event_bridge = boto3.client('events')

request_dates = {}

@tracer.capture_method
def get_stable_date(id=None):
    """Return current date for this invocation. The return value remains consistent
    across multiple requests for the same id. 

    Parameters
    ----------
    id : str
        identifier of the local context, e.g. context.aws_request_id

    Returns
    -------
    str
        Current date time in iso format, e.g. '2023-02-10T10:04:14Z'
    """
    if not (id in request_dates.keys()):
        now_str = datetime.now().isoformat()
        print(f"Time recorded: {now_str} for request {id}")
        request_dates[id] = now_str        

    return request_dates[id]
    

@tracer.capture_method
def get_event_body(event):
    """Get body of the API Gateway event

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
    event_body = event.get("body", '{}')

    try:
        event_json = json.loads(event_body)
    except json.decoder.JSONDecodeError as e:
        logger.fatal("This event input is not a valid JSON")
        raise e
    except TypeError as e:
        logger.fatal("This event input is not a valid JSON")
        raise e

    # Check if event body contains data, otherwise log & raise exception
    if not event_json:
        msg = "This event input did not contain body payload."
        logger.fatal(msg)
        raise EventValidationException(msg)

    return event_json


@tracer.capture_method
def publish_event(contract, request_id):
    """Push contract event data to EventBridge bus

    Parameters
    ----------
    contract : dict
        Contract object

    Returns
    -------
    Amazon EventBridge PutEvents response : dict
        response object from EventBridge API call
    """
    
    contract_status_changed_event = {
        "contract_last_modified_on": contract["contract_last_modified_on"],
        "property_id": contract["property_id"],
        "contract_id": contract["contract_id"],
        "contract_status": contract["contract_status"],
    }

    return event_bridge.put_events(
            Entries=[
                {
                    'Time': get_stable_date(request_id),
                    "Source": SERVICE_NAMESPACE,
                    "DetailType": "ContractStatusChanged",
                    "Detail": json.dumps(contract_status_changed_event),
                    "EventBusName": EVENT_BUS
                }
            ]
        )
