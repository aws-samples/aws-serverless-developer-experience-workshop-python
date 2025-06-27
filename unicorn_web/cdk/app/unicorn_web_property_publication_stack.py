# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from dataclasses import dataclass
import json
from aws_cdk import (
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_eventschemas as eventschemas,
    aws_iam as iam,
    aws_lambda_nodejs as nodejs,
    aws_logs as logs,
    aws_sqs as sqs,
    aws_lambda_event_sources as lambda_event_sources,
    aws_lambda as lambda_,
    Stack,
    Duration,
    RemovalPolicy,
)
from constructs import Construct

from lib.helper import (
    get_default_logs_retention_period,
    StackHelper,
    STAGE,
    UNICORN_NAMESPACES,
)


@dataclass
class WebPropertyPublicationStackProps:
    """
    Properties for the WebPropertyPublicationStack
    """

    description: str
    stage: STAGE  # Deployment stage of the application
    event_bus_name: str  # Name of SSM Parameter that holds the EventBus for this service
    table_name: str  # Name of SSM Parameter that holds the DynamoDB table tracking property status
    rest_api_id: str  # Name of SSM Parameter that holds the RestApId of Web service's Rest Api
    rest_api_root_resource_id: str  # Name of SSM Parameter that holds the RootResourceId of Web service's Rest Api
    rest_api_url: str  # Name of SSM Parameter that holds the Url of Web service's Rest Api
    powertools_layer: lambda_.LayerVersion


