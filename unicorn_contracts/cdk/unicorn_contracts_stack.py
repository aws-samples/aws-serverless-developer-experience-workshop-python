
from aws_cdk import (
    Aws,
    Stack,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from aws_cdk.aws_pipes import CfnPipe
from aws_cdk.aws_eventschemas import CfnSchema
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from constructs import Construct
from pathlib import Path
from unicorn_shared import (
    UNICORN_NAMESPACES,
    STAGE,
    logsRetentionPeriod,
    eventBusName,
    isProd
)
from event_schema import EventsSchemaConstruct
from subscriber_policies import SubscriberPoliciesConstruct

import json
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_logs as logs
import aws_cdk.aws_iam as iam
import aws_cdk.aws_ssm as ssm
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_apigateway as apigateway


class UnicornConstractsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, *, stage: STAGE, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        retention_period = logsRetentionPeriod(stage)

        event_bus = events.EventBus(
            self,
            id=f'UnicornContractsBus-{stage.value}',
            event_bus_name=eventBusName(stage, UNICORN_NAMESPACES.CONTRACTS)
        )

        catch_all_log_group = logs.LogGroup(
            self, 'CatchAllLogGroup',
            log_group_name=f"/aws/events/{stage.value}/{UNICORN_NAMESPACES.CONTRACTS.value}-catchall",
            removal_policy=RemovalPolicy.DESTROY,
            retention=retention_period
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

        # Create a Catchall rule used for development purposes.
        catch_all_rule = events.Rule(
            self,
            'contracts.catchall',
            description='Catch all events published by the contracts service.',
            event_bus=event_bus,
            event_pattern={'account': [f'{Aws.ACCOUNT_ID}']},

            rule_name=f'{UNICORN_NAMESPACES.CONTRACTS.value}-catchall',
            enabled=True
        )
        catch_all_rule.add_target(
            targets.CloudWatchLogGroup(catch_all_log_group)
        )

        # Share Event bus through SSM
        ssm.StringParameter(
            self,
            'UnicornContractsEventBusParam',
            parameter_name=f'/uni-prop/{stage.value}/UnicornContractsEventBus',
            string_value=event_bus.event_bus_name,
        )

        ssm.StringParameter(
            self,
            'UnicornContractsEventBusArnParam',
            parameter_name=f'/uni-prop/{stage.value}/UnicornContractsEventBusArn',
            string_value=event_bus.event_bus_arn,
        )

        # --------------------------------------------------------------------------
        #                               DYNAMODB TABLE                              
        # --------------------------------------------------------------------------
        # Persist Contracts information in DynamoDB
        table = dynamodb.TableV2(
            self,
            'ContractsTable',
            table_name=f'uni-prop-{stage.value}-contracts-ContractsTable',
            partition_key={
                'name': 'property_id',
                'type': dynamodb.AttributeType.STRING},
            removal_policy=RemovalPolicy.DESTROY,
            dynamo_stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )

        # --------------------------------------------------------------------------
        #                             EVENT BRIDGE PIPES                            
        # --------------------------------------------------------------------------
        # Pipe to transform a changed Contracts table record to ContractStatusChanged and publish it via the UnicornContractsEventBus

        pipe_DLQ = sqs.Queue(
            self,
            'ContractsTableStreamToEventPipeDLQ',
            removal_policy=RemovalPolicy.DESTROY,
            retention_period=Duration.days(14),
            queue_name=f'ContractsTableStreamToEventPipeDLQ-{stage.value}'
        )

        pipe_role = iam.Role(
            self,
            'pipe-role', 
            assumed_by=iam.ServicePrincipal('pipes.amazonaws.com')
        )

        pipe_DLQ.grant_send_messages(pipe_role)
        table.grant_stream_read(pipe_role)
        event_bus.grant_put_events_to(pipe_role)

        CfnPipe(
            self,
            'ContractsTableStreamToEventPipe',
            role_arn=pipe_role.role_arn,
            source=table.table_stream_arn,

            source_parameters=CfnPipe.PipeSourceParametersProperty(
                dynamo_db_stream_parameters=CfnPipe.PipeSourceDynamoDBStreamParametersProperty(
                    maximum_retry_attempts=3,
                    dead_letter_config=CfnPipe.DeadLetterConfigProperty(
                        arn=pipe_DLQ.queue_arn
                    ),
                    starting_position='LATEST',
                    on_partial_batch_item_failure='AUTOMATIC_BISECT',
                    batch_size=1,
                ),
                filter_criteria=CfnPipe.FilterCriteriaProperty(
                    filters=[CfnPipe.FilterProperty(
                        pattern=json.dumps({
                            'eventName': ['INSERT', 'MODIFY'],
                            'dynamodb': {
                                'NewImage': {
                                    'contract_status': {
                                        'S': ['DRAFT', 'APPROVED'],
                                    },
                                },
                            }
                        }))
                    ])
            ),
            target=event_bus.event_bus_arn,
            target_parameters=CfnPipe.PipeTargetParametersProperty(
                event_bridge_event_bus_parameters=CfnPipe.PipeTargetEventBridgeEventBusParametersProperty(
                    source=UNICORN_NAMESPACES.CONTRACTS.value,
                    detail_type='ContractStatusChanged'
                ),
                input_template=json.dumps({
                    'property_id': '<$.dynamodb.NewImage.property_id.S>',
                    'contract_id': '<$.dynamodb.NewImage.contract_id.S>',
                    'contract_status': '<$.dynamodb.NewImage.contract_status.S>',
                    'contract_last_modified_on':
                        '<$.dynamodb.NewImage.contract_last_modified_on.S>',
                })
            )
        )

        # --------------------------------------------------------------------------
        #                             DEAD LETTER QUEUES                            
        # --------------------------------------------------------------------------
        # DeadLetterQueue for UnicornContractsIngestQueue. Contains messages that failed to be processed
        ingest_queue_DLQ = sqs.Queue(
            self,
            'UnicornContractsIngestDLQ',
            removal_policy=RemovalPolicy.DESTROY,
            retention_period=Duration.days(14),
            queue_name=f'UnicornContractsIngestQueueDLQ-{stage.value}'
        )

        # --------------------------------------------------------------------------
        #                                INGEST QUEUE                               
        # --------------------------------------------------------------------------
        # Queue API Gateway requests to be processed by ContractEventHandlerFunction
        ingest_queue = sqs.Queue(
            self,
            'UnicornContractsIngestQueue',
            removal_policy=RemovalPolicy.DESTROY,
            retention_period=Duration.days(14),
            queue_name=f'UnicornContractsIngestQueue-{stage.value}',
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=1,
                queue=ingest_queue_DLQ
            ),
            visibility_timeout=Duration.seconds(20)
        )

        # --------------------------------------------------------------------------
        #                              LAMBDA FUNCTIONS                             
        # --------------------------------------------------------------------------
        # Processes customer API requests from SQS queue UnicornContractsIngestQueue
        event_handler_logs = logs.LogGroup(
            self,
            'UnicornContractEventHandlerLogs',
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
                'POWERTOOLS_LOGGER_LOG_EVENT': 'false' if isProd(stage) else 'true', # Logs incoming event, default
                'POWERTOOLS_LOGGER_SAMPLE_RATE': '0.1' if isProd(stage) else '0',  # Debug log sampling percentage, default
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
        event_handler_logs.grant_write(contract_event_handler_lambda)
        table.grant_read_write_data(contract_event_handler_lambda)
        ingest_queue.grant_consume_messages(contract_event_handler_lambda)
        contract_event_handler_lambda.add_event_source(
            SqsEventSource(ingest_queue, batch_size=1, max_concurrency=5)
        )
        # --------------------------------------------------------------------------
        #                            API GATEWAY REST API                           
        # --------------------------------------------------------------------------
        api_logs = logs.LogGroup(
            self, 
            'UnicornContractsApiLogGroup',
            removal_policy=RemovalPolicy.DESTROY,
            retention=retention_period,
        )

        api_role = iam.Role(
            self,
            'UnicornContractsApiIntegrationRole',
            role_name='UnicornContractsApiIntegrationRole',
            assumed_by=iam.ServicePrincipal('apigateway.amazonaws.com'),
        )
        ingest_queue.grant_send_messages(api_role)

        api = apigateway.RestApi(
            self,
            'UnicornContractsApi',
            cloud_watch_role=True,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
            deploy_options=apigateway.StageOptions(
                stage_name=stage.value,
                data_trace_enabled=True,
                tracing_enabled=True,
                metrics_enabled=True,
                access_log_destination=apigateway.LogGroupLogDestination(api_logs),
                method_options={
                    '/*/*': {
                        'loggingLevel': apigateway.MethodLoggingLevel.ERROR if isProd(stage) else apigateway.MethodLoggingLevel.INFO,
                    },
                },
            ),
            endpoint_types=[apigateway.EndpointType.REGIONAL],
        )

        api_role.add_to_policy(
            iam.PolicyStatement(
                actions=['sqs:SendMessage', 'sqs:GetQueueUrl'],
                resources=[ingest_queue.queue_arn],
            )
        )

        sqs_integration = apigateway.AwsIntegration(
            service='sqs',
            region=Aws.REGION,
            integration_http_method='POST',
            path=ingest_queue.queue_name,
            options=apigateway.IntegrationOptions(
                credentials_role=api_role,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code='200',
                        response_templates={
                            'application/json': '{"message":"OK"}',
                        },
                    ),
                ],
                request_parameters={
                    'integration.request.header.Content-Type':
                        "'application/x-www-form-urlencoded'",
                },
                passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
                request_templates={
                    'application/json':
                        'Action=SendMessage&MessageBody=$input.body&MessageAttribute.1.Name=HttpMethod&MessageAttribute.1.Value.StringValue=$context.httpMethod&MessageAttribute.1.Value.DataType=String',
                },
            ),
        )

        contracts_api_resource = api.root.add_resource('contracts')

        contracts_api_resource.add_method(
            'POST',
            sqs_integration,
            method_responses=[apigateway.MethodResponse(status_code='200')]
        )

        contracts_api_resource.add_method(
            'PUT',
            sqs_integration,
            method_responses=[apigateway.MethodResponse(status_code='200')]
        )

        # --------------------------------------------------------------------------
        #                                Events Schema                              
        # --------------------------------------------------------------------------
        event_registry_name = f'{UNICORN_NAMESPACES.CONTRACTS.value}-{stage.value}'

        contract_status_changed_event_schema = Path(__file__).parent.parent.joinpath('integration/ContractStatusChangedEventSchema.json').read_text()
        contract_status_changed_schema = CfnSchema(
            self,
            'ContractStatusChangedEventSchema',
            type='OpenApi3',
            registry_name=event_registry_name,
            description='The schema for a request to publish a property',
            schema_name=f'{event_registry_name}@ContractStatusChanged',
            content=contract_status_changed_event_schema
        )

        EventsSchemaConstruct(
            self,
            f'uni-prop-{stage.value}-contracts-EventSchemaStack',
            name=event_registry_name,
            namespace=UNICORN_NAMESPACES.CONTRACTS.value,
            schemas=[contract_status_changed_schema],
        )

        # --------------------------------------------------------------------------
        #                                  Subscribe                                
        # --------------------------------------------------------------------------
        SubscriberPoliciesConstruct(
            self,
            f'uni-prop-{stage.value}-contracts-SubscriptionsStack',
            stage=stage,
            event_bus=event_bus,
            sources=[UNICORN_NAMESPACES.CONTRACTS]
        )

        # --------------------------------------------------------------------------
        #                                   Outputs                                 
        # --------------------------------------------------------------------------
        CfnOutput(
            self,
            'ApiUrl',
            description='Web service API endpoint',
            value=api.url,
        )

        CfnOutput(
            self,
            'IngestQueueUrl',
            description='URL for the Ingest SQS Queue',
            value=ingest_queue.queue_url,
        )

        CfnOutput(
            self,
            'ContractsTableName',
            description='DynamoDB table storing contract information',
            value=table.table_name,
        )

        CfnOutput(
            self,
            'ContractEventHandlerFunctionName',
            description='ContractEventHandler function name',
            value=contract_event_handler_lambda.function_name,
        )

        CfnOutput(
            self,
            'ContractEventHandlerFunctionArn',
            description='ContractEventHandler function ARN',
            value=contract_event_handler_lambda.function_arn,
        )

        CfnOutput(
            self,
            'UnicornContractsEventBusName',
            value=event_bus.event_bus_name,
        )

        CfnOutput(
            self,
            'UnicornContractsCatchAllLogGroupArn',
            description="Log all events on the service's EventBridge Bus",
            value=catch_all_log_group.log_group_arn,
        )
