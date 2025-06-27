# app/unicorn_web_events_stack.py
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from aws_cdk import Stack, RemovalPolicy
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_iam as iam
import aws_cdk.aws_logs as logs
import aws_cdk.aws_eventschemas as eventschemas

from lib.helper import get_default_logs_retention_period, StackHelper, STAGE, UNICORN_NAMESPACES

class WebEventsStack(Stack):
    """Stack that defines the Unicorn Web infrastructure
    
    Properties:
        stage: Deployment stage of the application
    
    Remarks:
        This stack creates:
        - DynamoDB table for data storage
        - API Gateway REST API
        - EventBridge event bus
        - Property publication Construct
        - Property eventing Construct
        - Associated IAM roles and permissions
    """
    
    def __init__(self, scope, id, *, stage: STAGE, **kwargs):
        """Creates a new WebEventsStack
        
        Args:
            scope: The scope in which to define this construct
            id: The scoped construct ID
            stage: Deployment stage of the application
            **kwargs: Configuration properties
        """
        super().__init__(scope, id, **kwargs)

        # Current deployment stage of the application
        self.stage = stage
        # Name of SSM Parameter that holds the EventBus for this service
        self.event_bus_name_parameter = "UnicornWebEventBus"
        
        # Add standard tags to the CloudFormation stack for resource organization
        # and cost allocation
        StackHelper.add_stack_tags(self, {
            "namespace": UNICORN_NAMESPACES.WEB,
            "stage": stage
        })
        
        # EVENT BUS
        
        # Custom EventBridge event bus for the application
        # Handles all application-specific events and enables event-driven architecture
        event_bus = events.EventBus(self, f"UnicornWebBus-{stage.value}", 
            event_bus_name=f"UnicornWebBus-{stage.value}"
        )
        
        # Resource policy allowing subscribers to create rules and targets
        # Enables other services to subscribe to events from this bus
        event_bus.add_to_resource_policy(
            iam.PolicyStatement(
                sid=f"AllowSubscribersToCreateSubscriptionRules-web-{stage.value}",
                effect=iam.Effect.ALLOW,
                principals=[iam.AccountRootPrincipal()],
                actions=["events:*Rule", "events:*Targets"],
                resources=[event_bus.event_bus_arn],
                conditions={
                    "StringEqualsIfExists": {
                        "events:creatorAccount": Stack.of(self).account
                    }
                }
            )
        )
        
        # Event bus policy restricting event publishing permissions
        # Only allows services from UnicornWebNamespace to publish events
        events.CfnEventBusPolicy(self, "UnicornWebEventsBusPublishPolicy",
            event_bus_name=event_bus.event_bus_name,
            statement_id=f"OnlyWebServiceCanPublishToEventBus-{stage.value}",
            statement=iam.PolicyStatement(
                principals=[iam.AccountRootPrincipal()],
                actions=["events:PutEvents"],
                resources=[event_bus.event_bus_arn],
                conditions={
                    "StringEquals": {"events:source": UNICORN_NAMESPACES.WEB.value}
                }
            ).to_json()
        )
        
        # CloudFormation output exposing the EventBus name
        # Enables other stacks and services to reference this event bus
        StackHelper.create_output(self, {
            "name": self.event_bus_name_parameter,
            "value": event_bus.event_bus_name,
            "stage": stage.value,
            "create_ssm_string_parameter": True
        })
        
        StackHelper.create_output(self, {
            "name": f"{self.event_bus_name_parameter}Arn",
            "value": event_bus.event_bus_arn,
            "stage": stage.value,
            "create_ssm_string_parameter": True
        })
        
        # DEVELOPMENT LOGGING
        # Development environment logging configuration
        # Creates CloudWatch log groups to capture all events for debugging
        if stage == STAGE.LOCAL or stage == STAGE.DEV:
            # CloudWatch log group for catching all events during development
            # Helps with debugging and monitoring event flow
            catch_all_log_group = logs.LogGroup(
                self, 
                "UnicornWebCatchAllLogGroup",
                log_group_name=f"/aws/events/{stage.value}/{UNICORN_NAMESPACES.WEB.value}-catchall",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(stage)
            )
            
            # EventBridge rule to capture all events for development purposes
            # Routes all events to CloudWatch logs for visibility
            events.Rule(self, "web.catchall",
                rule_name="web.catchall",
                description=f"Catch all events published by the {UNICORN_NAMESPACES.WEB.value} service.",
                event_bus=event_bus,
                event_pattern={
                    "account": [Stack.of(self).account],
                    "source": [UNICORN_NAMESPACES.WEB.value]
                },
                enabled=True,
                targets=[targets.CloudWatchLogGroup(catch_all_log_group)]
            )
            
            # CloudFormation outputs for log group information
            # Provides easy access to logging resources
            StackHelper.create_output(self, {
                "name": "UnicornWebCatchAllLogGroupName",
                "description": "Log all events on the service's EventBridge Bus",
                "value": catch_all_log_group.log_group_name,
                "stage": stage.value
            })
            
            StackHelper.create_output(self, {
                "name": "UnicornWebCatchAllLogGroupArn",
                "description": "Log all events on the service's EventBridge Bus",
                "value": catch_all_log_group.log_group_arn,
                "stage": stage.value
            })
        
        # EVENTS SCHEMA
        
        # EventBridge Schema Registry for event schema management
        # Stores and validates event schemas for the application
        registry = eventschemas.CfnRegistry(self, "EventRegistry",
            registry_name=f"{UNICORN_NAMESPACES.WEB.value}-{stage.value}",
            description=f"Event schemas for Unicorn Web {stage.value}"
        )
        
        # Registry access policy
        # Controls who can access and use the event schemas
        eventschemas.CfnRegistryPolicy(self, "RegistryPolicy",
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
                            "schemas:SearchSchemas"
                        ],
                        resources=[
                            registry.attr_registry_arn,
                            f"arn:aws:schemas:{Stack.of(self).region}:{Stack.of(self).account}:schema/{registry.attr_registry_name}*"
                        ]
                    )
                ]
            )
        )
