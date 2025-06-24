#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from constructs import Construct
from aws_cdk import (
    Lazy, IStableStringProducer,
    aws_events as events,
    aws_events_targets as targets,
    aws_ssm as ssm,
)

from lib.helper import UNICORN_NAMESPACES

class CrossUniPropServiceSubscriptionConstruct(Construct):
    """
    Construct that creates a cross-service event subscription between EventBridge buses.
    Enables event-driven communication between different services.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        publisher_event_bus_arn_param: str,
        subscriber_event_bus: events.IEventBus,
        publisher_name_space: UNICORN_NAMESPACES,
        subscriber_name_space: UNICORN_NAMESPACES,
        event_type_name: str,
    ):
        """
        Creates a new cross-service event subscription.

        Args:
            scope: The scope in which to define this construct
            id: The scoped construct ID
            publisher_event_bus_arn_param: SSM parameter name containing the publisher's EventBus ARN
            subscriber_event_bus: EventBus instance that will receive the events
            publisher_name_space: Namespace identifier for the publishing service
            subscriber_name_space: Namespace identifier for the subscribing service
            event_type_name: Name of the event type to subscribe to

        This construct:
        - Retrieves the publisher's EventBus ARN from SSM Parameter Store
        - Creates an EventBridge rule on the publisher's bus
        - Configures the rule to forward matching events to the subscriber's bus
        """
        super().__init__(scope, id)

        # Retrieve the publisher's EventBus ARN from SSM Parameter Store
        publisher_event_bus_arn = ssm.StringParameter.value_from_lookup(
            self, publisher_event_bus_arn_param, "arn:aws:events:region:account:event-bus/name"
        )
        
        print(f"publisher_event_bus_arn: {publisher_event_bus_arn}")
        

        # Create reference to the publisher's EventBus
        publisher_event_bus = events.EventBus.from_event_bus_arn(
            self, "publisherEventBus", publisher_event_bus_arn
        )

        # Create EventBridge rule for the subscription
        rule_name = f"{publisher_name_space.value}-{event_type_name}"
        events.Rule(
            self,
            rule_name,
            rule_name=rule_name,
            description=f"Subscription to {event_type_name} events by the {subscriber_name_space.value} service.",
            event_bus=publisher_event_bus,
            event_pattern={
                "source": [publisher_name_space.value],
                "detail_type": [event_type_name],
            },
            targets=[targets.EventBus(subscriber_event_bus)],
        )
