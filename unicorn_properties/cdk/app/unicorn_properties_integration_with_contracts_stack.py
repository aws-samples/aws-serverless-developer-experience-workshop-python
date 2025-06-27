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


class PropertiesToContractsIntegrationStack(Stack):
    """
    Stack that manages integration between Properties and Contracts services.

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
        contracts_event_bus_arn: str,
        **kwargs,
    ):
        """
        Creates a new PropertiesToContractsIntegrationStack
        
        Args:
            scope: The scope in which to define this construct
            id: The scoped construct ID
            props: Stack configuration properties
            
        This stack creates:
        - Event subscription from Contracts service to Properties service
        - Routes ContractStatusUpdated events to the Properties service
        """
        super().__init__(scope, id, **kwargs)

        # Add standard tags to the CloudFormation stack for resource organization
        # and cost allocation
        StackHelper.add_stack_tags(
            self,
            {
                "namespace": UNICORN_NAMESPACES.PROPERTIES,
                "stage": stage,
            },
        )

        # Retrieve the Properties service EventBus name from SSM Parameter Store
        # and create a reference to the existing EventBus
        event_bus = events.EventBus.from_event_bus_name(
            self,
            "PropertiesEventBus",
            StackHelper.lookup_ssm_parameter(
                self, f"/uni-prop/{stage.value}/{event_bus_name}"
            ),
        )

        # Cross-service event subscription
        # Routes contract status events from Contracts service to Properties service
        #
        # Configuration:
        # - Subscribes to ContractStatusUpdated events
        # - Source filtered to Contracts service namespace
        # - Forwards events to Properties service event bus
        CrossUniPropServiceSubscriptionConstruct(
            self,
            "unicorn-properties-ContractStatusChangedSubscription",
            publisher_event_bus_arn_param=contracts_event_bus_arn,
            publisher_name_space=UNICORN_NAMESPACES.CONTRACTS,
            subscriber_event_bus=event_bus,
            subscriber_name_space=UNICORN_NAMESPACES.PROPERTIES,
            event_type_name="ContractStatusChanged",
        )
