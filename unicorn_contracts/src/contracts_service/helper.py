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
def get_current_date(request_id=None):
    """Return current date for this invocation. To keep the return value consistent while function is 
    queried multiple times, function maintains the value returned for each request id and returns same 
    value on subsequent requests.

    Parameters
    ----------
    request_id : str
        context.aws_request_id

    Returns
    -------
    str
        Current date time i.e. '01/08/2022 20:36:30'
    """
    if request_id is not None and request_id in request_dates.keys():
        return request_dates[request_id]
        
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    logger.info(f"Time recorded: {now_str} for request {request_id}")
    request_dates[request_id] = now_str
    return now_str
    

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
        logger.critical("This event input is not a valid JSON")
        raise e
    except TypeError as e:
        logger.critical("This event input is not a valid JSON")
        raise e

    # Check if event body contains data, otherwise log & raise exception
    if not event_json:
        msg = "This event input did not contain body payload."
        logger.critical(msg)
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
                    'Time': get_current_date(request_id),
                    "Source": SERVICE_NAMESPACE,
                    "DetailType": "ContractStatusChanged",
                    "Detail": json.dumps(contract_status_changed_event),
                    "EventBusName": EVENT_BUS
                }
            ]
        )
