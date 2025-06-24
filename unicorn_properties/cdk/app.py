#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import aws_cdk as cdk
# from cdk_nag import AwsSolutionsChecks

from lib.helper import get_stage_from_context
from app.unicorn_properties_events_stack import PropertiesEventStack
from app.unicorn_properties_contracts_stack import PropertyContractsStack
from app.unicorn_properties_property_approval_stack import PropertyApprovalStack
from app.unicorn_properties_integration_with_contracts_stack import PropertiesToContractsIntegrationStack
from app.unicorn_properties_integration_with_web_stack import PropertiesToWebIntegrationStack

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION")
)

app = cdk.App()
# cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

stage = get_stage_from_context(app)

events_stack = PropertiesEventStack(
    app,
    f"uni-prop-{stage.value}-properties-events",
    description="Unicorn Properties Events Service. Central event bus for unicorn properties.",
    stage=stage,
    env=env
)

contracts_stack = PropertyContractsStack(
    app,
    f"uni-prop-{stage.value}-properties-contracts",
    description="Unicorn Properties Contracts Service. Manages contract data.",
    stage=stage,
    env=env,
    event_bus_name_parameter=events_stack.event_bus_name_parameter
)
contracts_stack.add_dependency(
    events_stack,
    "requires EventBus from Events Stack"
)

property_approval_stack = PropertyApprovalStack(
    app,
    f"uni-prop-{stage.value}-properties-approval",
    description="Unicorn Properties Approval Service. Manages contract data.",
    stage=stage,
    env=env,
    event_bus_name=events_stack.event_bus_name_parameter,
    contract_status_table_name=contracts_stack.contract_status_table_name_parameter,
    property_approval_sync_function_iam_role_arn=contracts_stack.property_approval_sync_function_iam_role_arn_parameter
)
property_approval_stack.add_dependency(
    contracts_stack,
    "requires resources from Contracts stack"
)
property_approval_stack.add_dependency(
    events_stack,
    "requires EventBus from Events Stack"
)

# These stacks are used when integrating the Properties services with other Unicorn Properties services.
# They require the other services be fully deployed prior to deployment.
properties_to_contracts = PropertiesToContractsIntegrationStack(
    app,
    f"uni-prop-{stage.value}-properties-integration-with-contracts",
    description="Unicorn Properties to Contracts service integration.",
    stage=stage,
    event_bus_name=events_stack.event_bus_name_parameter,
    contracts_event_bus_arn=f"/uni-prop/{stage.value}/UnicornContractsEventBusArn",
    env=env
)
properties_to_contracts.add_dependency(
    property_approval_stack,
    "requires Property stack to be fully deployed"
)

properties_to_web = PropertiesToWebIntegrationStack(
    app,
    f"uni-prop-{stage.value}-properties-integration-with-web",
    description="Unicorn Properties to Web service integration.",
    stage=stage,
    event_bus_name=events_stack.event_bus_name_parameter,
    web_event_bus_arn_param=f"/uni-prop/{stage.value}/UnicornWebEventBusArn",
    env=env
)
properties_to_web.add_dependency(
    property_approval_stack,
    "requires Property service to be fully deployed"
)

app.synth()
