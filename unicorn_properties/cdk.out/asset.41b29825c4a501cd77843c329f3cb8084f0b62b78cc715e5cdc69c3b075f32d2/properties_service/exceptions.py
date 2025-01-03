# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

class ContractStatusNotFoundException(Exception):
    """
    Custom exception for encapsulating exceptions Contract Status for a specified property is not found
    """

    def __init__(self, message=None, status_code=None, details=None):
        super(ContractStatusNotFoundException, self).__init__()

        self.message = message or "No contract found for specified Property ID"
        self.status_code = status_code or 400
        self.details = details or {}
