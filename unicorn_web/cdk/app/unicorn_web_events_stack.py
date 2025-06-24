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
    """Stack that defines the Unicorn Web Events infrastructure"""
    
    def __init__(self, scope, id, *, stage: STAGE, **kwargs):
        super().__init__(scope, id, **kwargs)

        self.event_bus_name_parameter = "UnicornWebEventBus"
        
        # Add standard tags to the CloudFormation stack
        StackHelper.add_stack_tags(self, {
            "namespace": UNICORN_NAMESPACES.WEB,
            "stage": stage
        })
        
        # EVENT BUS
        event_bus = events.EventBus(self, f"UnicornWebBus-{stage.value}", 
            event_bus_name=f"UnicornWebBus-{stage.value}"
        )
        
        # Resource policy allowing subscribers to create rules and targets
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
        events.CfnEventBusPolicy(self, "UnicornWebEventsBusPublishPolicy",
            event_bus_name=event_bus.event_bus_name,
            statement_id=f"OnlyWebServiceCanPublishToEventBus-{stage.value}",
            statement=iam.PolicyStatement(
                principals=[iam.AccountRootPrincipal()],
                actions=["events:PutEvents"],
                resources=[event_bus.event_bus_arn],
                sid=f"OnlyWebServiceCanPublishToEventBus-{stage.value}",
                conditions={
                    "StringEquals": {"events:source": UNICORN_NAMESPACES.WEB.value}
                }
            ).to_json()
        )
        
        # CloudFormation output exposing the EventBus name
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
        if stage == STAGE.LOCAL or stage == STAGE.DEV:
            catch_all_log_group = logs.LogGroup(
                self, 
                "UnicornWebCatchAllLogGroup",
                log_group_name=f"/aws/events/{stage.value}/{UNICORN_NAMESPACES.WEB.value}-catchall",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(stage)
            )
            
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
        registry = eventschemas.CfnRegistry(self, "EventRegistry",
            registry_name=f"{UNICORN_NAMESPACES.WEB.value}-{stage.value}",
            description=f"Event schemas for Unicorn Web {stage.value}"
        )
        
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
