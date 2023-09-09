# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from importlib import reload

import pytest
from unittest import mock
from botocore.exceptions import ClientError

from .lambda_context import LambdaContext
from .helper import load_event, return_env_vars_dict, create_ddb_table_properties


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_contract_status_changed_event_handler(dynamodb, mocker):
    eventbridge_event = load_event('tests/events/lambda/contract_status_changed.json')

    from properties_service import contract_status_changed_event_handler
    # Reload is required to prevent function setup reuse from another test 
    reload(contract_status_changed_event_handler)

    create_ddb_table_properties(dynamodb)

    ret = contract_status_changed_event_handler.lambda_handler(eventbridge_event, LambdaContext())

    assert ret["statusCode"] == 200


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_property_id(dynamodb, mocker):
    eventbridge_event = {'detail': {}}

    from properties_service import contract_status_changed_event_handler
    # Reload is required to prevent function setup reuse from another test 
    reload(contract_status_changed_event_handler)

    create_ddb_table_properties(dynamodb)

    with pytest.raises(ClientError) as e:
        contract_status_changed_event_handler.lambda_handler(eventbridge_event, LambdaContext())

    assert 'ValidationException' in str(e.value)
