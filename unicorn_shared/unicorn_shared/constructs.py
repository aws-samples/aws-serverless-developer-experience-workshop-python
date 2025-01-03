from typing import List
from constructs import Construct
from aws_cdk import (
    Stack,
    Duration
)
from aws_cdk.aws_eventschemas import CfnSchema, CfnRegistry, CfnRegistryPolicy
from typing import Mapping

import aws_cdk.aws_iam as iam
import aws_cdk.aws_events as events
import aws_cdk.aws_lambda as lambda_


from unicorn_shared import (
    UNICORN_NAMESPACES,
    STAGE,
    logsRetentionPeriod,
    eventBusName,
    isProd
)

class DefaultLambdaFunctionConstruct(lambda_.Function):
    def __init__(self, scope: Construct, construct_id: str, *, handler: str, stage: STAGE, environment: Mapping[str, str] = {}, namespace: UNICORN_NAMESPACES, **kwargs) -> None:
        
        super().__init__(scope, 
            construct_id, 
            handler=handler, 
            code=lambda_.Code.from_asset("src"), 
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.seconds(30),
            architecture = lambda_.Architecture.X86_64,
            function_name = f"{construct_id}-{stage.value}",
            tracing=lambda_.Tracing.ACTIVE,
            environment = {
                'SERVICE_NAMESPACE': namespace.value,
                'POWERTOOLS_LOGGER_CASE': 'PascalCase',
                'POWERTOOLS_SERVICE_NAME': namespace.value,
                'POWERTOOLS_TRACE_DISABLED': 'false',  # Explicitly disables tracing, default
                'POWERTOOLS_LOGGER_LOG_EVENT':  'false' if isProd(stage) else 'true', # Logs incoming event, default
                'POWERTOOLS_LOGGER_SAMPLE_RATE': '0.1' if isProd(stage) else '0',  # Debug log sampling percentage, default
                'POWERTOOLS_METRICS_NAMESPACE': namespace.value,
                'POWERTOOLS_LOG_LEVEL': 'INFO',  # Log level for Logger (INFO, DEBUG, etc.), default
                'LOG_LEVEL': 'INFO',  # Log level for Logger
                **environment
            },
            **kwargs)


class SubscriberPoliciesConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, *, stage: STAGE, event_bus: events.EventBus, sources: List[UNICORN_NAMESPACES], **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        policy_statement = iam.PolicyStatement(
            principals=[iam.AccountRootPrincipal()],
            actions=[
                'events:PutRule',
                'events:DeleteRule',
                'events:DescribeRule',
                'events:DisableRule',
                'events:EnableRule',
                'events:PutTargets',
                'events:RemoveTargets',
            ],
            resources=[event_bus.event_bus_arn],
            
            conditions={
                'StringEquals': {
                    "events:source": list(map(lambda namespace: namespace.value, sources)),
                },
                'StringEqualsIfExists': {
                    'events:creatorAccount': Stack.of(self).account,
                },
                'Null': {
                    'events:source': "false",
                },
            }
        ).to_json()

        event_bus_policy = events.CfnEventBusPolicy(
            self,
            'ContractEventsBusPublishPolicy',
            statement_id=f'{event_bus.event_bus_name}-{stage.value}-policy',
            event_bus_name=event_bus.event_bus_name,
            statement=policy_statement
        )


class EventsSchemaConstruct(Construct):

    def __init__(self, scope: Construct, construct_id: str, *, name: str, namespace: str, schemas: List[CfnSchema], **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        registry = CfnRegistry(
            self,
            namespace,
            description=f'Event schemas for {namespace}',
            registry_name=name
        )
        for schema in schemas:
            schema.node.add_dependency(registry)

        schema_arns = list(map(lambda schema: schema.attr_schema_arn, schemas))
        
        registry_policy = CfnRegistryPolicy(
            self, "RegistryPolicy",
            registry_name=name,
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        sid="AllowExternalServices",
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
                        resources=[*schema_arns, registry.attr_registry_arn]
                        # Equivalent to CloudFormation:
                        # - Fn::GetAtt: EventRegistry.RegistryArn
                        # - Fn::Sub: "arn:${AWS::Partition}:schemas:${AWS::Region}:${AWS::AccountId}:schema/${EventRegistry.RegistryName}*"
                    )
                ]
            )
        )

        for schema in schemas:
            registry_policy.node.add_dependency(schema)
        

        