# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
# import json
from importlib import reload

# import pytest
from unittest import mock
# from botocore.exceptions import ClientError

from .event_generator import sqs_event
from .helper import TABLE_NAME
from .helper import load_event, return_env_vars_dict
from .helper import create_ddb_table_property_web, create_test_eventbridge_bus, create_test_sqs_ingestion_queue
from .helper import prop_id_to_pk_sk

@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_event(dynamodb, eventbridge, sqs, lambda_context):
    payload = load_event('request_approval_event')
    event = sqs_event([{'body': payload, 'attributes': {'HttpMethod': 'POST'}}])

    # Loading function here so that mocking works correctly.
    from approvals_service import request_approval_function
    # Reload is required to prevent function setup reuse from another test 
    reload(request_approval_function)

    create_ddb_table_property_web(dynamodb)
    create_test_eventbridge_bus(eventbridge)
    create_test_sqs_ingestion_queue(sqs)

    request_approval_function.lambda_handler(event, lambda_context)

    # 'PK': 'PROPERTY#usa#anytown',
    # 'SK': 'main-street#123',
    # usa/anytown/main-street/123

    prop_id = prop_id_to_pk_sk(payload['property_id'])
    res = dynamodb.Table(TABLE_NAME).get_item(Key=prop_id)

    assert res['Item']['PK']            == prop_id['PK']
    assert res['Item']['SK']            == prop_id['SK']

    assert res['Item']['city']          == 'Anytown'
    assert res['Item']['contract']      == 'sale'
    assert res['Item']['country']       == 'USA'
    assert res['Item']['description']   == 'Test Description'
    assert res['Item']['listprice']     == '200'
    assert res['Item']['number']        == '123'
    assert res['Item']['status']        == 'PENDING'
    assert res['Item']['street']        == 'Main Street'



# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_broken_input_event(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/request_approval_bad_input.json')

#     # Loading function here so that mocking works correctly.
#     import approvals_service.request_approval_function as app

#     # Reload is required to prevent function setup reuse from another test
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 400
#     assert 'message' in data.keys()
#     assert 'unable' in data['message'].lower()


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_invalid_property_id(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/request_invalid_property_id.json')

#     # Loading function here so that mocking works correctly.
#     import approvals_service.request_approval_function as app

#     # Reload is required to prevent function setup reuse from another test
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 400
#     assert 'message' in data.keys()
#     assert 'invalid' in data['message'].lower()


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_already_approved(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/request_already_approved.json')

#     # Loading function here so that mocking works correctly.
#     import approvals_service.request_approval_function as app

#     # Reload is required to prevent function setup reuse from another test
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 200
#     assert 'result' in data.keys()
#     assert 'already' in data['result'].lower()


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_property_does_not_exist(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/request_non_existent_property.json')

#     # Loading function here so that mocking works correctly.
#     import approvals_service.request_approval_function as app

#     # Reload is required to prevent function setup reuse from another test
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 404
#     assert 'message' in data.keys()
#     assert 'no property found' in data['message'].lower()
