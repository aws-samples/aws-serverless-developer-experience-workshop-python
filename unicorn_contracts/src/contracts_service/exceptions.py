# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json


class ContractNotFoundException(Exception):
    """
    Custom exception for encapsulating exceptions for Lambda handler
    """

    def __init__(self, message=None, status_code=None, details=None):
        super(ContractNotFoundException, self).__init__()

        self.message = message or "No contract found for specified Property ID"
        self.status_code = status_code or 400
        self.details = details or {}
        
        self.apigw_return = {
            "statusCode": self.status_code,
            "body": json.dumps({"message": self.message})
        }
