# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
import json
from pathlib import Path
import aws_cdk as cdk
from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_sqs as sqs,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_logs as logs,
    aws_eventschemas as eventschemas,
    aws_lambda_nodejs as nodejs,
    aws_pipes as pipes,
    RemovalPolicy,
    Duration,
    Stack,
    CfnOutput,
    Tags,
    Aws,
)
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from constructs import Construct
from cdk_nag import NagSuppressions

from lib.helper import STAGE, UNICORN_NAMESPACES

# Load the JSON schema
with open(os.path.join(os.path.dirname(__file__), '../../integration/ContractStatusChangedEventSchema.json'), 'r') as f:
    ContractStatusChangedEventSchema = json.load(f)

class UnicornContractsStack(Stack):
    def __init__(self, scope: Construct, id: str, *, stage: STAGE, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Tag CloudFormation Stack
        Tags.of(self).add('namespace', UNICORN_NAMESPACES.CONTRACTS.value)
        Tags.of(self).add('stage', stage.value)
        Tags.of(self).add('project', 'AWS Serverless Developer Experience')

        # Set log retention period based on stage
        def logs_retention_period(stage_value):
            if stage_value == STAGE.LOCAL.value:
                return RetentionDays.ONE_DAY
            elif stage_value == STAGE.DEV.value:
                return RetentionDays.ONE_WEEK
            elif stage_value == STAGE.PROD.value:
                return RetentionDays.TWO_WEEKS
            else:
                return RetentionDays.ONE_DAY
                
        retention_period = logs_retention_period(stage)

        # -------------------------------------------------------------------------
        #                                EVENT BUS
        # -------------------------------------------------------------------------

        event_bus = events.EventBus(
            self,
            f"UnicornContractsBus-{stage.value}",
            event_bus_name=f"UnicornContractsBus-{stage.value}"
        )

        event_bus_policy = events.CfnEventBusPolicy(
            self,
            'ContractEventsBusPublishPolicy',
            statement_id=f'OnlyContractsServiceCanPublishToEventBus-{stage.value}',
            event_bus_name=event_bus.event_bus_name,
            statement=iam.PolicyStatement(
                actions=['events:PutEvents'],
                resources=[event_bus.event_bus_arn],
                principals=[iam.AccountRootPrincipal()],
                sid=f'OnlyContractsServiceCanPublishToEventBus-{stage.value}',
                conditions={
                    'StringEquals': {
                        "aws:Source": UNICORN_NAMESPACES.CONTRACTS.value
                    }
                }
            ).to_json()
        )

        # CloudWatch log group used to catch all events
        catch_all_log_group = logs.LogGroup(
            self, 
            'CatchAllLogGroup',
            log_group_name=f"/aws/events/{stage.value}/{UNICORN_NAMESPACES.CONTRACTS.value}-catchall",
            removal_policy=RemovalPolicy.DESTROY,
            retention=retention_period
        )

        # Catchall rule used for development purposes
        events.Rule(
            self, 
            'contracts.catchall',
            rule_name='contracts.catchall',
            description=f"Catch all events published by the {UNICORN_NAMESPACES.CONTRACTS.value} service.",
            event_bus=event_bus,
            event_pattern={
                "account": [self.account],
                "source": [UNICORN_NAMESPACES.CONTRACTS.value]
            },
            enabled=True,
            targets=[targets.CloudWatchLogGroup(catch_all_log_group)]
        )

        # Share Event bus Name through SSM
        ssm.StringParameter(
            self, 
            'UnicornContractsEventBusNameParam',
            parameter_name=f"/uni-prop/{stage.value}/UnicornContractsEventBus",
            string_value=event_bus.event_bus_name
        )

        # Share Event bus Arn through SSM
        ssm.StringParameter(
            self, 
            'UnicornContractsEventBusArnParam',
            parameter_name=f"/uni-prop/{stage.value}/UnicornContractsEventBusArn",
            string_value=event_bus.event_bus_arn
        )

        # -------------------------------------------------------------------------
        #                              DYNAMODB TABLE
        # -------------------------------------------------------------------------
        # Persist Contracts information in DynamoDB
        table = dynamodb.TableV2(
            self, 
            "ContractsTable",
            table_name=f"uni-prop-{stage.value}-contracts-ContractsTable",
            partition_key=dynamodb.Attribute(
                name="property_id",
                type=dynamodb.AttributeType.STRING
            ),
            dynamo_stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.DESTROY  # Be careful with this in production
        )

        # -------------------------------------------------------------------------
        #                            EVENT BRIDGE PIPES
        # -------------------------------------------------------------------------
        # Pipe to transform a changed Contracts table record to ContractStatusChanged and publish it via the UnicornContractsEventBus

        # Dead Letter Queue (DLQ) for the contract ingestion queue.
        # messages that fail processing after 1 attempt are moved here for investigation.
        # Messages are retained for 14 days (1,209,600 seconds).
        pipe_dlq = sqs.Queue(
            self, 
            'ContractsTableStreamToEventPipeDLQ',
            queue_name=f"ContractsTableStreamToEventPipeDLQ-{stage.value}",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            retention_period=Duration.days(14),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        NagSuppressions.add_resource_suppressions(
            pipe_dlq, 
            [
                {
                    "id": "AwsSolutions-SQS3",
                    "reason": "This queue is used as a DLQ and does not require its own DLQ."
                }
            ]
        )

        pipe_role = iam.Role(
            self,
            f"ContractsTableStreamToEventPipeRole-{stage.value}",
            description="IAM role for Pipe",
            assumed_by=iam.ServicePrincipal(
                "pipes.amazonaws.com"
            ).with_conditions({
                "StringEquals": {"aws:SourceAccount": Stack.of(self).account}
            })
        )

        pipe_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["dynamodb:ListStreams"],
                resources=["*"]
            )
        )
        
        pipe_dlq.grant_send_messages(pipe_role)
        table.grant_stream_read(pipe_role)
        event_bus.grant_put_events_to(pipe_role)

        contracts_table_stream_to_event_pipe_log_group = logs.LogGroup(
            self,
            'ContractsTableStreamToEventPipeLogGroup',
            log_group_name=f"/aws/pipe/{stage.value}/ContractsTableStreamToEventPipe",
            removal_policy=RemovalPolicy.DESTROY,
            retention=retention_period
        )

        pipes.CfnPipe(
            self, 
            'ContractsTableStreamToEventPipe',
            role_arn=pipe_role.role_arn,
            source=table.table_stream_arn,
            source_parameters={
                "dynamoDbStreamParameters": {
                    "maximumRetryAttempts": 3,
                    "deadLetterConfig": {
                        "arn": pipe_dlq.queue_arn
                    },
                    "startingPosition": "LATEST",
                    # "onPartialBatchItemFailure": "AUTOMATIC_BISECT",  # TO DO - Not implemented on SAM template
                    "batchSize": 1
                },
                "filterCriteria": {
                    "filters": [
                        {
                            "pattern": json.dumps({
                                "eventName": ["INSERT", "MODIFY"],
                                "dynamodb": {
                                    "NewImage": {
                                        "contract_status": {
                                            "S": ["DRAFT", "APPROVED"]
                                        }
                                    }
                                }
                            })
                        }
                    ]
                }
            },
            target=event_bus.event_bus_arn,
            target_parameters={
                "eventBridgeEventBusParameters": {
                    "source": UNICORN_NAMESPACES.CONTRACTS,
                    "detailType": "ContractStatusChanged"
                },
                "inputTemplate": json.dumps({
                    "property_id": "<$.dynamodb.Keys.property_id.S>",
                    "contract_id": "<$.dynamodb.NewImage.contract_id.S>",
                    "contract_status": "<$.dynamodb.NewImage.contract_status.S>",
                    "contract_last_modified_on": "<$.dynamodb.NewImage.contract_last_modified_on.S>"
                })
            },
            log_configuration={
                "cloudwatchLogsLogDestination": {
                    "logGroupArn": contracts_table_stream_to_event_pipe_log_group.log_group_arn
                },
                "level": "ERROR"
            }
        )

        # -------------------------------------------------------------------------
        #                            DEAD LETTER QUEUES
        # -------------------------------------------------------------------------
        # DeadLetterQueue for UnicornContractsIngestQueue. Contains messages that failed to be processed
        ingest_queue_dlq = sqs.Queue(
            self, 
            'UnicornContractsIngestDLQ',
            queue_name=f"UnicornContractsIngestDLQ-{stage.value}",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        # -------------------------------------------------------------------------
        #                               INGEST QUEUE
        # -------------------------------------------------------------------------
        # Queue API Gateway requests to be processed by ContractEventHandlerFunction
        ingest_queue = sqs.Queue(
            self, 
            'UnicornContractsIngestQueue',
            queue_name=f"UnicornContractsIngestQueue-{stage.value}",
            retention_period=Duration.days(14),
            dead_letter_queue=sqs.DeadLetterQueue(
                queue=ingest_queue_dlq,
                max_receive_count=1
            ),
            visibility_timeout=Duration.seconds(20),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        # -------------------------------------------------------------------------
        #                             LAMBDA FUNCTIONS
        # -------------------------------------------------------------------------
        # Processes customer API requests from SQS queue UnicornContractsIngestQueue
        event_handler_logs = logs.LogGroup(
            self,
            'UnicornContractEventsHandlerLogs',
            removal_policy=RemovalPolicy.DESTROY,
            retention=retention_period
        )

        contract_event_handler_lambda = lambda_.Function(
            self,
            f'UnicornContractEventHandlerFunction-{stage.value}',
            runtime=lambda_.Runtime.PYTHON_3_13,
            code=lambda_.Code.from_asset('src/'),
            handler='contracts_service.contract_event_handler.lambda_handler',
            tracing=lambda_.Tracing.ACTIVE,
            log_group=event_handler_logs,
            environment={
                'DYNAMODB_TABLE': table.table_name,
                'SERVICE_NAMESPACE': UNICORN_NAMESPACES.CONTRACTS.value,
                'POWERTOOLS_LOGGER_CASE': 'PascalCase',
                'POWERTOOLS_SERVICE_NAME': UNICORN_NAMESPACES.CONTRACTS.value,
                'POWERTOOLS_TRACE_DISABLED': 'false',  # Explicitly disables tracing, default
                'POWERTOOLS_LOGGER_LOG_EVENT': str(stage.value != "prod"), # Logs incoming event, default
                'POWERTOOLS_LOGGER_SAMPLE_RATE': "0" if stage.value == "prod" else "0.1",  # Debug log sampling percentage, default
                'POWERTOOLS_METRICS_NAMESPACE': UNICORN_NAMESPACES.CONTRACTS.value,
                'POWERTOOLS_LOG_LEVEL': 'INFO',  # Log level for Logger (INFO, DEBUG, etc.), default
                'LOG_LEVEL': 'INFO',  # Log level for Logger
            },
            layers=[
                lambda_.LayerVersion.from_layer_version_arn(
                    self,
                    'UnicornContractsLayer',
                    layer_version_arn=f'arn:aws:lambda:{Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-x86_64:4'
                    
                )
            ]
        )
        
        table.grant_read_write_data(contract_event_handler_lambda)
        ingest_queue.grant_consume_messages(contract_event_handler_lambda)
        contract_event_handler_lambda.add_event_source(
            SqsEventSource(ingest_queue, batch_size=1, max_concurrency=5)
        )

        # -------------------------------------------------------------------------
        #                            API GATEWAY REST API
        # -------------------------------------------------------------------------
        api_log_group = logs.LogGroup(
            self, 
            'UnicornContractsApiLogGroup',
            retention=retention_period,
            removal_policy=RemovalPolicy.DESTROY
        )

        api_role = iam.Role(
            self,
            f"UnicornContractsApiIntegrationRole-{stage.value}",
            assumed_by=iam.ServicePrincipal('apigateway.amazonaws.com')
        )
        
        ingest_queue.grant_send_messages(api_role)

        api = apigateway.RestApi(
            self, 
            'UnicornContractsApi',
            description='Unicorn Properties Contract Service API',
            cloud_watch_role=True,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
            endpoint_types=[apigateway.EndpointType.REGIONAL],
            deploy_options=apigateway.StageOptions(
                stage_name=stage,
                data_trace_enabled=True,
                tracing_enabled=True,
                metrics_enabled=True,
                logging_level=apigateway.MethodLoggingLevel.OFF,
                access_log_destination=apigateway.LogGroupLogDestination(api_log_group),
                access_log_format=apigateway.AccessLogFormat.custom(
                    json.dumps({
                        "requestId": apigateway.AccessLogField.context_request_id(),
                        "integration-error": apigateway.AccessLogField.context_integration_error_message(),
                        "integration-status": "$context.integration.status",
                        "integration-latency": apigateway.AccessLogField.context_integration_latency(),
                        "integration-request-id": apigateway.AccessLogField.context_aws_endpoint_request_id(),
                        "integration-integrationStatus": apigateway.AccessLogField.context_integration_status(),
                        "response-latency": apigateway.AccessLogField.context_response_latency(),
                        "status": apigateway.AccessLogField.context_status()
                    })
                ),
                method_options={
                    "/*/*": {
                        "throttling_rate_limit": 10,
                        "throttling_burst_limit": 100,
                        "logging_level": apigateway.MethodLoggingLevel.ERROR if stage.value == "prod" else apigateway.MethodLoggingLevel.INFO
                    }
                }
            )
        )

        # JSON Schema validation model for contract creation requests
        create_contract_model = api.add_model(
            'CreateContractModel',
            model_name='CreateContractModel',
            content_type='application/json',
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                type=apigateway.JsonSchemaType.OBJECT,
                required=['property_id', 'seller_name', 'address'],
                properties={
                    "property_id": {"type": apigateway.JsonSchemaType.STRING},
                    "seller_name": {"type": apigateway.JsonSchemaType.STRING},
                    "address": {
                        "type": apigateway.JsonSchemaType.OBJECT,
                        "required": ['city', 'country', 'number', 'street'],
                        "properties": {
                            "city": {"type": apigateway.JsonSchemaType.STRING},
                            "country": {"type": apigateway.JsonSchemaType.STRING},
                            "number": {
                                "type": apigateway.JsonSchemaType.INTEGER,
                                "format": "int32"
                            },
                            "street": {"type": apigateway.JsonSchemaType.STRING}
                        }
                    }
                }
            )
        )

        # Request validator for the CreateContractModel
        create_contract_validator = apigateway.RequestValidator(
            self,
            'CreateContractValidator',
            rest_api=api,
            request_validator_name='Validate CreateContract Body',
            validate_request_body=True
        )

        # JSON Schema validation model for contract update requests
        update_contract_model = api.add_model(
            'UpdateContractModel',
            model_name='UpdateContractModel',
            content_type='application/json',
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                type=apigateway.JsonSchemaType.OBJECT,
                required=['property_id'],
                properties={
                    "property_id": {"type": apigateway.JsonSchemaType.STRING}
                    # TO DO - Check SAM implementation. The Open API spec refers back to CreateContractModel specification
                }
            )
        )

        # Request validator for the UpdateContractModel
        update_contract_validator = apigateway.RequestValidator(
            self,
            'UpdateContractValidator',
            rest_api=api,
            request_validator_name='Validate Update Contract Body',
            validate_request_body=True
        )

        api_role.add_to_policy(
            iam.PolicyStatement(
                actions=['sqs:SendMessage', 'sqs:GetQueueUrl'],
                resources=[ingest_queue.queue_arn]
            )
        )

        contracts_api_resource = api.root.add_resource(
            'contracts',
            default_integration=apigateway.AwsIntegration(
                service='sqs',
                integration_http_method='POST',
                path=ingest_queue.queue_name,
                options=apigateway.IntegrationOptions(
                    credentials_role=api_role,
                    passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
                    integration_responses=[
                        apigateway.IntegrationResponse(
                            status_code='200',
                            response_templates={
                                'application/json': '{"message":"OK"}'
                            }
                        )
                    ],
                    request_templates={
                        'application/json': 'Action=SendMessage&MessageBody=$input.body&MessageAttribute.1.Name=HttpMethod&MessageAttribute.1.Value.StringValue=$context.httpMethod&MessageAttribute.1.Value.DataType=String'
                    },
                    request_parameters={
                        'integration.request.header.Content-Type': "'application/x-www-form-urlencoded'"
                    }
                )
            )
        )

        # Add POST method to /contracts with validation
        contracts_api_resource.add_method(
            'POST',
            request_validator=create_contract_validator,
            request_models={
                'application/json': create_contract_model
            },
            method_responses=[
                apigateway.MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': apigateway.Model.EMPTY_MODEL
                    }
                )
            ]
        )

        # Add PUT method to /contracts with validation
        contracts_api_resource.add_method(
            'PUT',
            request_validator=update_contract_validator,
            request_models={
                'application/json': update_contract_model
            },
            method_responses=[
                apigateway.MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': apigateway.Model.EMPTY_MODEL
                    }
                )
            ]
        )

        NagSuppressions.add_resource_suppressions(
            api,
            [
                {"id": "AwsSolutions-APIG2", "reason": "Validation not required"},
                {"id": "AwsSolutions-APIG3", "reason": "Does not require WAF"},
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "Authorization not implemented for this workshop."
                },
                {
                    "id": "AwsSolutions-COG4",
                    "reason": "Authorization not implemented for this workshop."
                }
            ],
            True
        )

        # -------------------------------------------------------------------------
        #                               Events Schema
        # -------------------------------------------------------------------------

        registry = eventschemas.CfnRegistry(
            self, 
            'EventRegistry',
            registry_name=f"{UNICORN_NAMESPACES.CONTRACTS.value}-{stage.value}",
            description=f"Event schemas for Unicorn Contracts {stage.value}"
        )

        registry_policy = eventschemas.CfnRegistryPolicy(
            self,
            'RegistryPolicy',
            registry_name=registry.attr_registry_name,
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        principals=[
                            iam.AccountPrincipal(Stack.of(self).account)
                        ],
                        actions=[
                            'schemas:DescribeCodeBinding',
                            'schemas:DescribeRegistry',
                            'schemas:DescribeSchema',
                            'schemas:GetCodeBindingSource',
                            'schemas:ListSchemas',
                            'schemas:ListSchemaVersions',
                            'schemas:SearchSchemas'
                        ],
                        resources=[
                            registry.attr_registry_arn,
                            f"arn:aws:schemas:{Stack.of(self).region}:{Stack.of(self).account}:schema/{registry.attr_registry_name}*"
                        ]
                    )
                ]
            )
        )

        contract_status_changed_schema = eventschemas.CfnSchema(
            self,
            'ContractStatusChangedEventSchema',
            type='OpenApi3',
            registry_name=registry.attr_registry_name,
            description='The schema for a request to publish a property',
            schema_name=f"{UNICORN_NAMESPACES.CONTRACTS.value}@ContractStatusChanged",
            content=json.dumps(ContractStatusChangedEventSchema)
        )
        
        registry_policy.node.add_dependency(contract_status_changed_schema)

        # -------------------------------------------------------------------------
        #                                 Subscribe
        # -------------------------------------------------------------------------

        # Allow event subscribers to create subscription rules on this event bus
        event_bus.add_to_resource_policy(
            iam.PolicyStatement(
                sid=f"AllowSubscribersToCreateSubscriptionRules-contracts-{stage.value}",
                effect=iam.Effect.ALLOW,
                principals=[iam.AccountRootPrincipal()],
                actions=['events:*Rule', 'events:*Targets'],
                resources=[event_bus.event_bus_arn],
                conditions={
                    "StringEqualsIfExists": {
                        "events:creatorAccount": Stack.of(self).account
                    }
                    # TO DO - Review if below are valid as they may not apply to PutRule/PutTargets as per https://aws.amazon.com/blogs/compute/simplifying-cross-account-access-with-amazon-eventbridge-resource-policies/
                    # "StringEquals": {
                    #     "event:source": [UNICORN_NAMESPACES.CONTRACTS]
                    # },
                    # "Null": {
                    #     "events:source": "false"
                    # }
                }
            )
        )

        NagSuppressions.add_resource_suppressions(
            [
                api_log_group,
                catch_all_log_group,
                contracts_table_stream_to_event_pipe_log_group,
                event_handler_logs
            ],
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Custom Resource to set Log Retention Policy"
                }
            ]
        )

        # -------------------------------------------------------------------------
        #                                  Outputs
        # -------------------------------------------------------------------------
        CfnOutput(
            self, 
            'ApiUrl',
            description='Web service API endpoint',
            value=api.url
        )

        CfnOutput(
            self, 
            'IngestQueueUrl',
            description='URL for the Ingest SQS Queue',
            value=ingest_queue.queue_url
        )

        CfnOutput(
            self, 
            'ContractsTableName',
            description='DynamoDB table storing contract information',
            value=table.table_name
        )

        CfnOutput(
            self, 
            'ContractEventHandlerFunctionName',
            description='ContractEventHandler function name',
            value=contract_event_handler_lambda.function_name
        )
        
        CfnOutput(
            self, 
            'ContractEventHandlerFunctionArn',
            description='ContractEventHandler function ARN',
            value=contract_event_handler_lambda.function_arn
        )

        CfnOutput(
            self, 
            'UnicornContractsEventBusName',
            value=event_bus.event_bus_name
        )

        CfnOutput(
            self, 
            'UnicornContractsCatchAllLogGroupArn',
            description="Log all events on the service's EventBridge Bus",
            value=catch_all_log_group.log_group_arn
        )
