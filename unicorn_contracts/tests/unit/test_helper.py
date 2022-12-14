import json
import os
import pytest
from unittest import mock
from importlib import reload
from moto import mock_dynamodb, mock_events

from .helper import return_env_vars_dict
from .lambda_context import LambdaContext
from contracts_service.exceptions import EventValidationException


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

    from contracts_service import create_contract
    reload(create_contract)

    with pytest.raises(json.decoder.JSONDecodeError):
        ret = create_contract.get_event_body(event)


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_get_event_body_bad_type(dynamodb, eventbridge, mocker):

    event = {
        "body": 1
    }

    from contracts_service import create_contract
    reload(create_contract)

    with pytest.raises(TypeError):
        ret = create_contract.get_event_body(event)
