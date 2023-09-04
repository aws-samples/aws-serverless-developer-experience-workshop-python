# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# import os
# import json

# from unittest import mock
# from importlib import reload

# from .lambda_context import LambdaContext
# from .helper import load_event, return_env_vars_dict, create_ddb_table_property_web


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_search_by_street(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/search_by_street_event.json')

#     # Loading function here so that mocking works correctly.
#     import search_service.property_search_function as app

#     # Reload is required to prevent function setup reuse from another test 
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 200
#     assert type(data) == list
#     assert len(data) == 1
#     item = data[0]
#     assert item['city'] == 'Anytown'
#     assert item['number'] == '124'


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_search_by_city(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/search_by_city.json')

#     # Loading function here so that mocking works correctly.
#     import search_service.property_search_function as app

#     # Reload is required to prevent function setup reuse from another test
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 200
#     assert type(data) == list
#     assert len(data) == 1
#     item = data[0]
#     assert item['city'] == 'Anytown'
#     assert item['number'] == '124'


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_search_full_address(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/search_by_full_address.json')

#     # Loading function here so that mocking works correctly.
#     import search_service.property_search_function as app

#     # Reload is required to prevent function setup reuse from another test
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 200
#     assert data['city'] == 'Anytown'
#     assert data['number'] == '124'


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_search_full_address_declined(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/search_by_full_address_declined.json')

#     # Loading function here so that mocking works correctly.
#     import search_service.property_search_function as app

#     # Reload is required to prevent function setup reuse from another test
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 404
#     assert 'message' in data
#     assert 'declined' in data['message'].lower()


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_search_full_address_new(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/search_by_full_address_new.json')

#     # Loading function here so that mocking works correctly.
#     import search_service.property_search_function as app

#     # Reload is required to prevent function setup reuse from another test
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 404
#     assert 'message' in data
#     assert 'new' in data['message'].lower()


# @mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
# def test_search_full_address_not_found(dynamodb, eventbridge, mocker):
#     apigw_event = load_event('events/search_by_full_address_not_found.json')

#     # Loading function here so that mocking works correctly.
#     import search_service.property_search_function as app

#     # Reload is required to prevent function setup reuse from another test
#     reload(app)

#     create_ddb_table_property_web(dynamodb)

#     context = LambdaContext()
#     ret = app.lambda_handler(apigw_event, context)  # type: ignore
#     data = json.loads(ret['body'])

#     assert ret['statusCode'] == 404
#     assert 'message' in data
#     assert 'not found' in data['message'].lower()
