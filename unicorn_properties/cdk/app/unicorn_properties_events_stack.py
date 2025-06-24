#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_logs as logs,
    aws_eventschemas as eventschemas,
)
from constructs import Construct
from typing import Any

from lib.helper import (
    get_default_logs_retention_period,
    StackHelper,
    STAGE,
    UNICORN_NAMESPACES,
)

class PropertiesEventStack(Stack):
    """
    Stack that defines the core event infrastructure for the Properties service.

    This stack establishes the event backbone of the application, demonstrating
    key concepts of event-driven architectures including:
    - Custom event buses for domain-specific events
    - Event schema management and validation
    - Development-time event logging
    - Cross-service event routing
    """

    def __init__(self, scope: Construct, id: str, *, stage: STAGE, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        self.event_bus_name_parameter = "UnicornPropertiesEventBus"

        # Add standard tags to the CloudFormation stack
        StackHelper.add_stack_tags(
            self,
            {
                "namespace": UNICORN_NAMESPACES.PROPERTIES,
                "stage": stage,
            },
        )

        # Create EventBridge event bus
        event_bus = events.EventBus(
            self,
            f"UnicornPropertiesBus-{stage.value}",
            event_bus_name=f"UnicornPropertiesBus-{stage.value}",
        )

        # Add resource policy for subscribers
        event_bus.add_to_resource_policy(
            iam.PolicyStatement(
                sid=f"AllowSubscribersToCreateSubscriptionRules-properties-{stage.value}",
                effect=iam.Effect.ALLOW,
                principals=[iam.AccountRootPrincipal()],
                actions=["events:*Rule", "events:*Targets"],
                resources=[event_bus.event_bus_arn],
                conditions={
                    "StringEqualsIfExists": {
                        "events:creatorAccount": Stack.of(self).account
                    }
                },
            )
        )

        # Create event bus policy for publishing
        events.CfnEventBusPolicy(
            self,
            "UnicornPropertiesEventsBusPublishPolicy",
            event_bus_name=event_bus.event_bus_name,
            statement_id=f"OnlyPropertiesServiceCanPublishToEventBus-{stage.value}",
            statement=iam.PolicyStatement(
                principals=[iam.AccountRootPrincipal()],
                actions=["events:PutEvents"],
                resources=[event_bus.event_bus_arn],
                conditions={
                    "StringEquals": {"events:source": UNICORN_NAMESPACES.PROPERTIES.value}
                },
            ).to_json(),
        )

        # Create outputs for event bus
        StackHelper.create_output(
            self,
            {
                "name": self.event_bus_name_parameter,
                "value": event_bus.event_bus_name,
                "stage": stage.value,
                "create_ssm_string_parameter": True,
            },
        )
        StackHelper.create_output(
            self,
            {
                "name": f"{self.event_bus_name_parameter}Arn",
                "value": event_bus.event_bus_arn,
                "stage": stage.value,
                "create_ssm_string_parameter": True,
            },
        )

        # Development environment logging
        if stage in [STAGE.LOCAL, STAGE.DEV]:
            catch_all_log_group = logs.LogGroup(
                self,
                "UnicornPropertiesCatchAllLogGroup",
                log_group_name=f"/aws/events/{stage.value}/{UNICORN_NAMESPACES.PROPERTIES.value}-catchall",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(stage),
            )

            events.Rule(
                self,
                "properties.catchall",
                rule_name="properties.catchall",
                description=f"Catch all events published by the {UNICORN_NAMESPACES.PROPERTIES.value} service.",
                event_bus=event_bus,
                event_pattern={
                    "account": [Stack.of(self).account],
                    "source": [UNICORN_NAMESPACES.PROPERTIES.value],
                },
                enabled=True,
                targets=[targets.CloudWatchLogGroup(catch_all_log_group)],
            )

            StackHelper.create_output(
                self,
                {
                    "name": "UnicornPropertiesCatchAllLogGroupName",
                    "description": "Log all events on the service's EventBridge Bus",
                    "value": catch_all_log_group.log_group_name,
                    "stage": stage.value,
                },
            )
            StackHelper.create_output(
                self,
                {
                    "name": "UnicornPropertiesCatchAllLogGroupArn",
                    "description": "Log all events on the service's EventBridge Bus",
                    "value": catch_all_log_group.log_group_arn,
                    "stage": stage.value,
                },
            )

        # Create event schema registry
        registry = eventschemas.CfnRegistry(
            self,
            "EventRegistry",
            registry_name=f"{UNICORN_NAMESPACES.PROPERTIES.value}-{stage.value}",
            description=f"Event schemas for Unicorn Properties {stage.value}",
        )

        eventschemas.CfnRegistryPolicy(
            self,
            "RegistryPolicy",
            registry_name=registry.attr_registry_name,
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="AllowExternalServices",
                        effect=iam.Effect.ALLOW,
                        principals=[iam.AccountPrincipal(Stack.of(self).account)],
                        actions=[
                            "schemas:DescribeCodeBinding",
                            "schemas:DescribeRegistry",
                            "schemas:DescribeSchema",
                            "schemas:GetCodeBindingSource",
                            "schemas:ListSchemas",
                            "schemas:ListSchemaVersions",
                            "schemas:SearchSchemas",
                        ],
                        resources=[
                            registry.attr_registry_arn,
                            f"arn:aws:schemas:{Stack.of(self).region}:{Stack.of(self).account}:schema/{registry.attr_registry_name}*",
                        ],
                    )
                ]
            ).to_json(),
        )