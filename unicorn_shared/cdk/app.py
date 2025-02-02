#!/usr/bin/env python3
from cdk_nag import AwsSolutionsChecks
from unicorn_shared import STAGE, UNICORN_NAMESPACES
from aws_cdk import Tags, App, Stack

from unicorn_shared_stack import UnicornSharedStack

app = App()
#cdk.Aspects.of(app).add(AwsSolutionsChecks())

unicorn_contracts = UnicornSharedStack(app, f'uni-prop-{STAGE.local.value}-shared', stage=STAGE.local)
Tags.of(unicorn_contracts).add("stage", STAGE.local.value)
Tags.of(unicorn_contracts).add("project", "AWS_Serverless_Developer_Experience")
Tags.of(unicorn_contracts).add("namespace", UNICORN_NAMESPACES.CONTRACTS.value)

app.synth()
