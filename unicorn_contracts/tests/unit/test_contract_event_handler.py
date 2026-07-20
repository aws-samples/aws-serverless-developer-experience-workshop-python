# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from importlib import reload

import pytest
from unittest import mock

from .event_generator import sqs_event
from .helper import TABLE_NAME
from .helper import load_event, return_env_vars_dict
from .helper import create_ddb_table_contracts, create_test_sqs_ingestion_queue, create_ddb_table_contracts_with_entry


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_create_event(dynamodb, sqs, lambda_context):
    payload = load_event("create_contract_valid_1")
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "POST"}}])

    # Loading function here so that mocking works correctly.
    from contracts_service import contract_event_handler  # noqa: F401

    # Reload is required to prevent function setup reuse from another test
    reload(contract_event_handler)

    create_ddb_table_contracts(dynamodb)
    create_test_sqs_ingestion_queue(sqs)

    contract_event_handler.lambda_handler(event, lambda_context)

    res = dynamodb.Table(TABLE_NAME).get_item(Key={"property_id": payload["property_id"]})

    assert res["Item"]["property_id"] == payload["property_id"]
    assert res["Item"]["contract_status"] == "DRAFT"

    assert res["Item"]["seller_name"] == payload["seller_name"]
    assert res["Item"]["address"]["country"] == payload["address"]["country"]
    assert res["Item"]["address"]["city"] == payload["address"]["city"]
    assert res["Item"]["address"]["street"] == payload["address"]["street"]
    assert res["Item"]["address"]["number"] == payload["address"]["number"]


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_update_event(dynamodb, sqs, lambda_context):
    payload = load_event("update_contract_valid_1")
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "PUT"}}])

    # Loading function here so that mocking works correctly.
    from contracts_service import contract_event_handler  # noqa: F401

    # Reload is required to prevent function setup reuse from another test
    reload(contract_event_handler)

    create_ddb_table_contracts_with_entry(dynamodb)
    create_test_sqs_ingestion_queue(sqs)

    contract_event_handler.lambda_handler(event, lambda_context)

    res = dynamodb.Table(TABLE_NAME).get_item(Key={"property_id": payload["property_id"]})

    assert res["Item"]["property_id"] == payload["property_id"]
    assert res["Item"]["contract_status"] == "APPROVED"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_create_contract_already_exists(dynamodb, sqs, lambda_context):
    payload = load_event("create_contract_valid_1")
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "POST"}}])

    from contracts_service import contract_event_handler  # noqa: F401

    reload(contract_event_handler)

    create_ddb_table_contracts_with_entry(dynamodb)
    create_test_sqs_ingestion_queue(sqs)

    # Contract for property_id "usa/anytown/main-street/111" already exists in DRAFT status;
    # ConditionalCheckFailedException is caught and logged, not raised.
    contract_event_handler.lambda_handler(event, lambda_context)

    res = dynamodb.Table(TABLE_NAME).get_item(Key={"property_id": payload["property_id"]})
    # The original contract should remain unchanged (still DRAFT, same contract_id)
    assert res["Item"]["contract_status"] == "DRAFT"
    assert res["Item"]["contract_id"] == "11111111"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_update_contract_not_in_draft(dynamodb, sqs, lambda_context):
    payload = load_event("update_contract_valid_1")
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "PUT"}}])

    from contracts_service import contract_event_handler  # noqa: F401

    reload(contract_event_handler)

    # Create table with an entry already in APPROVED status
    table = create_ddb_table_contracts(dynamodb)
    create_test_sqs_ingestion_queue(sqs)
    table.put_item(
        Item={
            "property_id": "usa/anytown/main-street/111",
            "contract_created": "01/08/2022 20:36:30",
            "contract_last_modified_on": "01/08/2022 20:36:30",
            "contract_id": "11111111",
            "address": {"country": "USA", "city": "Anytown", "street": "Main Street", "number": 111},
            "seller_name": "John Doe",
            "contract_status": "APPROVED",
        }
    )

    # ConditionalCheckFailedException is caught and logged, not raised.
    contract_event_handler.lambda_handler(event, lambda_context)

    res = dynamodb.Table(TABLE_NAME).get_item(Key={"property_id": payload["property_id"]})
    # Status should remain APPROVED (update was rejected)
    assert res["Item"]["contract_status"] == "APPROVED"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_invalid_http_method(dynamodb, sqs, lambda_context):
    payload = load_event("create_contract_valid_1")
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "DELETE"}}])

    from contracts_service import contract_event_handler  # noqa: F401

    reload(contract_event_handler)

    create_ddb_table_contracts(dynamodb)
    create_test_sqs_ingestion_queue(sqs)

    with pytest.raises(Exception, match="Unable to handle HttpMethod DELETE"):
        contract_event_handler.lambda_handler(event, lambda_context)


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_malformed_sqs_body(dynamodb, sqs, lambda_context):
    event = sqs_event([{"body": "not a valid dict", "attributes": {"HttpMethod": "POST"}}])

    from contracts_service import contract_event_handler  # noqa: F401

    reload(contract_event_handler)

    create_ddb_table_contracts(dynamodb)
    create_test_sqs_ingestion_queue(sqs)

    with pytest.raises((KeyError, TypeError)):
        contract_event_handler.lambda_handler(event, lambda_context)
