#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    aws_events as events,
)
from constructs import Construct

from app.constructs.unicorn_properties_service_subscription_construct import (
    CrossUniPropServiceSubscriptionConstruct,
)
from lib.helper import StackHelper, STAGE, UNICORN_NAMESPACES


class PropertiesToWebIntegrationStack(Stack):
    """
    Stack that manages integration between Properties and Web services.

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
        stage: STAGE,
        event_bus_name: str,
        web_event_bus_arn_param: str,
        **kwargs,
    ):

        super().__init__(scope, id, **kwargs)

        # Add standard tags
        StackHelper.add_stack_tags(
            self,
            {
                "namespace": UNICORN_NAMESPACES.PROPERTIES,
                "stage": stage,
            },
        )

        # Get reference to existing EventBus
        event_bus = events.EventBus.from_event_bus_name(
            self,
            "PropertiesEventBus",
            StackHelper.lookup_ssm_parameter(
                self, f"/uni-prop/{stage.value}/{event_bus_name}"
            ),
        )

        # Create cross-service event subscription
        CrossUniPropServiceSubscriptionConstruct(
            self,
            "unicorn.properies-PublicationApprovalRequestedSubscription",
            publisher_event_bus_arn_param=web_event_bus_arn_param,
            publisher_name_space=UNICORN_NAMESPACES.WEB,
            subscriber_event_bus=event_bus,
            subscriber_name_space=UNICORN_NAMESPACES.PROPERTIES,
            event_type_name="PublicationApprovalRequested",
        )
