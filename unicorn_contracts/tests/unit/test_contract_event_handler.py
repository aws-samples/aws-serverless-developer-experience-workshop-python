# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import re
from datetime import datetime, timedelta, timezone
from importlib import reload

import pytest
from unittest import mock

from .event_generator import sqs_event
from .helper import TABLE_NAME
from .helper import load_event, return_env_vars_dict
from .helper import create_ddb_table_contracts, create_test_sqs_ingestion_queue, create_ddb_table_contracts_with_entry

# yyyy-MM-ddTHH:mm:ssZ: UTC, whole seconds, literal Z (20 characters)
TIMESTAMP_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


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

    # Both timestamps are in the stored format, and a new contract has one creation instant
    assert re.fullmatch(TIMESTAMP_PATTERN, res["Item"]["contract_created"])
    assert re.fullmatch(TIMESTAMP_PATTERN, res["Item"]["contract_last_modified_on"])
    assert res["Item"]["contract_created"] == res["Item"]["contract_last_modified_on"]


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

    # The update writes a new last-modified value in the stored format
    assert re.fullmatch(TIMESTAMP_PATTERN, res["Item"]["contract_last_modified_on"])
    assert res["Item"]["contract_last_modified_on"] != "2022-08-01T20:36:30Z"


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
            "contract_created": "2022-08-01T20:36:30Z",
            "contract_last_modified_on": "2022-08-01T20:36:30Z",
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


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_format_timestamp_truncates_the_fraction():
    from contracts_service import contract_event_handler

    reload(contract_event_handler)

    instant = datetime(2026, 11, 21, 2, 42, 30, 987654, tzinfo=timezone.utc)
    assert contract_event_handler.format_timestamp(instant) == "2026-11-21T02:42:30Z"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_format_timestamp_keeps_the_same_width_when_the_fraction_is_zero():
    from contracts_service import contract_event_handler

    reload(contract_event_handler)

    instant = datetime(2026, 11, 21, 2, 42, 30, 0, tzinfo=timezone.utc)
    assert contract_event_handler.format_timestamp(instant) == "2026-11-21T02:42:30Z"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_format_timestamp_converts_a_non_utc_instant_to_utc():
    from contracts_service import contract_event_handler

    reload(contract_event_handler)

    sydney = timezone(timedelta(hours=11))
    instant = datetime(2026, 11, 21, 13, 42, 30, tzinfo=sydney)
    assert contract_event_handler.format_timestamp(instant) == "2026-11-21T02:42:30Z"
