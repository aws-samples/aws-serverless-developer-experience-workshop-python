#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import aws_cdk as cdk
# from cdk_nag import AwsSolutionsChecks, Aspects

from lib.helper import get_stage_from_context
from app.unicorn_contracts_stack import UnicornContractsStack

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION")
)

app = cdk.App()
# Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

stage = get_stage_from_context(app)

UnicornContractsStack(app, f"uni-prop-{stage.value}-contracts",
    description="Unicorn Contracts Service. Manage contract information for property listings.",
    stage=stage,
    env=env
)

app.synth()