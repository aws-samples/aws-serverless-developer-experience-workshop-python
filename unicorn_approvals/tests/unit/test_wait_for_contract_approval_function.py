# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from importlib import reload

import pytest
from unittest import mock
from botocore.exceptions import ClientError

from .helper import load_event, return_env_vars_dict, create_ddb_table_contracts_with_entry, create_ddb_table_properties


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_handle_wait_for_contract_approval_function(dynamodb, lambda_context):
    stepfunctions_event = load_event("lambda/wait_for_contract_approval_function")

    from approvals_service import wait_for_contract_approval_function

    reload(wait_for_contract_approval_function)

    create_ddb_table_contracts_with_entry(dynamodb)

    ddbitem_before = dynamodb.Table("table1").get_item(Key={"property_id": stepfunctions_event["Input"]["property_id"]})
    assert "sfn_wait_approved_task_token" not in ddbitem_before["Item"]

    ret = wait_for_contract_approval_function.lambda_handler(stepfunctions_event, lambda_context)
    ddbitem_after = dynamodb.Table("table1").get_item(Key={"property_id": stepfunctions_event["Input"]["property_id"]})

    assert ret["property_id"] == stepfunctions_event["Input"]["property_id"]
    assert ddbitem_after["Item"]["sfn_wait_approved_task_token"] == stepfunctions_event["TaskToken"]


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_contract_not_found(dynamodb, lambda_context):
    stepfunctions_event = {
        "TaskToken": "xxx",
        "Input": {
            "property_id": "usa/anytown/main-street/999",
        },
    }

    from approvals_service import wait_for_contract_approval_function
    from approvals_service.exceptions import ContractStatusNotFoundException

    reload(wait_for_contract_approval_function)

    # Create empty table (no entry for the requested property_id)
    create_ddb_table_properties(dynamodb)

    with pytest.raises(ContractStatusNotFoundException):
        wait_for_contract_approval_function.lambda_handler(stepfunctions_event, lambda_context)


@mock.patch.dict(os.environ, return_env_vars_dict({"CONTRACT_STATUS_TABLE": "nonexistent_table"}), clear=True)
def test_dynamodb_failure(dynamodb, lambda_context):
    stepfunctions_event = load_event("lambda/wait_for_contract_approval_function")

    from approvals_service import wait_for_contract_approval_function
    from approvals_service.exceptions import ContractStatusNotFoundException

    reload(wait_for_contract_approval_function)

    # Do NOT create the table so DynamoDB raises a ResourceNotFoundException
    # The handler catches ClientError and raises ContractStatusNotFoundException
    with pytest.raises((ClientError, ContractStatusNotFoundException)):
        wait_for_contract_approval_function.lambda_handler(stepfunctions_event, lambda_context)
