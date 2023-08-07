# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
# import json
from importlib import reload

# import pytest
from unittest import mock
from moto import mock_stepfunctions

# from aws_lambda_powertools.event_handler.exceptions import InternalServerError
# from botocore.exceptions import ClientError

from .lambda_context import LambdaContext
from .helper import load_event, return_env_vars_dict, create_ddb_table_contracts_with_entry


@mock_stepfunctions
@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_handle_contract_exists_checker_function(dynamodb, mocker):
    stepfunctions_event = load_event('tests/events/lambda/contract_exists_checker.json')

    from properties_service import contract_exists_checker_function
    reload(contract_exists_checker_function)

    create_ddb_table_contracts_with_entry(dynamodb)

    ret = contract_exists_checker_function.lambda_handler(stepfunctions_event, LambdaContext())

    assert ret['property_id'] == stepfunctions_event['Input']['property_id']
    assert ret['address']['country'] == stepfunctions_event['Input']['country']
