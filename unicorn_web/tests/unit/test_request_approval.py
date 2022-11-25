# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json

from unittest import mock
from importlib import reload

from .lambda_context import LambdaContext
from .helper import load_event, return_env_vars_dict, create_ddb_table_property_web


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_event(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/request_approval_event.json')

    # Loading function here so that mocking works correctly.
    import approvals_service.request_approval as app

    # Reload is required to prevent function setup reuse from another test 
    reload(app)

    create_ddb_table_property_web(dynamodb)

    context = LambdaContext()
    ret = app.lambda_handler(apigw_event, context)  # type: ignore
    data = json.loads(ret['body'])

    assert ret['statusCode'] == 200
    assert 'result' in data.keys()
    assert 'Approval Requested' in data['result']

@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_broken_input_event(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/request_approval_bad_input.json')

    # Loading function here so that mocking works correctly.
    import approvals_service.request_approval as app

    # Reload is required to prevent function setup reuse from another test
    reload(app)

    create_ddb_table_property_web(dynamodb)

    context = LambdaContext()
    ret = app.lambda_handler(apigw_event, context)  # type: ignore
    data = json.loads(ret['body'])

    assert ret['statusCode'] == 400
    assert 'message' in data.keys()
    assert 'unable' in data['message'].lower()

@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_invalid_property_id(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/request_invalid_property_id.json')

    # Loading function here so that mocking works correctly.
    import approvals_service.request_approval as app

    # Reload is required to prevent function setup reuse from another test
    reload(app)

    create_ddb_table_property_web(dynamodb)

    context = LambdaContext()
    ret = app.lambda_handler(apigw_event, context)  # type: ignore
    data = json.loads(ret['body'])

    assert ret['statusCode'] == 400
    assert 'message' in data.keys()
    assert 'invalid' in data['message'].lower()

@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_already_approved(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/request_already_approved.json')

    # Loading function here so that mocking works correctly.
    import approvals_service.request_approval as app

    # Reload is required to prevent function setup reuse from another test
    reload(app)

    create_ddb_table_property_web(dynamodb)

    context = LambdaContext()
    ret = app.lambda_handler(apigw_event, context)  # type: ignore
    data = json.loads(ret['body'])

    assert ret['statusCode'] == 200
    assert 'result' in data.keys()
    assert 'already' in data['result'].lower()

@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_property_does_not_exist(dynamodb, eventbridge, mocker):
    apigw_event = load_event('events/request_non_existent_property.json')

    # Loading function here so that mocking works correctly.
    import approvals_service.request_approval as app

    # Reload is required to prevent function setup reuse from another test
    reload(app)

    create_ddb_table_property_web(dynamodb)

    context = LambdaContext()
    ret = app.lambda_handler(apigw_event, context)  # type: ignore
    data = json.loads(ret['body'])

    assert ret['statusCode'] == 404
    assert 'message' in data.keys()
    assert 'no property found' in data['message'].lower()
