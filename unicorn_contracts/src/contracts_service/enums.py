# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from enum import Enum


class ContractStatus(Enum):
    """Contract status Enum
 
    APPROVED 	The contract record is approved.
    CANCELLED   The contract record is canceled or terminated. You cannot modify a contract record that has this status value.
    CLOSED 	    The contract record is closed and all its terms and conditions are met.
                You cannot modify a contract record that has this status value.
    DRAFT 	    The contract is a draft.
    EXPIRED 	The contract record is expired. The end date for the contract has passed.
                You cannot modify a contract record that has this status value.
                You can change the status from expire to pending revision by revising the expired contract.
 
    Parameters
    ----------
    Enum : _type_
        _description_
    """
    APPROVED = 1
    CANCELLED = 2
    CLOSED = 3
    DRAFT = 4
    EXPIRED = 5
