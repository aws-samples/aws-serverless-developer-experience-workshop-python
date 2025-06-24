# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from aws_cdk import Stack, CfnOutput
from constructs import Construct
from app.constructs.namespaces_construct import NamespacesConstruct

class UnicornNamespacesStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        namespaces = NamespacesConstruct(self, 'Namespaces')

        CfnOutput(self, 'UnicornContractsNamespace', 
            description='Unicorn Contracts namespace parameter',
            value=namespaces.unicorn_contracts_namespace.parameter_name
        )
        CfnOutput(self, 'UnicornPropertiesNamespace', 
            description='Unicorn Properties namespace parameter',
            value=namespaces.unicorn_properties_namespace.parameter_name
        )
        CfnOutput(self, 'UnicornWebNamespace', 
            description='Unicorn Web namespace parameter',
            value=namespaces.unicorn_web_namespace.parameter_name
        )
        CfnOutput(self, 'UnicornContractsNamespaceValue', 
            description='Unicorn Contracts namespace parameter value',
            value=namespaces.unicorn_contracts_namespace.string_value
        )
        CfnOutput(self, 'UnicornPropertiesNamespaceValue', 
            description='Unicorn Properties namespace parameter value',
            value=namespaces.unicorn_properties_namespace.string_value
        )
        CfnOutput(self, 'UnicornWebNamespaceValue', 
            description='Unicorn Web namespace parameter value',
            value=namespaces.unicorn_web_namespace.string_value
        )