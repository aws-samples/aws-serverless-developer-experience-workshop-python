# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from importlib import reload

import pytest
from unittest import mock
from botocore.exceptions import ClientError

from .event_generator import sqs_event
from .helper import TABLE_NAME
from .helper import load_event, return_env_vars_dict
from .helper import create_ddb_table_contracts, create_test_sqs_ingestion_queue, create_ddb_table_contracts_with_entry


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

    assert res['Item']['property_id']           == payload['property_id']
    assert res['Item']['contract_status']       == 'DRAFT'

    assert res['Item']['seller_name']           == payload['seller_name']
    assert res['Item']['address']['country']    == payload['address']['country']
    assert res['Item']['address']['city']       == payload['address']['city']
    assert res['Item']['address']['street']     == payload['address']['street']
    assert res['Item']['address']['number']     == payload['address']['number']


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_update_event(dynamodb, sqs, lambda_context):
    payload = load_event('update_contract_valid_1')
    event = sqs_event([{'body': payload, 'attributes': {'HttpMethod': 'PUT'}}])

    # Loading function here so that mocking works correctly.
    from contracts_service import contract_event_handler  # noqa: F401
    # Reload is required to prevent function setup reuse from another test 
    reload(contract_event_handler)

    create_ddb_table_contracts_with_entry(dynamodb)
    create_test_sqs_ingestion_queue(sqs)

    contract_event_handler.lambda_handler(event, lambda_context)

    res = dynamodb.Table(TABLE_NAME).get_item(Key={'property_id': payload['property_id']})

    assert res['Item']['property_id']           == payload['property_id']
    assert res['Item']['contract_status']       == 'APPROVED'


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
