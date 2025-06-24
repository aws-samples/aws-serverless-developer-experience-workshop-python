# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from dataclasses import dataclass
from constructs import Construct
import aws_cdk as cdk
from aws_cdk import aws_events as events

from app.constructs.unicorn_properties_service_subscription_construct import (
    CrossUniPropServiceSubscriptionConstruct,
)
from lib.helper import StackHelper, STAGE, UNICORN_NAMESPACES


@dataclass
class WebToPropertiesIntegrationStackProps:
    """
    Properties for the WebToPropertiesIntegrationStack

    Defines configuration properties required for service integration between
    the Web and Properties services, demonstrating loose coupling through
    event-driven integration patterns.
    """

    description: str
    stage: STAGE
    env: dict
    event_bus_name_parameter: str
    properties_event_bus_arn_param: str


class WebToPropertiesIntegrationStack(cdk.Stack):
    """
    Stack that manages integration between Web and Properties services
    Handles event routing and subscriptions between the two services

    This stack demonstrates microservice integration patterns including:
    - Event-driven service communication
    - Cross-service event routing
    - Service discovery using SSM parameters
    - Loose coupling through event subscriptions
    - Domain event filtering
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        props: WebToPropertiesIntegrationStackProps,
        **kwargs,
    ):
        """
        Creates a new WebToPropertiesIntegrationStack

        Parameters:
        - scope: The scope in which to define this construct
        - id: The scoped construct ID
        - props: Stack configuration properties

        This stack creates:
        - Event subscription from Properties service to Web service
        - Routes PublicationEvaluationCompleted events to the Web service
        """
        super().__init__(scope, id, description=props.description, env=props.env)

        # Add standard tags to the CloudFormation stack for resource organization
        # and cost allocation
        StackHelper.add_stack_tags(
            self,
            {
                "namespace": UNICORN_NAMESPACES.WEB,
                "stage": props.stage,
            },
        )

        # Retrieve the Properties service EventBus name from SSM Parameter Store
        # and create a reference to the existing EventBus
        event_bus = events.EventBus.from_event_bus_name(
            self,
            "WebEventBus",
            StackHelper.lookup_ssm_parameter(
                self, f"/uni-prop/{props.stage.value}/{props.event_bus_name_parameter}"
            ),
        )

        # Cross-service event subscription
        # Routes property evaluation events from Properties service to Web service
        #
        # Configuration:
        # - Subscribes to PublicationEvaluationCompleted events
        # - Source filtered to Properties service namespace
        # - Forwards events to Web service event bus
        CrossUniPropServiceSubscriptionConstruct(
            self,
            "unicorn.web-PublicationEvaluationCompletedSubscription",
            publisher_event_bus_arn_param=props.properties_event_bus_arn_param,
            publisher_name_space=UNICORN_NAMESPACES.PROPERTIES,
            subscriber_event_bus=event_bus,
            subscriber_name_space=UNICORN_NAMESPACES.WEB,
            event_type_name="PublicationEvaluationCompleted",
        )
