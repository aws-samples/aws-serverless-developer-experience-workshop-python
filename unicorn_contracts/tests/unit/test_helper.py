# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json
from importlib import reload

import pytest
from unittest import mock
# from moto import mock_dynamodb, mock_events

# from contracts_service.exceptions import EventValidationException

from .helper import return_env_vars_dict, create_test_eventbridge_bus
from .lambda_context import LambdaContext


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_push_event(dynamodb, eventbridge, mocker):
    context = LambdaContext()

    contract = {
            "created_date": "current_date",
            "contract_last_modified_on": "last_modified_date",
            "address": "1",
            "property_id": "1",
            "contract_id": "1",
            "contract_status": "New",
        }
    
    # detail_type = "Contract created"

    from contracts_service import helper
    reload(helper)

    create_test_eventbridge_bus(eventbridge)

    ret = helper.publish_event(contract, context.aws_request_id)
    assert ret['FailedEntryCount'] == 0
    assert len(ret['Entries']) == 1
    for e in ret['Entries']:
        assert "EventId" in e
        assert "ErrorCode" not in e
        assert "ErrorMessage" not in e


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_get_event_body(dynamodb, eventbridge, mocker):

    event = {
        "body": "{\"add\": \"St.1 , Building 10\", \"sell\": \"John Smith\", \"prop\": \"4781231c-bc30-4f30-8b30-7145f4dd1adb\"}"
    }

    from contracts_service import helper
    reload(helper)

    ret = helper.get_event_body(event)
    assert type(ret) == dict


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_get_event_body_bad_json(dynamodb, eventbridge, mocker):

    event = {
        "body": "{\"add\": \"St.1 , Building 10\", \"sell\": \"John Smith\", \"prop\" \"4781231c-bc30-4f30-8b30-7145f4dd1adb\"}"
    }

    from contracts_service import create_contract_function
    reload(create_contract_function)

    with pytest.raises(json.decoder.JSONDecodeError):
        ret = create_contract_function.get_event_body(event)


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_get_event_body_bad_type(dynamodb, eventbridge, mocker):

    event = {
        "body": 1
    }

    from contracts_service import create_contract_function
    reload(create_contract_function)

    with pytest.raises(TypeError):
        ret = create_contract_function.get_event_body(event)
