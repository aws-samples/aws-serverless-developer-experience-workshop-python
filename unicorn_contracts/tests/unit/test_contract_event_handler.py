# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from importlib import reload

import pytest
from unittest import mock, TestCase
from botocore.exceptions import ClientError

from .events import sqs_event
from .helper import load_event, return_env_vars_dict, create_ddb_table_contracts, create_test_sqs_ingestion_queue
from .helper import TABLE_NAME


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_create_event(dynamodb, sqs, lambda_context):
    payload = load_event('create_contract_valid_1')
    event = sqs_event([{'body': payload, 'attributes': {'HttpMethod': 'POST'}}])
    
    # Loading function here so that mocking works correctly.
    from contracts_service import contract_event_handler  # noqa: F401
    # Reload is required to prevent function setup reuse from another test 
    reload(contract_event_handler)

    create_ddb_table_contracts(dynamodb)
    create_test_sqs_ingestion_queue(sqs)

    contract_event_handler.lambda_handler(event, lambda_context)

    res = dynamodb.Table(TABLE_NAME).get_item(Key={'property_id': payload['property_id']})

    TestCase().assertDictEqual(res, res | {"Item": payload})


    # Read value in DDB
    # data = json.loads(ret["body"])

    # assert ret["statusCode"] == 200
    # assert "property_id" in data.keys()
    # assert "contract_status" in data.keys()


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_missing_body_event(dynamodb, eventbridge, mocker, lambda_context):
#     event = load_event('events/create_missing_body_event.json')
    
#     from contracts_service import contract_event_handler  # noqa: F401
#     reload(contract_event_handler)
    
#     create_ddb_table_contracts(dynamodb)

#     contract_event_handler.lambda_handler(event, lambda_context)

#     # Read value in DDB
#     # data = json.loads(ret["body"])

#     # assert ret["statusCode"] == 200
#     # assert "property_id" in data.keys()
#     # assert "contract_status" in data.keys()


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_empty_dict_body_event(dynamodb, eventbridge, mocker, lambda_context):
#     apigw_event = load_event('events/create_empty_dict_body_event.json')
#     from contracts_service import contract_event_handler  # noqa: F401
#     reload(create_contract_function)
#     create_ddb_table_contracts(dynamodb)

#     ret = create_contract_function.lambda_handler(apigw_event, lambda_context)
#     data = json.loads(ret["body"])

#     assert ret["statusCode"] == 400
#     assert "message" in ret["body"]
#     assert data["message"] == "Event body not valid."


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_wrong_event_data(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/create_wrong_event.json')
#     from contracts_service import contract_event_handler  # noqa: F401
#     reload(create_contract_function)
#     create_ddb_table_contracts(dynamodb)

#     context = LambdaContext()

#     ret = create_contract_function.lambda_handler(apigw_event, context)
#     data = json.loads(ret["body"])

#     assert ret["statusCode"] == 400
#     assert "message" in ret["body"]
#     assert data["message"] == "Event body not valid."


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_ddb_env_var():
    del os.environ['DYNAMODB_TABLE']
    # Loading function here so that mocking works correctly
    with pytest.raises(EnvironmentError):
        from contracts_service import contract_event_handler
        reload(contract_event_handler)


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_sm_env_var():
    del os.environ['SERVICE_NAMESPACE']

    with pytest.raises(EnvironmentError):
        from contracts_service import contract_event_handler
        reload(contract_event_handler)


@mock.patch.dict(os.environ, return_env_vars_dict({"DYNAMODB_TABLE": "table27"}), clear=True)
def test_wrong_dynamodb_table(dynamodb, lambda_context):
    event = sqs_event([{'body': load_event('create_contract_valid_1'), 'attributes': {'HttpMethod': 'POST'}}])

    from contracts_service import contract_event_handler  # noqa: F401
    
    create_ddb_table_contracts(dynamodb)

    with pytest.raises(ClientError):
        reload(contract_event_handler)
        contract_event_handler.lambda_handler(event, lambda_context)
