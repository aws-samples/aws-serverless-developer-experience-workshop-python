# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import json
from importlib import reload

from unittest import mock

from .helper import load_event, return_env_vars_dict, create_ddb_table_property_web


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_search_by_city(dynamodb, lambda_context):
    apigw_event = load_event("search_by_city")

    from search_service import property_search_function

    reload(property_search_function)

    create_ddb_table_property_web(dynamodb)

    ret = property_search_function.lambda_handler(apigw_event, lambda_context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert type(data) == list
    # Only APPROVED items are returned; test data has 1 APPROVED item (main-street#124)
    assert len(data) == 1
    item = data[0]
    assert item["city"] == "Anytown"
    assert item["number"] == "124"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_search_by_city_and_street(dynamodb, lambda_context):
    apigw_event = load_event("search_by_street_event")

    from search_service import property_search_function

    reload(property_search_function)

    create_ddb_table_property_web(dynamodb)

    ret = property_search_function.lambda_handler(apigw_event, lambda_context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert type(data) == list
    # Only APPROVED items with SK beginning with "main-street#" are returned
    assert len(data) == 1
    item = data[0]
    assert item["city"] == "Anytown"
    assert item["number"] == "124"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_property_details_happy_path(dynamodb, lambda_context):
    apigw_event = load_event("search_by_full_address")

    from search_service import property_search_function

    reload(property_search_function)

    create_ddb_table_property_web(dynamodb)

    ret = property_search_function.lambda_handler(apigw_event, lambda_context)
    data = json.loads(ret["body"])

    assert ret["statusCode"] == 200
    assert data["city"] == "Anytown"
    assert data["number"] == "124"


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_property_not_found_returns_404(dynamodb, lambda_context):
    apigw_event = load_event("search_by_full_address_not_found")

    from search_service import property_search_function

    reload(property_search_function)

    create_ddb_table_property_web(dynamodb)

    ret = property_search_function.lambda_handler(apigw_event, lambda_context)

    assert ret["statusCode"] == 404


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_property_not_approved_returns_404(dynamodb, lambda_context):
    # main-street/125 has status DECLINED in test data
    apigw_event = load_event("search_by_full_address_declined")

    from search_service import property_search_function

    reload(property_search_function)

    create_ddb_table_property_web(dynamodb)

    ret = property_search_function.lambda_handler(apigw_event, lambda_context)

    assert ret["statusCode"] == 404


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_non_get_method_returns_error(dynamodb, lambda_context):
    apigw_event = load_event("search_by_city")
    # Change method to POST which is not supported by any route
    apigw_event["httpMethod"] = "POST"
    apigw_event["requestContext"]["httpMethod"] = "POST"

    from search_service import property_search_function

    reload(property_search_function)

    create_ddb_table_property_web(dynamodb)

    ret = property_search_function.lambda_handler(apigw_event, lambda_context)

    # ApiGatewayResolver returns 404 for unmatched routes (no POST handler)
    assert ret["statusCode"] in (400, 404, 405)
