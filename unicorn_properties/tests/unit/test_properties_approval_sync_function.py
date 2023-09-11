# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from importlib import reload

from unittest import mock

from .helper import load_event, return_env_vars_dict


@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_handle_status_changed_draft(stepfunction, lambda_context):
    ddbstream_event = load_event('ddb_stream_events/contract_status_changed_draft')

    from properties_service import properties_approval_sync_function
    reload(properties_approval_sync_function)

    ret = properties_approval_sync_function.lambda_handler(ddbstream_event, lambda_context)

    assert ret is None


# NOTE: This test cannot be implemented at this time because `moto`` does not yet support mocking `stepfunctions.send_task_success`
@mock.patch.dict(os.environ, return_env_vars_dict(), clear=True)
def test_handle_status_changed_approved(caplog, stepfunction, lambda_context):
    pass
    # ddbstream_event = load_event('ddb_stream_events/status_approved_waiting_for_approval')

    # from properties_service import properties_approval_sync_function
    # reload(properties_approval_sync_function)

    # ret = properties_approval_sync_function.lambda_handler(ddbstream_event, lambda_context)

    # assert ret is None
    # assert 'Contract status for property is APPROVED' in caplog.text
