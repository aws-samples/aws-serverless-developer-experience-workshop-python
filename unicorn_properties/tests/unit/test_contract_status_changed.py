# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# import json
import os
# import pytest
from unittest import mock
from importlib import reload
from moto import mock_dynamodb, mock_events

# from aws_lambda_powertools.event_handler.exceptions import InternalServerError
# from botocore.exceptions import ClientError

from .lambda_context import LambdaContext
from .helper import load_event, return_env_vars_dict, create_ddb_table_properties


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_handle_contract_status_changed_event(dynamodb, mocker):
    eventbridge_event = load_event('tests/events/lambda/contract_status_changed.json')

    from properties_service import contract_status_changed
    create_ddb_table_properties(dynamodb)

    context = LambdaContext()
    ret = contract_status_changed.lambda_handler(eventbridge_event, context)

    assert ret["statusCode"] == 200
