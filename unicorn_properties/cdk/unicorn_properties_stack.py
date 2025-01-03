
from aws_cdk import (
    Aws,
    Duration,
    Stack,
    RemovalPolicy,
    CfnOutput,
)

from unicorn_shared import (
    STAGE,
    UNICORN_NAMESPACES,
    logsRetentionPeriod,
    eventBusName,
    isProd,
)

from unicorn_shared.constructs import (
    SubscriberPoliciesConstruct,
    EventsSchemaConstruct,
    DefaultLambdaFunctionConstruct,
)

from aws_cdk.aws_stepfunctions import (
    DefinitionBody,
    LogLevel,
    LogOptions,
    StateMachine,
)

from aws_cdk.aws_eventschemas import CfnSchema
from constructs import Construct
from pathlib import Path

import aws_cdk.aws_events as events
import aws_cdk.aws_events_targets as targets
import aws_cdk.aws_logs as logs
import aws_cdk.aws_iam as iam
import aws_cdk.aws_ssm as ssm
import aws_cdk.aws_sqs as sqs
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_lambda_event_sources as eventsources

class UnicornPropertiesStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, *, stage: STAGE, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        retention_period = logsRetentionPeriod(stage)

        event_bus = events.EventBus(
            self,
            id=f'UnicornPropertiesBus-{stage.value}',
            event_bus_name=eventBusName(stage, UNICORN_NAMESPACES.PROPERTIES)
        )

        catch_all_log_group = logs.LogGroup(
            self, 'UnicornPropertiesCatchAllLogGroup',
            log_group_name=f"/aws/events/{stage.value}/{UNICORN_NAMESPACES.PROPERTIES.value}-catchall",
            removal_policy=RemovalPolicy.DESTROY,
            retention=retention_period
        )

        event_bus_policy = events.CfnEventBusPolicy(
            self,
            'UnicornPropertiesEventsBusPublishPolicy',
            statement_id=f'OnlyPropertiesServiceCanPublishToEventBus-{stage.value}',
            event_bus_name=event_bus.event_bus_name,
            statement=iam.PolicyStatement(
                actions=['events:PutEvents'],
                resources=[event_bus.event_bus_arn],
                principals=[iam.AccountRootPrincipal()],
                sid=f'OnlyPropertiesServiceCanPublishToEventBus-{stage.value}',
                conditions={
                    'StringEquals': {
                        "aws:Source": UNICORN_NAMESPACES.PROPERTIES.value
                    }
                }
            ).to_json()
        )

        # Create a Catchall rule used for development purposes.
        catch_all_rule = events.Rule(
            self,
            'UnicornPropertiesCatchAllRule',
            description='Catch all events published by the conproperties service.',
            event_bus=event_bus,
            event_pattern={
                'source': [
                    UNICORN_NAMESPACES.CONTRACTS.value,
                    UNICORN_NAMESPACES.PROPERTIES.value,
                    UNICORN_NAMESPACES.WEB.value
                ],
                'account': [f'{Aws.ACCOUNT_ID}']
            },

            rule_name=f'{UNICORN_NAMESPACES.CONTRACTS.value}-catchall',
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
            table_name=f'uni-prop-{stage.value}-properties-ContractStatusTable',
            partition_key={
                'name': 'property_id',
                'type': dynamodb.AttributeType.STRING},
            removal_policy=RemovalPolicy.DESTROY,
            dynamo_stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )

        # --------------------------------------------------------------------------
        #                             DEAD LETTER QUEUES                            
        # --------------------------------------------------------------------------
        # Store EventBridge events that failed to be DELIVERED to ContractStatusChangedHandlerFunction
        event_bus_DLQ = sqs.Queue(
            self,
            'PropertiesEventBusRuleDLQ',
            removal_policy=RemovalPolicy.DESTROY,
            retention_period=Duration.days(14),
            queue_name=f'PropertiesEventBusRuleDLQ-{stage.value}'
        )

        # Store failed INVOCATIONS to each Lambda function in Unicorn Properties Service
        properties_service_DLQ = sqs.Queue(
            self,
            'PropertiesServiceDLQ',
            removal_policy=RemovalPolicy.DESTROY,
            retention_period=Duration.days(14),
            queue_name=f'PropertiesServiceDLQ-{stage.value}'
        )

        # --------------------------------------------------------------------------
        #                             LAMBDA FUNCTIONS
        # --------------------------------------------------------------------------
        
        environment = {
            'CONTRACT_STATUS_TABLE': table.table_name
        }

        contract_status_changed_handler_function = DefaultLambdaFunctionConstruct(
            self,
            f'ContractStatusChangedHandlerFunction-{stage.value}',
            handler='properties_service.contract_status_changed_event_handler.lambda_handler',
            stage=stage,
            namespace=UNICORN_NAMESPACES.PROPERTIES,
            log_group=logs.LogGroup(
                self,
                f'ContractStatusChangedHandlerFunctionLogGroup-{stage.value}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=retention_period
            ),
            environment=environment
        )

        table.grant_read_write_data(contract_status_changed_handler_function)
        properties_service_DLQ.grant_send_messages(contract_status_changed_handler_function)

        events.Rule(
            self,
            f'unicorn.properties-ContractStatusChanged',
            rule_name='unicorn.properties-ContractStatusChanged',
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                detail_type=["ContractStatusChanged"],
                source=[UNICORN_NAMESPACES.CONTRACTS.value],
            ),
            targets=[
                targets.LambdaFunction(contract_status_changed_handler_function, dead_letter_queue=event_bus_DLQ),
            ],
            
        )

        # Listens to Contract status changes from ContractStatusTable to un-pause StepFunctions
        properties_approval_sync_function = DefaultLambdaFunctionConstruct(
            self,
            f'PropertiesApprovalSyncFunction-{stage.value}',
            handler='properties_service.properties_approval_sync_function.lambda_handler',
            stage=stage,
            namespace=UNICORN_NAMESPACES.PROPERTIES,
            log_group=logs.LogGroup(
                self,
                f'PropertiesApprovalSyncFunctionLogGroup-{stage.value}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=retention_period
            ),
            environment=environment
        )

        properties_service_DLQ.grant_send_messages(properties_approval_sync_function)
        table.grant_stream_read(properties_approval_sync_function)
        table.grant_read_data(properties_approval_sync_function)

        properties_approval_sync_function.add_event_source(
            eventsources.DynamoEventSource(
                table,
                starting_position=lambda_.StartingPosition.TRIM_HORIZON,
                on_failure=eventsources.SqsDlq(properties_service_DLQ)
            )
        )

        # Part of the ApprovalStateMachine, checks if a given Property has an existing Contract in ContractStatusTable
        contract_exists_checker_function = DefaultLambdaFunctionConstruct(
            self,
            f'ContractExistsCheckerFunction-{stage.value}',
            handler='properties_service.contract_exists_checker_function.lambda_handler',
            stage=stage,
            namespace=UNICORN_NAMESPACES.PROPERTIES,
            log_group=logs.LogGroup(
                self,
                f'ContractExistsCheckerFunctionLogGroup-{stage.value}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=retention_period
            ),
            environment=environment
        )
        table.grant_read_write_data(contract_exists_checker_function)

        wait_for_contract_approval_function = DefaultLambdaFunctionConstruct(
            self,
            f'WaitForContractApprovalFunction-{stage.value}',
            handler='properties_service.wait_for_contract_approval_function.lambda_handler',
            stage=stage,
            namespace=UNICORN_NAMESPACES.PROPERTIES,
            log_group=logs.LogGroup(
                self,
                f'WaitForContractApprovalFunctionLogGroup-{stage.value}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=retention_period
            ),
            environment=environment
        )
        table.grant_read_write_data(wait_for_contract_approval_function)

        content_integrity_validator_function = DefaultLambdaFunctionConstruct(
            self,
            f'ContentIntegrityValidatorFunction-{stage.value}',
            handler='properties_service.content_integrity_validator_function.lambda_handler',
            stage=stage,
            namespace=UNICORN_NAMESPACES.PROPERTIES,
            log_group=logs.LogGroup(
                self,
                f'ContentIntegrityValidatorFunctionLogGroup-{stage.value}',
                removal_policy=RemovalPolicy.DESTROY,
                retention=retention_period
            )
        )

        # --------------------------------------------------------------------------
        #                             STATE MACHINE
        # --------------------------------------------------------------------------

        images_bucket_name = ssm.StringParameter.value_for_typed_string_parameter_v2(
            self,
            parameter_name=f'/uni-prop/{stage.value}/ImagesBucket',
            type=ssm.ParameterValueType.STRING,
        )

        state_machine_log_group = logs.LogGroup(
            self,
            f'ApprovalStateMachineLogGroup-{stage.value}',
            removal_policy=RemovalPolicy.DESTROY,
            retention=retention_period
        )

        definition_body = Path(__file__).parent.parent.joinpath('src/state_machine/property_approval.asl.json').read_text()
        state_machine = StateMachine(self,
            id='ApprovalStateMachine',
            state_machine_name=f'ApprovalStateMachine-{Aws.STACK_NAME}',
            definition_body=DefinitionBody.from_string(definition_body),
            definition_substitutions={
                'ContractExistsChecker': contract_exists_checker_function.function_arn,
                'WaitForContractApproval': wait_for_contract_approval_function.function_arn,
                'ContentIntegrityValidator': content_integrity_validator_function.function_arn,
                'ImageUploadBucketName': images_bucket_name,
                'EventBusName': event_bus.event_bus_name,
                'ServiceNmae': UNICORN_NAMESPACES.PROPERTIES.value,
            },
            tracing_enabled=True,
            logs=LogOptions(
                level=LogLevel.ALL,
                include_execution_data=True,
                destination=state_machine_log_group,
            ),
            role=iam.Role(
                self,
                'StateMachineRole',
                assumed_by=iam.ServicePrincipal('states.amazonaws.com'),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name('AWSXRayDaemonWriteAccess'),
                    iam.ManagedPolicy.from_aws_managed_policy_name('ComprehendFullAccess'),
                    iam.ManagedPolicy.from_aws_managed_policy_name('AmazonRekognitionFullAccess'),
                ],
                inline_policies={
                    'CloudWatchPublishLogsMetrics': iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                actions=[
                                    'logs:CreateLogDelivery',
                                    'logs:GetLogDelivery',
                                    'logs:UpdateLogDelivery',
                                    'logs:DeleteLogDelivery',
                                    'logs:ListLogDeliveries',
                                    'logs:PutResourcePolicy',
                                    'logs:DescribeResourcePolicies',
                                    'logs:DescribeLogGroups',
                                    'cloudwatch:PutMetricData',
                                ],
                                resources=[
                                    "*",
                                ],
                            ),
                        ],
                    ),
                    'S3ReadPolicy': iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                actions=[
                                    's3:Get*',
                                ],
                                resources=[
                                    f'arn:aws:s3:::${images_bucket_name}/*',
                                ],
                            ),
                        ],
                    ),
                },
            ),
        )
        state_machine.grant_task_response(properties_approval_sync_function)
        event_bus.grant_put_events_to(state_machine)
        wait_for_contract_approval_function.grant_invoke(state_machine)
        content_integrity_validator_function.grant_invoke(state_machine)
        contract_exists_checker_function.grant_invoke(state_machine)

        events.Rule(
            self,
            f'unicorn.properties-PublicationApprovalRequested',
            rule_name='unicorn.properties-PublicationApprovalRequested',
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=[UNICORN_NAMESPACES.WEB.value],
                detail_type=['PublicationApprovalRequested'],
            ),
            targets=[
                targets.SfnStateMachine(state_machine, dead_letter_queue=event_bus_DLQ),
            ],
        )

        event_registry_name = f'{UNICORN_NAMESPACES.PROPERTIES.value}-{stage.value}'

        publication_evaluation_completed_event_schema = Path(__file__).parent.parent.joinpath('integration/PublicationEvaluationCompleted.json').read_text()
        publication_evaluation_completed_schema = CfnSchema(
            self,
            'PublicationEvaluationCompletedSchema',
            type='OpenApi3',
            registry_name=event_registry_name,
            schema_name=f'{event_registry_name}@PublicationEvaluationCompleted',
            description='The schema for when a property evaluation is completed',
            content=publication_evaluation_completed_event_schema,
        )

        EventsSchemaConstruct(
            self,
            f'uni-prop-{stage.value}-properties-EventSchemaSack',
            name=event_registry_name,
            namespace=UNICORN_NAMESPACES.PROPERTIES.value,
            schemas=[publication_evaluation_completed_schema],
        )

        # --------------------------------------------------------------------------
        #                             SUBSCRIPTIONS
        # --------------------------------------------------------------------------

        # Update this policy as you get new subscribers by adding their namespace to events:source
        SubscriberPoliciesConstruct(
            self,
            f'uni-prop-{stage.value}-properties-SubscriptionsStack',
            stage=stage,
            event_bus=event_bus,
            sources=[UNICORN_NAMESPACES.PROPERTIES]
        )

        # --------------------------------------------------------------------------
        #                             OUTPUTS
        # --------------------------------------------------------------------------
        
        # DYNAMODB OUTPUTS
        CfnOutput(
            self,
            'ContractStatusTableName',
            description='DynamoDB table storing contract status information',
            value=table.table_name,
        )

        # LAMBDA FUNCTIONS OUTPUTS
        CfnOutput(
            self,
            'ContractStatusChangedHandlerFunctionName',
            description='ContractStatusChangedHandler function name',
            value=contract_status_changed_handler_function.function_name,
        )
        CfnOutput(
            self,
            'ContractStatusChangedHandlerFunctionArn',
            description='ContractStatusChangedHandler function ARN',
            value=contract_status_changed_handler_function.function_arn,
        )

        CfnOutput(
            self,
            'PropertiesApprovalSyncFunctionName',
            value=properties_approval_sync_function.function_name,
        )
        CfnOutput(
            self,
            'PropertiesApprovalSyncFunctionArn',
            value=properties_approval_sync_function.function_arn,
        )

        CfnOutput(
            self,
            'ContractExistsCheckerFunctionNName',
            value=contract_exists_checker_function.function_name,
        )
        CfnOutput(
            self,
            'ContractExistsCheckerFunctionArn',
            value=contract_exists_checker_function.function_arn,
        )

        CfnOutput(
            self,
            'ContentIntegrityValidatorFunctionNName',
            value=content_integrity_validator_function.function_name,
        )
        CfnOutput(
            self,
            'ContentIntegrityValidatorFunctionArn',
            value=content_integrity_validator_function.function_arn,
        )

        CfnOutput(
            self,
            'WaitForContractApprovalFunctionNName',
            value=wait_for_contract_approval_function.function_name,
        )
        CfnOutput(
            self,
            'WaitForContractApprovalFunctionArn',
            value=wait_for_contract_approval_function.function_arn,
        )

        # STEPFUNCTIONS OUTPUTS
        CfnOutput(
            self,
            'ApprovalStateMachineName',
            value=state_machine.state_machine_name,
        )
        CfnOutput(
            self,
            'ApprovalStateMachineArn',
            value=state_machine.state_machine_arn,
        )
     
        # EVENT BRIDGE OUTPUTS
        CfnOutput(
            self,
            'UnicornPropertiesEventBusName',
            value=event_bus.event_bus_name,
        )

        # CLOUDWATCH LOGS OUTPUTS
        CfnOutput(
            self,
            'UnicornPropertiesCatchAllLogGroupArn',
            description="Log all events on the service's EventBridge Bus",
            value=catch_all_log_group.log_group_arn,
        )
        CfnOutput(
            self,
            'ApprovalStateMachineLogGroupName',
            value=state_machine_log_group.log_group_name,
        )
