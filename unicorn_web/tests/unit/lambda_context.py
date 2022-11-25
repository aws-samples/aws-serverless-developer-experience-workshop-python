# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Simple Lambda Context class to be passed to the lambda handler when test is invoked
"""


class LambdaContext:
    aws_request_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    log_group_name="/aws/lambda/test_log_group_name"
    log_stream_name="2022/12/01/[$LATEST]aaaaaaaabbbbbbbbccccccccdddddddd"
    function_name="test_function_name"
    memory_limit_in_mb=128
    function_version="$LATEST"
    invoked_function_arn="arn:aws:lambda:ap-southeast-2:111111111111:function:test_function_name"
    client_context=None
    #identity=CognitoIdentity([cognito_identity_id=None,cognito_identity_pool_id=None])])
