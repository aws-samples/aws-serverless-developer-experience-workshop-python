# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
import pytest
from unittest import mock
from importlib import reload

from botocore.exceptions import ClientError

from .lambda_context import LambdaContext
from .helper import load_event, return_env_vars_dict, create_ddb_table_contracts


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_event(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/create_valid_event.json')

    # Loading function here so that mocking works correctly.
    from contracts_service import create_contract_function

    # Reload is required to prevent function setup reuse from another test 
    reload(create_contract_function)

    create_ddb_table_contracts(dynamodb)

    context = LambdaContext()
    ret = create_contract_function.lambda_handler(apigw_event, context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert "property_id" in data.keys()
    assert "contract_status" in data.keys()


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_body_event(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/create_missing_body_event.json')
    from contracts_service import create_contract_function
    reload(create_contract_function)
    create_ddb_table_contracts(dynamodb)

    context = LambdaContext()
    ret = create_contract_function.lambda_handler(apigw_event, context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 400
    assert "message" in ret["body"]
    assert data["message"] == "Event body not valid."


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_empty_dict_body_event(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/create_empty_dict_body_event.json')
    from contracts_service import create_contract_function
    reload(create_contract_function)
    create_ddb_table_contracts(dynamodb)

    context = LambdaContext()

    ret = create_contract_function.lambda_handler(apigw_event, context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 400
    assert "message" in ret["body"]
    assert data["message"] == "Event body not valid."


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_wrong_event_data(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/create_wrong_event.json')
    from contracts_service import create_contract_function
    reload(create_contract_function)
    create_ddb_table_contracts(dynamodb)

    context = LambdaContext()

    ret = create_contract_function.lambda_handler(apigw_event, context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 400
    assert "message" in ret["body"]
    assert data["message"] == "Event body not valid."


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_ddb_env_var(dynamodb, eventbridge, mocker):
    del os.environ['DYNAMODB_TABLE']
    apigw_event = load_event('events/create_valid_event.json')
    # Loading function here so that mocking works correctly
    from contracts_service import create_contract_function
    with pytest.raises(EnvironmentError):
        reload(create_contract_function)


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_eb_env_var(dynamodb, eventbridge, mocker):
    del os.environ['EVENT_BUS']
    apigw_event = load_event('events/create_valid_event.json')
    # Loading function here so that mocking works correctly
    from contracts_service import helper
    with pytest.raises(EnvironmentError):
        reload(helper)


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_sm_env_var(dynamodb, eventbridge, mocker):
    del os.environ['SERVICE_NAMESPACE']
    apigw_event = load_event('events/create_valid_event.json')
    # Loading function here so that mocking works correctly
    from contracts_service import helper
    with pytest.raises(EnvironmentError):
        reload(helper)


@mock.patch.dict(os.environ, return_env_vars_dict({"DYNAMODB_TABLE": "table27"}), clear=True)
def test_wrong_dynamodb_table(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/create_valid_event.json')
    from contracts_service import create_contract_function
    reload(create_contract_function)
    create_ddb_table_contracts(dynamodb)

    context = LambdaContext()
    with pytest.raises(ClientError):
        ret = create_contract_function.lambda_handler(apigw_event, context)
