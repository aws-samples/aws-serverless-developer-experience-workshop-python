from aws_cdk import (
    Aws,
    Duration,
    Stack,
    RemovalPolicy,
    CfnOutput,
)
from aws_cdk.aws_eventschemas import CfnSchema
from pathlib import Path

from unicorn_shared import (
    STAGE,
    UNICORN_NAMESPACES,
    logsRetentionPeriod,
    eventBusName,
    isProd,
)
from unicorn_shared.constructs import (
    DefaultLambdaFunctionConstruct,
    EventsSchemaConstruct,
    SubscriberPoliciesConstruct,
)

from constructs import Construct

import aws_cdk.aws_apigateway as apigateway
import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_logs as logs
import aws_cdk.aws_iam as iam
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_lambda_event_sources as eventsources


class UnicornWebStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, *, stage: STAGE, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        retention_period = logsRetentionPeriod(stage)

        event_bus = events.EventBus(
            self,
            id=f'UnicornWebBus-{stage.value}',
            event_bus_name=eventBusName(stage, UNICORN_NAMESPACES.WEB)
        )

        catch_all_log_group = logs.LogGroup(
            self, 'UnicornWebCatchAllLogGroup',
            log_group_name=f"/aws/events/{stage.value}/{UNICORN_NAMESPACES.WEB.value}-catchall",
            removal_policy=RemovalPolicy.DESTROY,
            retention=retention_period
        )

        event_bus_policy = events.CfnEventBusPolicy(
            self,
            'UnicornWebEventsBusPublishPolicy',
            statement_id=f'OnlyWebServiceCanPublishToEventBus-{stage.value}',
            event_bus_name=event_bus.event_bus_name,
            statement=iam.PolicyStatement(
                actions=['events:PutEvents'],
                resources=[event_bus.event_bus_arn],
                principals=[iam.AccountRootPrincipal()],
                sid=f'OnlyWebServiceCanPublishToEventBus-{stage.value}',
                conditions={
                    'StringEquals': {
                        "aws:Source": UNICORN_NAMESPACES.WEB.value
                    }
                }
            ).to_json()
        )

         # Create a Catchall rule used for development purposes.
        catch_all_rule = events.Rule(
            self,
            'UnicornWebCatchAllRule',
            description='Catch all events published by the web service.',
            event_bus=event_bus,
            event_pattern={
                'source': [
                    UNICORN_NAMESPACES.CONTRACTS.value,
                    UNICORN_NAMESPACES.PROPERTIES.value,
                    UNICORN_NAMESPACES.WEB.value
                ],
                'account': [f'{Aws.ACCOUNT_ID}']
            },

            rule_name=f'{UNICORN_NAMESPACES.WEB.value}-catchall',
            enabled=True
        )
        catch_all_rule.add_target(
            targets.CloudWatchLogGroup(catch_all_log_group)
        )

        # --------------------------------------------------------------------------
        #                               DYNAMODB TABLE                              
        # --------------------------------------------------------------------------
        table = dynamodb.TableV2(
            self,
            'ContractStatusTable',
            table_name=f'uni-prop-{stage.value}-contracts-WebTable',
            partition_key={
                'name': 'PK',
                'type': dynamodb.AttributeType.STRING},
            sort_key={
                'name': 'SK',
                'type': dynamodb.AttributeType.STRING},
            removal_policy=RemovalPolicy.DESTROY,
            dynamo_stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )

        # --------------------------------------------------------------------------
        #                             DEAD LETTER QUEUES                            
        # --------------------------------------------------------------------------
        # DeadLetterQueue for UnicornWebIngestQueue. Contains messages that failed to be processed
        ingest_queue_DLQ = sqs.Queue(
            self,
            'UnicornWebIngestDLQ',
            removal_policy=RemovalPolicy.DESTROY,
            retention_period=Duration.days(14),
            queue_name=f'UnicornWebIngestDLQ-{stage.value}'
        )

        # --------------------------------------------------------------------------
        #                             INGEST QUEUES                            
        # --------------------------------------------------------------------------
        # Queue API Gateway requests to be processed by RequestApprovalFunction
        ingest_queue = sqs.Queue(
            self,
            'UnicornWebIngestQueue',
            removal_policy=RemovalPolicy.DESTROY,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=1,
                queue=ingest_queue_DLQ
            ),
            queue_name=f'UnicornWebIngestQueue-{stage.value}',
            visibility_timeout=Duration.seconds(30),
        )
        
        # --------------------------------------------------------------------------
        #                             LAMBDA FUNCTIONS
        # --------------------------------------------------------------------------
        # Lambda function to handle contract status changes
        search_function = DefaultLambdaFunctionConstruct(
            self,
            f'SearchFunction-{stage.value}',
            handler='search_service.property_search_function.lambda_handler',
            stage=stage,
            namespace=UNICORN_NAMESPACES.WEB,
            log_group=logs.LogGroup(
                self,
                f'SearchFunctionLogGroup-{stage.value}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=retention_period
            ),
            environment={
                'DYNAMODB_TABLE': table.table_name,
            },
        )
        table.grant_read_data(search_function)

        # Process queued API requests to approve properties from UnicornWebIngestQueue
        request_approval_function = DefaultLambdaFunctionConstruct(
            self,
            f'RequestApprovalFunction-{stage.value}',
            handler='approvals_service.request_approval_function.lambda_handler',
            stage=stage,
            namespace=UNICORN_NAMESPACES.WEB,
            log_group=logs.LogGroup(
                self,
                f'RequestApprovalFunctionLogs-{stage.value}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=retention_period
            ),
            environment={
                'DYNAMODB_TABLE': table.table_name,
                'EVENT_BUS': event_bus.event_bus_name,
            },
        )
        event_bus.grant_put_events_to(request_approval_function)
        table.grant_read_data(request_approval_function)
        request_approval_function.add_event_source(
            eventsources.SqsEventSource(ingest_queue, batch_size=1, max_concurrency=5)
        )

        publication_approved_event_handler_function = DefaultLambdaFunctionConstruct(
            self,
            f'PublicationApprovedEventHandler-{stage.value}',
            handler='approvals_service.publication_approved_event_handler.lambda_handler',
            stage=stage,
            namespace=UNICORN_NAMESPACES.WEB,
            log_group=logs.LogGroup(
                self,
                f'PublicationApprovedEventHandlerFunctionLogGroup-{stage.value}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=retention_period
            ),
            environment={
                'DYNAMODB_TABLE': table.table_name,
                'EVENT_BUS': event_bus.event_bus_name,
            },
        )
        table.grant_write_data(publication_approved_event_handler_function)
        events.Rule(
            self,
            f'PublicationApprovedEventRule-{stage.value}',
            rule_name='unicorn.web-PublicationEvaluationCompleted',
            event_bus=event_bus,
            event_pattern={
                'detail': {
                    'source': [UNICORN_NAMESPACES.PROPERTIES.value],
                    'detailType': ['PublicationEvaluationCompleted']
                }
            },
            targets=[
                targets.LambdaFunction(publication_approved_event_handler_function)
            ]
        )

        # --------------------------------------------------------------------------
        #                             API GATEWAY - REST API
        # --------------------------------------------------------------------------
        api_logs = logs.LogGroup(
            self,
            f'UnicornWebApiLogGroup-{stage.value}',
            removal_policy=RemovalPolicy.DESTROY,
            retention=retention_period
        )

        api_role = iam.Role(
            self,
            'UnicornWebApiIntegrationRole',
            assumed_by=iam.ServicePrincipal('apigateway.amazonaws.com'),
        )
        ingest_queue.grant_send_messages(api_role)
        search_function.grant_invoke(api_role)

        api = apigateway.RestApi(
            self,
            f'UnicornWebApi-{stage.value}',
            cloud_watch_role=True,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
            deploy_options=apigateway.StageOptions(
                stage_name=f'{stage.value}',
                data_trace_enabled=True,
                tracing_enabled=True,
                metrics_enabled=True,
                access_log_destination=apigateway.LogGroupLogDestination(api_logs),
                method_options={
                    '/*/*': apigateway.MethodDeploymentOptions(
                        logging_level=apigateway.MethodLoggingLevel.ERROR if isProd(stage) else apigateway.MethodLoggingLevel.INFO,
                    )
                },
            ),
            endpoint_types=[apigateway.EndpointType.REGIONAL],
        )

        sqs_integration = apigateway.AwsIntegration(
            service='sqs',
            region=f'{Aws.REGION}',
            integration_http_method='POST',
            path=ingest_queue.queue_name,
            options=apigateway.IntegrationOptions(
                credentials_role=api_role,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code='200',
                        response_templates={
                            'application/json': 'OK',
                        },
                    )
                ],
                request_parameters={
                    'integration.request.header.Content-Type':
                        "'application/x-www-form-urlencoded'",
                },
                passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
                request_templates={
                    'application/json': 
                        'Action=SendMessage&MessageBody=$input.body&MessageAttribute.1.Name=HttpMethod&MessageAttribute.1.Value.StringValue=$context.httpMethod&MessageAttribute.1.Value.DataType=String'
                },
            )
        )

        api.root.add_resource('request_approval').add_method(
            'POST',
            sqs_integration,
            method_responses=[
                apigateway.MethodResponse(status_code='200')
            ]
        )

        search_resource = api.root.add_resource(
            'search',
            default_integration=apigateway.LambdaIntegration(search_function)
        )

        list_properties_by_country = search_resource.add_resource('{country}')
        list_properties_by_country.add_method('GET')
        list_properties_by_city = list_properties_by_country.add_resource('{city}')
        list_properties_by_city.add_method('GET') 
        list_properties_by_street = list_properties_by_city.add_resource('{street}')
        list_properties_by_street.add_method('GET')

        properties_resource = api.root.add_resource('properties')
        property_by_country = properties_resource.add_resource('{country}')
        property_by_city = property_by_country.add_resource('{city}')
        property_by_street = property_by_city.add_resource('{street}')
        property_by_street.add_resource(
            '{number}',
            default_integration=apigateway.LambdaIntegration(search_function)
        ).add_method('GET')

        # --------------------------------------------------------------------------
        #                             SERVICE INTEGRATIONS
        # --------------------------------------------------------------------------
        event_registry_name = f'{UNICORN_NAMESPACES.WEB.value}-{stage.value}'

        publication_approval_requested_event_schema = Path(__file__).parent.parent.joinpath('integration/PublicationApprovalRequested.json').read_text()
        
        publication_approval_requested_schema = CfnSchema(
            self,
            'ContractStatusChangedEventSchema',
            type='OpenApi3',
            registry_name=event_registry_name,
            description='The schema for a request to publish a property',
            schema_name=f'{event_registry_name}@PublicationApprovalRequested',
            content=publication_approval_requested_event_schema
        )

        EventsSchemaConstruct(
            self,
            f'uni-prop-{stage.value}-web-EventSchemaStack',
            name=event_registry_name,
            namespace=UNICORN_NAMESPACES.WEB.value,
            schemas=[publication_approval_requested_schema],
        )

        # --------------------------------------------------------------------------
        #                             SUBSCRIPTIONS
        # --------------------------------------------------------------------------
        SubscriberPoliciesConstruct(
            self,
            f'uni-prop-{stage.value}-web-SubscriptionsStack',
            stage=stage,
            event_bus=event_bus,
            sources=[
                UNICORN_NAMESPACES.WEB,
                UNICORN_NAMESPACES.PROPERTIES
            ]
        )

        # --------------------------------------------------------------------------
        #                             OUTPUTS
        # --------------------------------------------------------------------------
        # Api Gateway Outputs
        CfnOutput(
            self,
            'ApiUrl',
            description='Web service API endpoint',
            value=api.url,
        )

        # Api Actions Outputs
        CfnOutput(
            self,
            'ApiSearchProperties',
            description='GET request to list all properties in a given city',
            value=f'{api.url}search',
        )
        CfnOutput(
            self,
            'ApiSearchPropertiesByCity',
            description='GET request to list all properties in a given city',
            value=f'{api.url}search/{{country}}/{{city}}',
        )
        CfnOutput(
            self,
            'ApiSearchPropertiesByStreet',
            description='GET request to list all properties in a given street',
            value=f'{api.url}search/{{country}}/{{city}}/{{street}}',
        )
        CfnOutput(
            self,
            'ApiPropertyDetails',
            description='GET request to list all properties in a given street',
            value=f'{api.url}search/{{country}}/{{city}}/{{street}}/{{number}}',
        )
        CfnOutput(
            self,
            'ApiRequestApproval',
            description='POST request to request approval for a property',
            value=f'{api.url}request_approval',
        )

        # SQS Outputs
        CfnOutput(
            self,
            'IngestQueueUrl',
            description='URL for the Ingest SQS Queue',
            value=ingest_queue.queue_url,
        )

        # DynamoDB Outputs
        CfnOutput(
            self,
            'WebTableName',
            value=table.table_name,
            description='DynamoDB table storing property information',
        )
            
        # Lambda Function Outputs
        CfnOutput(
            self,
            'searchFunctionName',
            value=search_function.function_name,
            description='Search function name',
        )
        CfnOutput(
            self,
            'searchFunctionArn',
            value=search_function.function_arn,
            description='Search function ARN',
        )
        CfnOutput(
            self,
            'PublicationApprovedEventHandlerFunctionName',
            value=publication_approved_event_handler_function.function_name,
            description='PublicationApprovedEventHandler function name',
        )
        CfnOutput(
            self,
            'PublicationApprovedEventHandlerFunctionArn',
            value=publication_approved_event_handler_function.function_arn,
            description='PublicationApprovedEventHandler function ARN',
        )

        # EventBridge Outputs
        CfnOutput(
            self,
            'UnicornWebEventBusName',
            value=event_bus.event_bus_name,
        )

        # CLOUDWATCH LOGS OUTPUTS
        CfnOutput(
            self,
            'UnicornWebCatchAllLogGroupName',
            description="Log all events on the service's EventBridge Bus",
            value=catch_all_log_group.log_group_name,
        )
        CfnOutput(
            self,
            'UnicornWebCatchAllLogGroupArn',
            description="Log all events on the service's EventBridge Bus",
            value=catch_all_log_group.log_group_arn,
        )
