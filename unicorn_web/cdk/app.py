#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from aws_cdk import aws_lambda as lambda_, App, Aws

from lib.helper import get_stage_from_context
from app.unicorn_web_events_stack import WebEventsStack
from app.unicorn_web_api_stack import WebApiStack
from app.unicorn_web_property_search_stack import (
    WebPropertySearchStack,
    WebPropertySearchStackProps,
)
from app.unicorn_web_property_publication_stack import (
    WebPropertyPublicationStack,
    WebPropertyPublicationStackProps,
)

from app.unicorn_web_integration_with_properties_stack import (
    WebToPropertiesIntegrationStack,
    WebToPropertiesIntegrationStackProps,
)

"""
Environment configuration for AWS deployment
Uses CDK default account and region from environment variables
"""
env = {
    "account": os.environ.get("CDK_DEFAULT_ACCOUNT"),
    "region": os.environ.get("CDK_DEFAULT_REGION"),
}

"""
Initialize the CDK application
"""
app = App()

"""
Retrieve deployment stage from CDK context
Determines the environment (dev, test, prod) for resource naming and configuration
"""
stage = get_stage_from_context(app)

events_stack = WebEventsStack(
    app,
    f"uni-prop-{stage.value}-web-events",
    description="Unicorn Web Events Service",
    stage=stage,
    env=env,
)

powertools_layer = lambda_.LayerVersion.from_layer_version_arn(
    events_stack,
    "UnicornWebPowertoolLayer",
    layer_version_arn=f"arn:aws:lambda:{Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-x86_64:4",
)

api_stack = WebApiStack(
    app,
    f"uni-prop-{stage.value}-web-api",
    description="Unicorn Web API Base Infrastructure",
    stage=stage,
    env=env,
)
api_stack.add_dependency(events_stack, "requires EventBus from Events Stack")

# """
# Deploy the property search service
# Creates:
# - Lambda function
# - API Gateway endpoint
# - DynamoDB table
# - EventBridge rule to trigger the Lambda function
# """
search_stack_props = WebPropertySearchStackProps(
    description="Unicorn Web Property Search Service",
    stage=stage,
    event_bus_name=events_stack.event_bus_name_parameter,
    table_name=api_stack.web_table_name_parameter,
    rest_api_id=api_stack.web_rest_api_id_parameter,
    rest_api_root_resource_id=api_stack.web_api_root_resource_id_parameter,
    rest_api_url=api_stack.web_api_url_parameter,
    powertools_layer=powertools_layer,
    env=env,
)
property_search_stack = WebPropertySearchStack(
    app,
    f"uni-prop-{stage.value}-web-property-search",
    props=search_stack_props,
)
property_search_stack.add_dependency(api_stack, "requires Table and Api from Api Stack")


publication_stack_props = WebPropertyPublicationStackProps(
    description="Unicorn Web Property Publication Service",
    stage=stage,
    event_bus_name=events_stack.event_bus_name_parameter,
    table_name=api_stack.web_table_name_parameter,
    rest_api_id=api_stack.web_rest_api_id_parameter,
    rest_api_root_resource_id=api_stack.web_api_root_resource_id_parameter,
    rest_api_url=api_stack.web_api_url_parameter,
    powertools_layer=powertools_layer,
)
property_publication_stack = WebPropertyPublicationStack(
    app,
    f"uni-prop-{stage.value}-web-property-publication",
    props=publication_stack_props,
)
property_publication_stack.add_dependency(
    api_stack, "requires Table and Api from Api Stack"
)

# """
# Deploy the integration stack between Web and Properties services
# Creates:
# - Event subscriptions between services
# - Cross-service communication infrastructure

# Parameters:
# - webStack.eventBus - EventBus from the main web stack for event routing
# - propertiesEventBusArnParam - SSM parameter containing the Properties service EventBus ARN
# """
web_to_properties_stack_props = WebToPropertiesIntegrationStackProps(
    description="Unicorn Web to Properties Service integration.",
    stage=stage,
    env=env,
    event_bus_name_parameter=events_stack.event_bus_name_parameter,
    properties_event_bus_arn_param=f"/uni-prop/{stage.value}/UnicornPropertiesEventBusArn",
)

web_to_properties = WebToPropertiesIntegrationStack(
    app,
    f"uni-prop-{stage.value}-web-integration-with-properties",
    props=web_to_properties_stack_props,
)
web_to_properties.add_dependency(
    property_publication_stack,
    "requires Web service to be fully deployed"
)
web_to_properties.add_dependency(
    property_search_stack,
    "requires Web service to be fully deployed"
)

app.synth()