class WebPropertyPublicationStack(Stack):
    """
    Stack that defines the Unicorn Web property publication infrastructure
    
    Example:
    ```python
    app = cdk.App()
    WebPropertyPublicationStack(app, 'WebPropertyPublicationStack',
        props=WebPropertyPublicationStackProps(
            stage=STAGE.DEV,
            # other required properties
        )
    )
    ```
    """
    
    # Current deployment stage of the application

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        props: WebPropertyPublicationStackProps,
        **kwargs,
    ):
        """
        Creates a new WebPropertyPublicationStack

        Parameters:
        - scope: The scope in which to define this construct
        - id: The scoped construct ID
        - props: Configuration properties

        Remarks:
        This stack creates:
        - DynamoDB table for data storage
        - API Gateway REST API
        - EventBridge event bus
        - Property publication Construct
        - Property eventing Construct
        - Associated IAM roles and permissions
        """
        super().__init__(scope, id)
        self.stage = props.stage

        # Add standard tags to the CloudFormation stack for resource organization
        # and cost allocation
        StackHelper.add_stack_tags(
            self,
            {
                "namespace": UNICORN_NAMESPACES.WEB,
                "stage": self.stage,
            },
        )

        # Import resources based on details from SSM Parameter Store
        # Create CDK references to these existing resources.
        event_bus = events.EventBus.from_event_bus_name(
            self,
            "WebEventBus",
            StackHelper.lookup_ssm_parameter(
                self, f"/uni-prop/{props.stage.value}/{props.event_bus_name}"
            ),
        )

        table = dynamodb.TableV2.from_table_name(
            self,
            "webTable",
            StackHelper.lookup_ssm_parameter(
                self, f"/uni-prop/{props.stage.value}/{props.table_name}"
            ),
        )

        api_url = StackHelper.lookup_ssm_parameter(
            self, f"/uni-prop/{props.stage.value}/{props.rest_api_url}"
        )

        api = apigateway.RestApi.from_rest_api_attributes(
            self,
            "webRestApi",
            rest_api_id=StackHelper.lookup_ssm_parameter(
                self, f"/uni-prop/{props.stage.value}/{props.rest_api_id}"
            ),
            root_resource_id=StackHelper.lookup_ssm_parameter(
                self, f"/uni-prop/{props.stage.value}/{props.rest_api_root_resource_id}"
            ),
        )

        # -------------------------------------------------------------------------- #
        #                                SQS QUEUES                                    #
        # -------------------------------------------------------------------------- #

        # Dead Letter Queue for failed ingestion messages
        # Store
        ingest_queue_dlq = sqs.Queue(
            self,
            "IngestDLQ",
            queue_name=f"IngestDLQ-{props.stage.value}",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Main approval request queue
        # Handles incoming property approval requests
        # Configured with DLQ for failed message handling
        approval_request_queue = sqs.Queue(
            self,
            f"ApprovalRequestQueue-{props.stage.value}",
            queue_name=f"ApprovalRequestQueue-{props.stage.value}",
            dead_letter_queue={
                "queue": ingest_queue_dlq,
                "max_receive_count": 1,
            },
            visibility_timeout=Duration.seconds(20),
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # CloudFormation output for ApprovalRequestQueue URL
        StackHelper.create_output(
            self,
            {
                "name": "ApprovalRequestQueueUrl",
                "description": "URL for the Ingest SQS Queue",
                "value": approval_request_queue.queue_url,
                "stage": props.stage.value,
            },
        )

        # -------------------------------------------------------------------------- #
        #                                IAM ROLES                                     #
        # -------------------------------------------------------------------------- #

        # IAM role for API Gateway to SQS integration
        # Allows API Gateway to send messages to the approval request queue
        api_integration_role = iam.Role(
            self,
            f"WebApiSqsIntegrationRole-{props.stage.value}",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
        )
        approval_request_queue.grant_send_messages(api_integration_role)

        # -------------------------------------------------------------------------- #
        #                               EVENT SCHEMA                                   #
        # -------------------------------------------------------------------------- #

        # Load the schema from the JSON file
        schema_path = os.path.join(
            os.path.dirname(__file__),
            "../../integration/PublicationApprovalRequested.json",
        )
        with open(schema_path, "r") as schema_file:
            publication_approval_requested_event_schema = json.load(schema_file)

        # Define and add the PublicationApprovalRequested event schema to
        # the Web's services EventBridge Schema Registry.
        eventschemas.CfnSchema(
            self,
            "PublicationApprovalRequestedEventSchema",
            type="OpenApi3",
            registry_name=f"{UNICORN_NAMESPACES.WEB.value}-{props.stage.value}",
            description="The schema for a request to publish a property",
            schema_name=f"{UNICORN_NAMESPACES.WEB.value}@PublicationApprovalRequested",
            content=json.dumps(publication_approval_requested_event_schema),
        )

        # -------------------------------------------------------------------------- #
        #                            LAMBDA FUNCTIONS                                  #
        # -------------------------------------------------------------------------- #

        # Dead Letter Queue for failed publication approval event handling
        publication_approvals_event_handler_dlq = sqs.Queue(
            self,
            "publicationApprovedEventHandlerDLQ",
            queue_name=f"publicationApprovalsEventHandlerDLQ-{props.stage.value}",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Lambda function to process queued API requests for property approval
        # Processes messages from the ApprovalRequestQueue and publishes events to EventBridge
        approval_request_function = lambda_.Function(
            self,
            f"RequestApprovalFunction-{props.stage.value}",
            runtime=lambda_.Runtime.PYTHON_3_13,
            code=lambda_.Code.from_asset("src/"),
            handler="approvals_service.request_aproval_function.lambda_handler",
            tracing=lambda_.Tracing.ACTIVE,
            log_group=logs.LogGroup(
                self,
                "RequestApprovalFunctionLogs",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(props.stage.value),
            ),
            environment={
                "DYNAMODB_TABLE": table.table_name,
                "SERVICE_NAMESPACE": UNICORN_NAMESPACES.WEB.value,
                "POWERTOOLS_LOGGER_CASE": "PascalCase",
                "POWERTOOLS_SERVICE_NAME": UNICORN_NAMESPACES.WEB.value,
                "POWERTOOLS_TRACE_DISABLED": "false",  # Explicitly disables tracing, default
                "POWERTOOLS_LOGGER_LOG_EVENT": str(
                    props.stage != STAGE.PROD
                ),  # Logs incoming event, default
                "POWERTOOLS_LOGGER_SAMPLE_RATE": (
                    "0" if props.stage == STAGE.PROD else "0.1"
                ),  # Debug log sampling percentage, default
                "POWERTOOLS_METRICS_NAMESPACE": UNICORN_NAMESPACES.WEB.value,
                "POWERTOOLS_LOG_LEVEL": "INFO",  # Log level for Logger (INFO, DEBUG, etc.), default
                "LOG_LEVEL": "INFO",  # Log level for Logger
            },
            layers=[props.powertools_layer],
            dead_letter_queue=publication_approvals_event_handler_dlq,
        )

        # Grant permissions to the approval request function
        event_bus.grant_put_events_to(approval_request_function)
        table.grant_read_data(approval_request_function)

        # Configure SQS event source for the approval request function
        # Processes messages in batches of 1 with maximum concurrency of 5
        approval_request_function.add_event_source(
            lambda_event_sources.SqsEventSource(
                approval_request_queue,
                batch_size=1,
                max_concurrency=5,
            )
        )

        # Lambda function to handle approved publication events
        # Processes PublicationEvaluationCompleted events and updates DynamoDB
        publication_approved_function = lambda_.Function(
            self,
            f"PublicationApprovedFunction-{props.stage.value}",
            runtime=lambda_.Runtime.PYTHON_3_13,
            code=lambda_.Code.from_asset("src/"),
            handler="approvals_service.publication_approval_function.lambda_handler",
            tracing=lambda_.Tracing.ACTIVE,
            log_group=logs.LogGroup(
                self,
                "PublicationApprovedLogs",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(props.stage.value),
            ),
            environment={
                "DYNAMODB_TABLE": table.table_name,
                "SERVICE_NAMESPACE": UNICORN_NAMESPACES.WEB.value,
                "POWERTOOLS_LOGGER_CASE": "PascalCase",
                "POWERTOOLS_SERVICE_NAME": UNICORN_NAMESPACES.WEB.value,
                "POWERTOOLS_TRACE_DISABLED": "false",  # Explicitly disables tracing, default
                "POWERTOOLS_LOGGER_LOG_EVENT": str(
                    props.stage != STAGE.PROD
                ),  # Logs incoming event, default
                "POWERTOOLS_LOGGER_SAMPLE_RATE": (
                    "0" if props.stage == STAGE.PROD else "0.1"
                ),  # Debug log sampling percentage, default
                "POWERTOOLS_METRICS_NAMESPACE": UNICORN_NAMESPACES.WEB.value,
                "POWERTOOLS_LOG_LEVEL": "INFO",  # Log level for Logger (INFO, DEBUG, etc.), default
                "LOG_LEVEL": "INFO",  # Log level for Logger
            },
            layers=[props.powertools_layer],
            dead_letter_queue=publication_approvals_event_handler_dlq,
        )
        table.grant_write_data(publication_approved_function)

        # CloudFormation Stack Outputs for publicationApprovedFunction
        StackHelper.create_output(
            self,
            {
                "name": "PublicationApprovedEventHandlerFunctionName",
                "value": publication_approved_function.function_name,
                "stage": props.stage.value,
            },
        )

        StackHelper.create_output(
            self,
            {
                "name": "PublicationApprovedEventHandlerFunctionArn",
                "value": publication_approved_function.function_arn,
                "stage": props.stage.value,
            },
        )

        # -------------------------------------------------------------------------- #
        #                                 EVENT RULES                                  #
        # -------------------------------------------------------------------------- #

        # EventBridge rule for publication evaluation events
        # Routes PublicationEvaluationCompleted events to the handler function
        events.Rule(
            self,
            "unicorn.web-PublicationEvaluationCompleted",
            rule_name="unicorn.web-PublicationEvaluationCompleted",
            description=f"PublicationEvaluationCompleted events published by the {UNICORN_NAMESPACES.PROPERTIES} service.",
            event_bus=event_bus,
            event_pattern={
                "source": [UNICORN_NAMESPACES.PROPERTIES],
                "detail_type": ["PublicationEvaluationCompleted"],
            },
        ).add_target(targets.LambdaFunction(publication_approved_function))

        # -------------------------------------------------------------------------- #
        #                           API GATEWAY INTEGRATION                            #
        # -------------------------------------------------------------------------- #

        # API Gateway integration with SQS
        # Configures the REST API to send messages to the approval request queue
        sqs_integration = apigateway.AwsIntegration(
            service="sqs",
            integration_http_method="POST",
            path=approval_request_queue.queue_name,
            options=dict(
                credentials_role=api_integration_role,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": '{"message":"OK"}',
                        },
                    )
                ],
                request_parameters={
                    "integration.request.header.Content-Type": "'application/x-www-form-urlencoded'"
                },
                passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
                request_templates={
                    "application/json": "Action=SendMessage&MessageBody=$input.body&MessageAttribute.1.Name=HttpMethod&MessageAttribute.1.Value.StringValue=$context.httpMethod&MessageAttribute.1.Value.DataType=String",
                },
            ),
        )

        # API Gateway method for requesting approval
        # Path: POST /request_approval
        # Integrates with SQS for asynchronous processing
        api.root.add_resource("request_approval").add_method(
            "POST",
            sqs_integration,
            method_responses=[apigateway.MethodResponse(status_code="200")],
        )

        # CloudFormation stack output for /request_approval path
        StackHelper.create_output(
            self,
            {
                "name": "ApiPropertyApproval",
                "description": "POST request to add a property to the database",
                "value": f"{api_url}request_approval",
                "stage": props.stage.value,
            },
        )

        deployment = apigateway.Deployment(
            self,
            "deployment",
            api=api,
            description="Unicorn Web API deployment",
            stage_name=props.stage.value,
        )
        deployment.node.add_dependency(api.root)
