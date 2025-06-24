# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from dataclasses import dataclass
from constructs import Construct
from aws_cdk import Lazy

import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_ssm as ssm
from lib.helper import UNICORN_NAMESPACES


class CrossUniPropServiceSubscriptionConstruct(Construct):
    """
    Construct that creates a cross-service event subscription between EventBridge buses
    Enables event-driven communication between different services
    """
    
    def __init__(
        self,
        scope: Construct,
        id: str,
        publisher_event_bus_arn_param: str,
        subscriber_event_bus: events.IEventBus,
        publisher_name_space: UNICORN_NAMESPACES,
        subscriber_name_space: UNICORN_NAMESPACES,
        event_type_name: str
    ):
        """
        Creates a new cross-service event subscription
        
        Parameters:
        - scope: The scope in which to define this construct
        - id: The scoped construct ID
        - publisher_event_bus_arn_param: SSM parameter name containing the publisher's EventBus ARN
        - subscriber_event_bus: EventBus instance that will receive the events
        - publisher_name_space: Namespace identifier for the publishing service
        - subscriber_name_space: Namespace identifier for the subscribing service
        - event_type_name: Name of the event type to subscribe to
        
        This construct:
        - Retrieves the publisher's EventBus ARN from SSM Parameter Store
        - Creates an EventBridge rule on the publisher's bus
        - Configures the rule to forward matching events to the subscriber's bus
        """
        super().__init__(scope, id)
        
        # PUBLISHER EVENT BUS LOOKUP
        
        # Convert the SSM parameter value to a token
        # Required because valueFromLookup returns a dummy value during initial synthesis
        # Token ensures the actual value is resolved after the lookup is completed
        resolved_publisher_event_bus_arn = ssm.StringParameter.value_from_lookup(
            self, publisher_event_bus_arn_param, "arn:partition:service:region:account-id:resource-id"
        )
        
        # EVENT SUBSCRIPTION SETUP
        
        # Reference to the publisher's EventBus
        # Created using the ARN retrieved from SSM
        publisher_event_bus = events.EventBus.from_event_bus_arn(
            self,
            'publisherEventBus',
            resolved_publisher_event_bus_arn
        )
        
        # EventBridge rule for the subscription
        # Forwards matching events from publisher to subscriber
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
            enabled=True,
            targets=[targets.EventBus(subscriber_event_bus)]
        )
