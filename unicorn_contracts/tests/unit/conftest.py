# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext

import pytest
from moto import mock_dynamodb, mock_events, mock_sqs


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.fixture(scope='function')
def dynamodb(aws_credentials):
    with mock_dynamodb():
        yield boto3.resource('dynamodb', region_name='ap-southeast-2')


@pytest.fixture(scope='function')
def eventbridge(aws_credentials):
    with mock_events():
        yield boto3.client('events', region_name='ap-southeast-2')


@pytest.fixture(scope='function')
def sqs(aws_credentials):
    with mock_sqs():
        yield boto3.client('sqs', region_name='ap-southeast-2')


@pytest.fixture(scope='function')
def lambda_context():
    context: LambdaContext = LambdaContext()
    context._function_name="contractsService-LambdaFunction-IWaQgsTEtLtX"
    context._function_version="$LATEST"
    context._invoked_function_arn="arn:aws:lambda:ap-southeast-2:424490683636:function:contractsService-LambdaFunction-IWaQgsTEtLtX"
    context._memory_limit_in_mb=128
    context._aws_request_id="6f970d26-71d6-4c87-a196-9375f85c7b07"
    context._log_group_name="/aws/lambda/contractsService-LambdaFunction-IWaQgsTEtLtX"
    context._log_stream_name="2022/07/14/[$LATEST]7c71ca59882b4c569dd007c7e41c81e8"
    # context._identity=CognitoIdentity([cognito_identity_id=None,cognito_identity_pool_id=None])])
    # context._client_context=None
    return context
