# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from importlib import reload

import pytest
from unittest import mock

from .lambda_context import LambdaContext
from .helper import load_event, return_env_vars_dict, create_ddb_table_contracts_with_entry


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_existing_contract_exists_checker_function(dynamodb, mocker):
    stepfunctions_event = load_event('tests/events/lambda/contract_status_checker.json')

    from properties_service import contract_exists_checker_function
    reload(contract_exists_checker_function)

    create_ddb_table_contracts_with_entry(dynamodb)

    ret = contract_exists_checker_function.lambda_handler(stepfunctions_event, LambdaContext())

    assert ret['property_id'] == stepfunctions_event['Input']['property_id']
    assert ret['address']['country'] == stepfunctions_event['Input']['country']


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_contract_exists_checker_function(dynamodb, mocker):
    stepfunctions_event = load_event('tests/events/lambda/contract_status_checker.json')
    stepfunctions_event['Input']['property_id'] = 'NOT/a/valid/CONTRACT'

    from properties_service import contract_exists_checker_function
    from properties_service.exceptions import ContractStatusNotFoundException
    reload(contract_exists_checker_function)

    create_ddb_table_contracts_with_entry(dynamodb)

    with pytest.raises(ContractStatusNotFoundException) as errinfo:
        contract_exists_checker_function.lambda_handler(stepfunctions_event, LambdaContext())

    assert errinfo.value.message == 'No contract found for specified Property ID'
