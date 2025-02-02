#!/usr/bin/env python3
from aws_cdk import Tags, App, Stack
from cdk_nag import AwsSolutionsChecks
from unicorn_shared import STAGE, UNICORN_NAMESPACES
from unicorn_web_stack import UnicornWebStack

app = App()
#cdk.Aspects.of(app).add(AwsSolutionsChecks())

unicorn_web_stack = UnicornWebStack(app, f'uni-prop-{STAGE.local.value}-web', stage=STAGE.local)
Tags.of(unicorn_web_stack).add("stage", STAGE.local.value)
Tags.of(unicorn_web_stack).add("project", "AWS_Serverless_Developer_Experience")
Tags.of(unicorn_web_stack).add("namespace", UNICORN_NAMESPACES.WEB.value)

app.synth()
