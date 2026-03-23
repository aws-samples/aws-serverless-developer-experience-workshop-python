# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import json
from importlib import reload

import pytest
from unittest import mock
from botocore.exceptions import ClientError

from .event_generator import sqs_event
from .helper import TABLE_NAME
from .helper import load_event, return_env_vars_dict
from .helper import create_ddb_table_property_web, create_test_eventbridge_bus, create_test_sqs_ingestion_queue
from .helper import prop_id_to_pk_sk


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_event(dynamodb, eventbridge, sqs, lambda_context):
    payload = load_event("request_approval_event")
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "POST"}}])

    # Loading function here so that mocking works correctly.
    from publication_manager_service import request_approval_function

    # Reload is required to prevent function setup reuse from another test
    reload(request_approval_function)

    create_ddb_table_property_web(dynamodb)
    create_test_eventbridge_bus(eventbridge)
    create_test_sqs_ingestion_queue(sqs)

    request_approval_function.lambda_handler(event, lambda_context)

    # 'PK': 'PROPERTY#usa#anytown',
    # 'SK': 'main-street#123',
    # usa/anytown/main-street/123

    prop_id = prop_id_to_pk_sk(payload["property_id"])
    res = dynamodb.Table(TABLE_NAME).get_item(Key=prop_id)

    assert res["Item"]["PK"] == prop_id["PK"]
    assert res["Item"]["SK"] == prop_id["SK"]

    assert res["Item"]["city"] == "Anytown"
    assert res["Item"]["contract"] == "sale"
    assert res["Item"]["country"] == "USA"
    assert res["Item"]["description"] == "Test Description"
    assert res["Item"]["listprice"] == "200"
    assert res["Item"]["number"] == "123"
    assert res["Item"]["status"] == "PENDING"
    assert res["Item"]["street"] == "Main Street"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_invalid_property_id_format(dynamodb, eventbridge, sqs, lambda_context):
    # Property ID with uppercase letter does not match the regex
    payload = {"property_id": "usa/anytown/Main-street/122"}
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "POST"}}])

    from publication_manager_service import request_approval_function

    reload(request_approval_function)

    create_ddb_table_property_web(dynamodb)
    create_test_eventbridge_bus(eventbridge)
    create_test_sqs_ingestion_queue(sqs)

    # get_keys_for_property returns ("", "") for invalid property_id,
    # then get_property queries DynamoDB with empty PK which raises ClientError (ValidationException)
    with pytest.raises((KeyError, ClientError)):
        request_approval_function.lambda_handler(event, lambda_context)


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_already_approved_skips_eventbridge(dynamodb, eventbridge, sqs, lambda_context):
    # property at main-street/124 has status APPROVED in the test table
    payload = {"property_id": "usa/anytown/main-street/124"}
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "POST"}}])

    from publication_manager_service import request_approval_function

    reload(request_approval_function)

    table = create_ddb_table_property_web(dynamodb)
    create_test_eventbridge_bus(eventbridge)
    create_test_sqs_ingestion_queue(sqs)

    # Update the item to APPROVED status so the function skips
    table.update_item(
        Key={"PK": "PROPERTY#usa#anytown", "SK": "main-street#124"},
        AttributeUpdates={"status": {"Value": "APPROVED", "Action": "PUT"}},
    )

    # Should complete without error and without publishing to EventBridge
    request_approval_function.lambda_handler(event, lambda_context)

    # Verify the status in DDB is still APPROVED (not changed to PENDING)
    res = dynamodb.Table(TABLE_NAME).get_item(
        Key={"PK": "PROPERTY#usa#anytown", "SK": "main-street#124"}
    )
    assert res["Item"]["status"] == "APPROVED"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_property_not_found(dynamodb, eventbridge, sqs, lambda_context):
    # Property usa/anytown/main-street/999 does not exist in the test data
    payload = {"property_id": "usa/anytown/main-street/999"}
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "POST"}}])

    from publication_manager_service import request_approval_function

    reload(request_approval_function)

    create_ddb_table_property_web(dynamodb)
    create_test_eventbridge_bus(eventbridge)
    create_test_sqs_ingestion_queue(sqs)

    # get_property returns empty dict, then item.pop("status") raises KeyError
    with pytest.raises(KeyError):
        request_approval_function.lambda_handler(event, lambda_context)


@mock.patch.dict(os.environ, return_env_vars_dict({"EVENT_BUS": "nonexistent_bus"}), clear=True)
def test_eventbridge_failure(dynamodb, eventbridge, sqs, lambda_context):
    payload = load_event("request_approval_event")
    event = sqs_event([{"body": payload, "attributes": {"HttpMethod": "POST"}}])

    from publication_manager_service import request_approval_function

    reload(request_approval_function)

    create_ddb_table_property_web(dynamodb)
    # Intentionally do NOT create the event bus so put_events fails
    create_test_sqs_ingestion_queue(sqs)

    with pytest.raises(Exception, match="Unable to send event to Event Bus|Error sending requests to Event Bus"):
        request_approval_function.lambda_handler(event, lambda_context)
