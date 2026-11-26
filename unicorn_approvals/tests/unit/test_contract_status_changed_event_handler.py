# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from importlib import reload

import pytest
from unittest import mock
from botocore.exceptions import ClientError

from .helper import TABLE_NAME, load_event, return_env_vars_dict, create_ddb_table_properties


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_contract_status_changed_event_handler(dynamodb, lambda_context):
    eventbridge_event = load_event("eventbridge/contract_status_changed")

    from approvals_service import contract_status_changed_event_handler

    # Reload is required to prevent function setup reuse from another test
    reload(contract_status_changed_event_handler)

    create_ddb_table_properties(dynamodb)

    ret = contract_status_changed_event_handler.lambda_handler(eventbridge_event, lambda_context)

    assert ret["statusCode"] == 200

    # The timestamp is stored exactly as it arrived on the event
    item = dynamodb.Table(TABLE_NAME).get_item(Key={"property_id": "usa/anytown/main-street/123"})["Item"]
    assert item["contract_last_modified_on"] == eventbridge_event["detail"]["contract_last_modified_on"]
    assert item["contract_last_modified_on"] == "2022-08-10T19:56:30Z"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_contract_status_changed_with_datetime_binding(dynamodb, lambda_context):
    # Bindings generated from the schema registry type the field as datetime (format: date-time)
    eventbridge_event = load_event("eventbridge/contract_status_changed")
    eventbridge_event["time"] = "2026-11-25T14:50:49Z"
    eventbridge_event["detail"] = {
        "contract_id": "26c280b0-59e1-4a24-a9b2-744e6b4afeab",
        "property_id": "usa/anytown/main-street/1111",
        "contract_status": "DRAFT",
        "contract_last_modified_on": "2026-11-25T14:50:48Z",
    }

    from approvals_service import contract_status_changed_event_handler
    from schema.unicorn_contracts.contractstatuschanged import ContractStatusChanged

    reload(contract_status_changed_event_handler)

    create_ddb_table_properties(dynamodb)

    types = {**ContractStatusChanged._types, "contract_last_modified_on": "datetime"}
    with mock.patch.object(ContractStatusChanged, "_types", types):
        ret = contract_status_changed_event_handler.lambda_handler(eventbridge_event, lambda_context)

    assert ret["statusCode"] == 200

    item = dynamodb.Table(TABLE_NAME).get_item(Key={"property_id": "usa/anytown/main-street/1111"})["Item"]
    assert item["contract_last_modified_on"] == "2026-11-25T14:50:48Z"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_property_id(dynamodb, lambda_context):
    eventbridge_event = {"detail": {}}

    from approvals_service import contract_status_changed_event_handler

    # Reload is required to prevent function setup reuse from another test
    reload(contract_status_changed_event_handler)

    create_ddb_table_properties(dynamodb)

    with pytest.raises(ClientError) as e:
        contract_status_changed_event_handler.lambda_handler(eventbridge_event, lambda_context)

    assert "ValidationException" in str(e.value)


@mock.patch.dict(os.environ, return_env_vars_dict({"CONTRACT_STATUS_TABLE": "nonexistent_table"}), clear=True)
def test_dynamodb_failure(dynamodb, lambda_context):
    eventbridge_event = load_event("eventbridge/contract_status_changed")

    from approvals_service import contract_status_changed_event_handler

    # Reload is required to prevent function setup reuse from another test
    reload(contract_status_changed_event_handler)

    # Do NOT create the table so DynamoDB raises a ResourceNotFoundException
    with pytest.raises(ClientError) as e:
        contract_status_changed_event_handler.lambda_handler(eventbridge_event, lambda_context)

    assert "ResourceNotFoundException" in str(e.value)
