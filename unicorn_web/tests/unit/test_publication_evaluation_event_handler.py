# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from importlib import reload

import pytest
from unittest import mock

from .helper import TABLE_NAME, load_event, return_env_vars_dict, create_ddb_table_property_web


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_property_approved(dynamodb, lambda_context):
    eventbridge_event = load_event("property_approved")
    property_id = eventbridge_event["detail"]["property_id"]

    from publication_manager_service import publication_evaluation_event_handler

    reload(publication_evaluation_event_handler)

    create_ddb_table_property_web(dynamodb)

    ret = publication_evaluation_event_handler.lambda_handler(eventbridge_event, lambda_context)
    assert ret["result"] == "Successfully updated property status"

    # property_id = "usa/anytown/main-street/126" => PK = PROPERTY#usa#anytown, SK = main-street#126
    country, city, street, number = property_id.split("/")
    pk = f"PROPERTY#{country}#{city}"
    sk = f"{street}#{number}"
    ddbitem_after = dynamodb.Table(TABLE_NAME).get_item(Key={"PK": pk, "SK": sk})
    assert ddbitem_after["Item"]["status"] == "APPROVED"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_property_declined(dynamodb, lambda_context):
    eventbridge_event = load_event("property_approved")
    # Change the evaluation result to DECLINED
    eventbridge_event["detail"]["evaluation_result"] = "DECLINED"
    property_id = eventbridge_event["detail"]["property_id"]

    from publication_manager_service import publication_evaluation_event_handler

    reload(publication_evaluation_event_handler)

    create_ddb_table_property_web(dynamodb)

    ret = publication_evaluation_event_handler.lambda_handler(eventbridge_event, lambda_context)
    assert ret["result"] == "Successfully updated property status"

    country, city, street, number = property_id.split("/")
    pk = f"PROPERTY#{country}#{city}"
    sk = f"{street}#{number}"
    ddbitem_after = dynamodb.Table(TABLE_NAME).get_item(Key={"PK": pk, "SK": sk})
    assert ddbitem_after["Item"]["status"] == "DECLINED"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_unknown_result_no_update(dynamodb, lambda_context):
    eventbridge_event = load_event("property_approved")
    # Set evaluation result to an unknown value
    eventbridge_event["detail"]["evaluation_result"] = "UNKNOWN_STATUS"

    from publication_manager_service import publication_evaluation_event_handler

    reload(publication_evaluation_event_handler)

    create_ddb_table_property_web(dynamodb)

    ret = publication_evaluation_event_handler.lambda_handler(eventbridge_event, lambda_context)
    assert "Skipped" in ret["result"]


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_invalid_property_id(dynamodb, lambda_context):
    eventbridge_event = load_event("property_approved")
    # Set an invalid property_id that cannot be split into 4 parts
    eventbridge_event["detail"]["property_id"] = "invalid"

    from publication_manager_service import publication_evaluation_event_handler

    reload(publication_evaluation_event_handler)

    create_ddb_table_property_web(dynamodb)

    with pytest.raises(ValueError):
        publication_evaluation_event_handler.lambda_handler(eventbridge_event, lambda_context)
