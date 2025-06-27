#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_lambda as lambda_,
    aws_lambda_nodejs as nodejs,
    aws_lambda_event_sources as event_sources,
    aws_logs as logs,
    aws_sqs as sqs,
    Aws,
)
from constructs import Construct

from lib.helper import (
    get_default_logs_retention_period,
    StackHelper,
    STAGE,
    UNICORN_NAMESPACES,
)

class PropertyContractsStack(Stack):
    """
    Stack that defines the Properties service's Contract Management infrastructure.

    This stack manages the integration between the Properties service and Contracts service,
    handling contract status changes and property approval synchronization.
    """

    # create constructor comment

    def __init__(self, scope: Construct, id: str, *, stage: STAGE, event_bus_name_parameter: str, **kwargs):
        """
        Creates a new PropertyContractsStack
        
        Parameters:
            scope: The scope in which to define this construct
            id: The scoped construct ID
            props: Configuration properties
        
        This stack creates:
        - DynamoDB table for contract status tracking with stream enabled
        - Dead Letter Queues for error handling
        - Lambda function to handle ContractStatusChange events from EventBridge
        - Lambda function to sync property approvals based on DynamoDB stream events
        - EventBridge rule for routing ContractStatusChanged events
        - Associated IAM roles and permissions
        """
        super().__init__(scope, id, **kwargs)

        self.contract_status_table_name_parameter = "ContractStatusTableName"
        self.property_approval_sync_function_iam_role_arn_parameter = "PropertiesApprovalSyncFunctionIamRoleArn"

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
                self,
                f"/uni-prop/{stage.value}/{event_bus_name_parameter}"
            )
        )

        # -------------------------------------------------------------------------- 
        #                                  STORAGE                                   
        # -------------------------------------------------------------------------- 

        # DynamoDB table for storing contract status data
        # Uses property_id as partition key for efficient querying
        # Includes stream configuration to trigger the PropertiesApprovalSync function
        table = dynamodb.TableV2(
            self,
            "ContractStatusTable",
            table_name=f"uni-prop-{stage.value}-properties-ContractStatusTable",
            partition_key=dynamodb.Attribute(
                name="property_id",
                type=dynamodb.AttributeType.STRING
            ),
            dynamo_stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.DESTROY  # be careful with this in production
        )

        # CloudFormation output for Contracts table name
        StackHelper.create_output(
            self,
            {
                "name": self.contract_status_table_name_parameter,
                "description": "DynamoDB table storing contract status information",
                "value": table.table_name,
                "stage": stage.value,
                "create_ssm_string_parameter": True,
            },
        )

        # --------------------------------------------------------------------------
        #                            LAMBDA FUNCTIONS                                
        # --------------------------------------------------------------------------

        # Dead Letter Queue for the Properties service
        # Handles failed event processing
        properties_service_dlq = sqs.Queue(
            self,
            "PropertiesServiceDlq",
            queue_name=f"PropertiesServiceDlq-{stage.value}",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # DLQ for failed EventBridge event delivery to ContractEventHandlerFunction
        contract_status_changed_events_dlq = sqs.Queue(
            self,
            "ContractStatusChangedEventsDlq",
            queue_name=f"ContractStatusChangedEventsDlq-{stage.value}",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
        )

        powertools_lambda_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            'UnicornContractsLayer',
            layer_version_arn=f'arn:aws:lambda:{Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-x86_64:4'
        )

        # Lambda function to handle ContractStatusChange events
        contract_status_changed_function = lambda_.Function(
            self,
            f"ContractEventHandlerFunction-{stage.value}",
            runtime=lambda_.Runtime.PYTHON_3_13,
            code=lambda_.Code.from_asset('src/'),
            handler='properties_service.contract_status_changed_event_function.lambda_handler',
            environment={
                "TABLE_NAME": table.table_name,
                "STAGE": stage.value,
                "SERVICE_NAMESPACE": UNICORN_NAMESPACES.PROPERTIES.value,
            },
            dead_letter_queue=properties_service_dlq,
            log_group=logs.LogGroup(
                self,
                "ContractStatusChangedHandlerFunctionLogGroup",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(stage),
            ),
            layers=[
                powertools_lambda_layer
            ]
        )

        # EventBridge rule for ContractStatusChange events
        events.Rule(
            self,
            "unicorn.properties-ContractStatusChanged",
            rule_name="unicorn.properties-ContractStatusChanged",
            description=f"ContractStatusChanged events published by the {UNICORN_NAMESPACES.CONTRACTS.value} service.",
            event_bus=event_bus,
            event_pattern={
                "source": [UNICORN_NAMESPACES.CONTRACTS],
                "detail_type": ["ContractStatusChanged"],
            },
            targets=[
                targets.LambdaFunction(
                    contract_status_changed_function,
                    dead_letter_queue=contract_status_changed_events_dlq,
                    retry_attempts=5,
                    max_event_age=Duration.minutes(15),
                )
            ],
        )

        # Lambda function that processes DynamoDB stream events from ContractStatusTable
        # to synchronize property approval states. This function:
        # - Listens to changes in contract status
        # - Processes the changes to update property approval workflows
        # - Handles failures using a Dead Letter Queue
        properties_approval_sync_function = lambda_.Function(
            self,
            f"PropertiesApprovalSyncFunction-{stage.value}",
            runtime=lambda_.Runtime.PYTHON_3_13,
            code=lambda_.Code.from_asset('src/'),
            handler='properties_service.properties_approval_sync_function.lambda_handler',
            environment={
                "TABLE_NAME": table.table_name,
                "STAGE": stage.value,
                "SERVICE_NAMESPACE": UNICORN_NAMESPACES.PROPERTIES.value,
            },
            dead_letter_queue=properties_service_dlq,
            # CloudWatch log group for the PropertiesApprovalSync function
            # Configured with stage-appropriate retention period
            log_group=logs.LogGroup(
                self,
                "PropertiesApprovalSyncFunctionLogGroup",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(stage),
            ),
            layers=[
                powertools_lambda_layer
            ]
        )

        # Allow Properties Approval Sync function to send messages to the Properties Service Dead Letter Queue
        properties_service_dlq.grant_send_messages(properties_approval_sync_function)
        # Allow Properties Approval Sync function to read data and stream data from Contract Status DynamoDB table
        table.grant_read_data(properties_approval_sync_function)
        table.grant_stream_read(properties_approval_sync_function)

        # CloudFormation output for Contracts table name
        StackHelper.create_output(
            self,
            {
                "name": self.property_approval_sync_function_iam_role_arn_parameter,
                "description": "Properties approvale sync function arn",
                "value": properties_approval_sync_function.role.role_arn,
                "stage": stage.value,
                "create_ssm_string_parameter": True,
            },
        )