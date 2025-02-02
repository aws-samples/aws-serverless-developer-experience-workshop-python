#!/usr/bin/env python3
from aws_cdk import Tags, App, Stack
from cdk_nag import AwsSolutionsChecks
from unicorn_shared import STAGE, UNICORN_NAMESPACES
from unicorn_properties_stack import UnicornPropertiesStack

app = App()
#cdk.Aspects.of(app).add(AwsSolutionsChecks())

unicorn_properties = UnicornPropertiesStack(app, f'uni-prop-{STAGE.local.value}-properties', stage=STAGE.local)
Tags.of(unicorn_properties).add("stage", STAGE.local.value)
Tags.of(unicorn_properties).add("project", "AWS_Serverless_Developer_Experience")
Tags.of(unicorn_properties).add("namespace", UNICORN_NAMESPACES.PROPERTIES.value)

app.synth()
