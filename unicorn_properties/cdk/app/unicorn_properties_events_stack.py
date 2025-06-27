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
    
    Example:
    ```python
    app = cdk.App()
    PropertiesEventStack(app, 'PropertiesEventStack', 
        stage=STAGE.DEV,
        env={
            'account': os.environ.get('CDK_DEFAULT_ACCOUNT'),
            'region': os.environ.get('CDK_DEFAULT_REGION')
        }
    )
    ```
    """

    def __init__(self, scope: Construct, id: str, *, stage: STAGE, **kwargs) -> None:
        """
        Creates a new PropertiesEventStack
        
        Parameters:
            scope: The scope in which to define this construct
            id: The scoped construct ID
            stage: Deployment stage of the application (local, dev, prod)
            **kwargs: Additional keyword arguments passed to the parent Stack
        
        This stack creates:
        - Custom EventBridge event bus for the Properties service's domain events
        - Event bus resource policies for cross-account access
        - Event schema registry for maintaining event contract definitions
        - SSM parameters for service discovery
        - Development environment logging infrastructure
        - Event schemas for property publication workflow
        """
        super().__init__(scope, id, **kwargs)
        
        # Current deployment stage of the application
        self.stage = stage
        # Name of SSM Parameter that holds the EventBus for this service
        self.event_bus_name_parameter = "UnicornPropertiesEventBus"

        # Add standard tags to the CloudFormation stack for resource organization
        # and cost allocation
        StackHelper.add_stack_tags(
            self,
            {
                "namespace": UNICORN_NAMESPACES.PROPERTIES,
                "stage": stage,
            },
        )

        # --------------------------------------------------------------------------
        #                                 EVENT BUS                                 
        # --------------------------------------------------------------------------

        # Custom EventBridge event bus for the application
        # Handles all application-specific events and enables event-driven architecture
        event_bus = events.EventBus(
            self,
            f"UnicornPropertiesBus-{stage.value}",
            event_bus_name=f"UnicornPropertiesBus-{stage.value}",
        )

        # Resource policy allowing subscribers to create rules and targets
        # Enables other services to subscribe to events from this bus
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

        # Event bus policy restricting event publishing permissions
        # Only allows services from UnicornPropertiesNamespace to publish events
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

        # CloudFormation output exposing the EventBus name
        # Enables other stacks and services to reference this event bus
        StackHelper.create_output(
            self,
            {
                "name": self.event_bus_name_parameter,
                "value": event_bus.event_bus_name,
                "stage": stage.value,
                # Create an SSM Parameter to allow other services to discover the event bus
                "create_ssm_string_parameter": True,
            },
        )
        StackHelper.create_output(
            self,
            {
                "name": f"{self.event_bus_name_parameter}Arn",
                "value": event_bus.event_bus_arn,
                "stage": stage.value,
                # Create an SSM Parameter to allow other services to discover the event bus
                "create_ssm_string_parameter": True,
            },
        )

        # --------------------------------------------------------------------------
        #                           DEVELOPMENT LOGGING                             
        # --------------------------------------------------------------------------

        # Development environment event logging infrastructure
        #
        # Demonstrates debugging patterns for event-driven architectures:
        # - Captures all events for development visibility
        # - Implements environment-specific logging
        # - Provides audit trail for event flow
        #
        # Note: This logging is only enabled in local and dev environments
        if stage in [STAGE.LOCAL, STAGE.DEV]:
            # CloudWatch log group for catching all events during development
            # Helps with debugging and monitoring event flow
            catch_all_log_group = logs.LogGroup(
                self,
                "UnicornPropertiesCatchAllLogGroup",
                log_group_name=f"/aws/events/{stage.value}/{UNICORN_NAMESPACES.PROPERTIES.value}-catchall",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(stage),
            )

            # EventBridge rule to capture all events for development purposes
            # Routes all events to CloudWatch logs for visibility
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

            # CloudFormation outputs for log group information
            # Provides easy access to logging resources
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

        # --------------------------------------------------------------------------
        #                              EVENTS SCHEMA                                
        # --------------------------------------------------------------------------

        # EventBridge Schema Registry for event schema management
        # Stores and validates event schemas for the application
        registry = eventschemas.CfnRegistry(
            self,
            "EventRegistry",
            registry_name=f"{UNICORN_NAMESPACES.PROPERTIES.value}-{stage.value}",
            description=f"Event schemas for Unicorn Properties {stage.value}",
        )

        # Registry access policy
        # Controls who can access and use the event schemas
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
