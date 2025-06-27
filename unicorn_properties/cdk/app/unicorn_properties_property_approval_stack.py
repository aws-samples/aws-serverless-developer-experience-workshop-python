#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import json
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_eventschemas as eventschemas,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda_nodejs as nodejs,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_sqs as sqs,
    aws_ssm as ssm,
    aws_lambda as lambda_,
    aws_lambda_destinations as destinations,
    Aws,
)
from constructs import Construct

from lib.helper import (
    LambdaHelper,
    StackHelper,
    get_default_logs_retention_period,
    STAGE,
    UNICORN_NAMESPACES,
)


class PropertyApprovalStack(Stack):
    """
    Stack that implements the Property services's approval workflow infrastructure.

    This stack demonstrates advanced serverless patterns including:
    - Step Functions workflow orchestration
    - Event-driven architecture integration
    - Asynchronous approval processes
    - Integration with AI services for content moderation
    - Error handling and dead letter queues
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        stage: STAGE,
        event_bus_name: str,
        contract_status_table_name: str,
        property_approval_sync_function_iam_role_arn: str,
        **kwargs,
    ):
        """
        Creates a new UnicornPropertiesStack
        
        Args:
            scope: The scope in which to define this construct
            id: The scoped construct ID
            stage: Deployment stage of the application
            event_bus_name: Name of SSM Parameter containing this service's Event Bus name
            contract_status_table_name: Name of SSM Parameter containing the DynamoDB table
            property_approval_sync_function_iam_role_arn: Name of SSM Parameter containing the IAM role ARN
            
        Remarks:
        This stack creates:
        - EventBridge event bus through Events Construct
        - Contracts Construct with associated DynamoDB table
        - Property Approval Construct integrated with Contracts
        - Associated IAM roles and permissions
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

        # Import resources based on details from SSM Parameter Store
        # Create CDK references to these existing resources.
        event_bus = events.EventBus.from_event_bus_name(
            self,
            "PropertiesEventBus",
            StackHelper.lookup_ssm_parameter(
                self, f"/uni-prop/{stage.value}/{event_bus_name}"
            ),
        )

        table = dynamodb.TableV2.from_table_name(
            self,
            "ContractStatusTable",
            StackHelper.lookup_ssm_parameter(
                self,
                f"/uni-prop/{stage.value}/{contract_status_table_name}",
            ),
        )

        approval_sync_function_iam_role_arn = StackHelper.lookup_ssm_parameter(
            self,
            f"/uni-prop/{stage.value}/{property_approval_sync_function_iam_role_arn}",
        )
        task_response_function_role = iam.Role.from_role_arn(
            self,
            "taskResponseFunctionRole",
            approval_sync_function_iam_role_arn,
            default_policy_name="workflowPermissions",
        )

        powertools_lambda_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            'UnicornPropertiesApprovalStackPowerToolsLayer',
            layer_version_arn=f'arn:aws:lambda:{Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-x86_64:4'
        )

        # --------------------------------------------------------------------------
        #                              LAMBDA FUNCTION
        # --------------------------------------------------------------------------

        # Lambda function to handle contract approval workflow
        # Updates the Property Item in DynamoDB Table with the
        # Step Function Task Token used to resume workflow.
        wait_for_contract_approval_function = lambda_.Function(
            self,
            f"WaitForContractApprovalFunction-{stage.value}",
            runtime=lambda_.Runtime.PYTHON_3_13,
            code=lambda_.Code.from_asset('src/'),
            handler='properties_service.wait_for_contract_approval_function.lambda_handler',
            environment={
                "TABLE_NAME": table.table_name,
                "STAGE": stage.value,
                "SERVICE_NAMESPACE": UNICORN_NAMESPACES.PROPERTIES.value,
            },
            log_group=logs.LogGroup(
                self,
                "WaitForContractApprovalFunctionLogGroup",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(stage),
            ),
            layers=[
                powertools_lambda_layer
            ]
        )

        # Grant permissions
        table.grant_read_write_data(wait_for_contract_approval_function)

        # CloudFormation outputs for Lambda function details
        # Useful for cross-stack references and operational monitoring
        StackHelper.create_output(
            self,
            {
                "name": "WaitForContractApprovalFunctionName",
                "value": wait_for_contract_approval_function.function_name,
                "stage": stage.value,
            },
        )
        StackHelper.create_output(
            self,
            {
                "name": "WaitForContractApprovalFunctionArn",
                "value": wait_for_contract_approval_function.function_arn,
                "stage": stage.value,
            },
        )

        # --------------------------------------------------------------------------
        #                              STATE MACHINE
        # --------------------------------------------------------------------------

        # Step Functions state machine for property approval workflow
        #
        # Implements a complex approval workflow demonstrating:
        # - Content moderation using AI services (Rekognition, Comprehend)
        # - Human approval task integration
        # - Parallel processing of approval tasks
        # - Error handling and recovery
        # - Event-driven status updates
        #
        # The workflow coordinates:
        # - Image analysis and moderation
        # - Text content review
        # - Contract status verification
        # - Manual approval processes
        # - Status event publication

        # Looks up the existing bucket containing our images's bucket name
        images_bucket_name = ssm.StringParameter.value_for_typed_string_parameter_v2(
            self, f"/uni-prop/{stage.value}/ImagesBucket", ssm.ParameterValueType.STRING
        )

        # CloudWatch log group for Step Functions state machine
        # Captures execution logs for debugging and monitoring
        state_machine_log_group = logs.LogGroup(
            self,
            "ApprovalStateMachineLogGroup",
            log_group_name=f"/aws/vendedlogs/states/uni-prop-{stage.value}-{UNICORN_NAMESPACES.PROPERTIES.value}-ApprovalStateMachine",
            retention=get_default_logs_retention_period(stage),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Step Functions state machine for property approval workflow
        # Orchestrates the end-to-end approval process
        state_machine = sfn.StateMachine(
            self,
            "ApprovalStateMachine",
            state_machine_name=f"{Stack.of(self).stack_name}-ApprovalStateMachine",
            definition_body=sfn.DefinitionBody.from_file(
                os.path.join(
                    os.path.dirname(__file__),
                    "../../src/state_machine/property_approval.asl.yaml",
                )
            ),
            definition_substitutions={
                "WaitForContractApprovalArn": wait_for_contract_approval_function.function_arn,
                "TableName": table.table_name,
                "ImageUploadBucketName": images_bucket_name,
                "EventBusName": event_bus.event_bus_name,
                "ServiceName": UNICORN_NAMESPACES.PROPERTIES,
            },
            tracing_enabled=True,
            logs=sfn.LogOptions(
                level=sfn.LogLevel.ALL,
                include_execution_data=True,
                destination=state_machine_log_group,
            ),
            role=iam.Role(
                self,
                "StateMachineRole",
                assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AWSXRayDaemonWriteAccess"
                    ),
                    iam.ManagedPolicy.from_aws_managed_policy_name(
                        "ComprehendFullAccess"
                    ),
                    iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AmazonRekognitionFullAccess"
                    ),
                ],
                inline_policies={
                    "CloudWatchPublishLogsMetrics": iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                actions=[
                                    "logs:CreateLogDelivery",
                                    "logs:GetLogDelivery",
                                    "logs:UpdateLogDelivery",
                                    "logs:DeleteLogDelivery",
                                    "logs:ListLogDeliveries",
                                    "logs:PutResourcePolicy",
                                    "logs:DescribeResourcePolicies",
                                    "logs:DescribeLogGroups",
                                    "cloudwatch:PutMetricData",
                                ],
                                resources=["*"],
                            ),
                        ]
                    ),
                    "S3ReadPolicy": iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                actions=["s3:Get*"],
                                resources=[f"arn:aws:s3:::{images_bucket_name}/*"],
                            ),
                        ]
                    ),
                },
            ),
        )

        # Grant permissions for state machine
        state_machine.grant_task_response(task_response_function_role)
        table.grant_read_data(state_machine)
        event_bus.grant_put_events_to(state_machine)
        wait_for_contract_approval_function.grant_invoke(state_machine)

        # --------------------------------------------------------------------------
        #                              EVENT HANDLING
        # --------------------------------------------------------------------------

        # Dead Letter Queue for failed EventBridge to Step Functions workflow events
        # Captures events that fail to be delivered to the state machine
        workflow_events_dlq = sqs.Queue(
            self,
            "WorkflowEventsDlq",
            queue_name=f"WorkflowEventsDlq-{stage.value}",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # EventBridge rule for publication approval requests
        # Triggers the approval workflow state machine
        events.Rule(
            self,
            "unicorn.properties-PublicationApprovalRequested",
            rule_name="unicorn.properties-PublicationApprovalRequested",
            description=f"PublicationApprovalRequested events published by the {UNICORN_NAMESPACES.WEB.value} service.",
            event_bus=event_bus,
            event_pattern={
                "source": [UNICORN_NAMESPACES.WEB.value],
                "detail_type": ["PublicationApprovalRequested"],
            },
            targets=[
                targets.SfnStateMachine(
                    state_machine,
                    dead_letter_queue=workflow_events_dlq,
                    retry_attempts=5,
                    max_event_age=Duration.minutes(15),
                ),
            ],
        )

        # Publication Evaluation Completed Event Schema
        #
        # Defines the contract for property publication workflow events:
        # - Ensures consistent event structure
        # - Enables strong typing for consumers
        # - Facilitates service integration testing
        #
        # This schema is used to validate events at runtime and generate
        # type-safe code bindings for consumers.
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "../../integration/PublicationEvaluationCompleted.json",
            )
        ) as f:
            publication_evaluation_completed_event_schema = json.load(f)

        eventschemas.CfnSchema(
            self,
            "PublicationEvaluationCompletedSchema",
            type="OpenApi3",
            registry_name=f"{UNICORN_NAMESPACES.PROPERTIES.value}-{stage.value}",
            description="The schema for when a property evaluation is completed",
            schema_name=f"{UNICORN_NAMESPACES.PROPERTIES.value}@PublicationEvaluationCompleted",
            content=json.dumps(publication_evaluation_completed_event_schema),
        )

        # CloudFormation outputs for state machine resources
        # Enables operational monitoring and cross-stack references
        StackHelper.create_output(
            self,
            {
                "name": "ApprovalStateMachineLogGroupName",
                "value": state_machine_log_group.log_group_name,
                "stage": stage.value,
            },
        )
        StackHelper.create_output(
            self,
            {
                "name": "ApprovalStateMachineName",
                "value": state_machine.state_machine_name,
                "stage": stage.value,
            },
        )
        StackHelper.create_output(
            self,
            {
                "name": "ApprovalStateMachineArn",
                "value": state_machine.state_machine_arn,
                "stage": stage.value,
            },
        )
