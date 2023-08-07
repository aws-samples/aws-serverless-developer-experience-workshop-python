# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os

import pytest
from unittest import mock

from .lambda_context import LambdaContext
from .helper import load_event, return_env_vars_dict


@pytest.fixture
def stepfunctions_event():
    return load_event('tests/events/lambda/content_integrity_validator_function_success.json')
    

@pytest.fixture
def invalid_image_moderation(stepfunctions_event):
    e = {
        'imageModerations': [
            {
                'ModerationLabels': [
                    {
                        "Confidence": 99.24723052978516,
                        "ParentName": "",
                        "Name": "Explicit Nudity"
                    },
                    {
                        "Confidence": 99.24723052978516,
                        "ParentName": "Explicit Nudity",
                        "Name": "Graphic Male Nudity"
                    },
                ]
            }
        ]
    }
    return {**stepfunctions_event, **e}


@pytest.fixture
def invalid_content_sentiment(stepfunctions_event):
    e = {
        'contentSentiment': {
            'Sentiment': 'NEGATIVE'
        }
    }
    return {**stepfunctions_event, **e}


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_image_and_valid_sentiment(stepfunctions_event):
    from properties_service import content_integrity_validator_function
    ret = content_integrity_validator_function.lambda_handler(stepfunctions_event, LambdaContext())

    assert ret['validation_result'] == "PASS"
    assert ret['imageModerations'] == stepfunctions_event['imageModerations']
    assert ret['contentSentiment'] == stepfunctions_event['contentSentiment']


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_valid_image_and_invalid_sentiment(invalid_content_sentiment):
    event = invalid_content_sentiment

    from properties_service import content_integrity_validator_function
    ret = content_integrity_validator_function.lambda_handler(event, LambdaContext())

    assert ret['validation_result'] == "FAIL"
    assert ret['imageModerations'] == event['imageModerations']
    assert ret['contentSentiment'] == event['contentSentiment']


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_invalid_image_and_valid_sentiment(invalid_image_moderation):
    event = invalid_image_moderation

    from properties_service import content_integrity_validator_function
    ret = content_integrity_validator_function.lambda_handler(event, LambdaContext())

    assert ret['validation_result'] == "FAIL"
    assert ret['imageModerations'] == event['imageModerations']
    assert ret['contentSentiment'] == event['contentSentiment']


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_invalid_image_and_invalid_sentiment(invalid_image_moderation, invalid_content_sentiment):
    event = {**invalid_image_moderation, **invalid_content_sentiment}

    from properties_service import content_integrity_validator_function
    ret = content_integrity_validator_function.lambda_handler(event, LambdaContext())

    assert ret['validation_result'] == "FAIL"
    assert ret['imageModerations'] == event['imageModerations']
    assert ret['contentSentiment'] == event['contentSentiment']
