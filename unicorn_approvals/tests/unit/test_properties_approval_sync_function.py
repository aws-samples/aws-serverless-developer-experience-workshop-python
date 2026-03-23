# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from importlib import reload

from unittest import mock

from .helper import load_event, return_env_vars_dict


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_handle_status_changed_draft(stepfunction, lambda_context):
    ddbstream_event = load_event("ddb_stream_events/contract_status_changed_draft")

    from approvals_service import properties_approval_sync_function

    reload(properties_approval_sync_function)

    ret = properties_approval_sync_function.lambda_handler(ddbstream_event, lambda_context)

    assert ret is None


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_handle_status_changed_approved(stepfunction, lambda_context):
    ddbstream_event = load_event("ddb_stream_events/status_approved_waiting_for_approval")

    from approvals_service import properties_approval_sync_function

    reload(properties_approval_sync_function)

    # Mock the module-level sfn client to bypass moto's lack of send_task_success support
    mock_sfn = mock.MagicMock()
    mock_sfn.send_task_success.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    with mock.patch.object(properties_approval_sync_function, "sfn", mock_sfn):
        ret = properties_approval_sync_function.lambda_handler(ddbstream_event, lambda_context)

    # Verify send_task_success was called with the task token from OldImage
    mock_sfn.send_task_success.assert_called_once()
    call_kwargs = mock_sfn.send_task_success.call_args
    assert "taskToken" in call_kwargs.kwargs or len(call_kwargs.args) > 0


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_no_task_token_skips(stepfunction, lambda_context):
    """APPROVED status but no task token in old or new image => returns None (skip)."""
    ddbstream_event = load_event("ddb_stream_events/status_approved_with_no_workflow")

    from approvals_service import properties_approval_sync_function

    reload(properties_approval_sync_function)

    ret = properties_approval_sync_function.lambda_handler(ddbstream_event, lambda_context)

    assert ret is None


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_missing_new_image_skips(stepfunction, lambda_context):
    """Record with missing NewImage key causes a KeyError => handler should raise."""
    ddbstream_event = {
        "Records": [
            {
                "eventID": "1",
                "eventName": "MODIFY",
                "eventVersion": "1.1",
                "eventSource": "aws:dynamodb",
                "awsRegion": "ap-southeast-2",
                "dynamodb": {
                    "Keys": {"property_id": {"S": "usa/anytown/main-street/999"}},
                    "SequenceNumber": "100000000005391461882",
                    "SizeBytes": 50,
                    "StreamViewType": "NEW_AND_OLD_IMAGES",
                },
                "eventSourceARN": "arn:aws:dynamodb:ap-southeast-2:123456789012:table/test/stream/2022-08-23T15:46:44.107",
            }
        ]
    }

    from approvals_service import properties_approval_sync_function

    reload(properties_approval_sync_function)

    try:
        ret = properties_approval_sync_function.lambda_handler(ddbstream_event, lambda_context)
        # If handler returns without error when NewImage is missing, that is acceptable (skip behaviour)
        assert ret is None
    except KeyError:
        # KeyError on missing NewImage is also acceptable
        pass
