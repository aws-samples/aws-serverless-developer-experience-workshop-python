# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from importlib import reload

from unittest import mock

from .lambda_context import LambdaContext
from .helper import load_event, return_env_vars_dict, create_ddb_table_contracts_with_entry


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_handle_wait_for_contract_approval_function(dynamodb, mocker):
    stepfunctions_event = load_event('tests/events/lambda/wait_for_contract_approval_function.json')

    from properties_service import wait_for_contract_approval_function
    reload(wait_for_contract_approval_function)

    create_ddb_table_contracts_with_entry(dynamodb)

    ddbitem_before = dynamodb.Table('table1').get_item(Key={'property_id': stepfunctions_event['Input']['property_id']})
    assert 'sfn_wait_approved_task_token' not in ddbitem_before['Item']

    ret = wait_for_contract_approval_function.lambda_handler(stepfunctions_event, LambdaContext())
    ddbitem_after = dynamodb.Table('table1').get_item(Key={'property_id': stepfunctions_event['Input']['property_id']})

    assert ret['property_id'] == stepfunctions_event['Input']['property_id']    
    assert ddbitem_after['Item']['sfn_wait_approved_task_token'] == stepfunctions_event['TaskToken']
