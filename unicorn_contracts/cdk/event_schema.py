from typing import List
from constructs import Construct
from aws_cdk import Stack
from aws_cdk.aws_eventschemas import CfnSchema, CfnRegistry, CfnRegistryPolicy

import aws_cdk.aws_iam as iam


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
        

        