# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from constructs import Construct
import aws_cdk.aws_ssm as ssm

class NamespacesConstruct(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)

        # Create SSM parameters for namespaces
        self.unicorn_contracts_namespace = ssm.StringParameter(
            self,
            'UnicornContractsNamespace',
            parameter_name='/uni-prop/namespaces/contracts',
            string_value='unicorn-contracts',
            description='Namespace for Unicorn Contracts service.',
            simple_name=False
        )

        self.unicorn_properties_namespace = ssm.StringParameter(
            self,
            'UnicornPropertiesNamespace',
            parameter_name='/uni-prop/namespaces/properties',
            string_value='unicorn-properties',
            description='Namespace for Unicorn Properties service.',
            simple_name=False
        )

        self.unicorn_web_namespace = ssm.StringParameter(
            self,
            'UnicornWebNamespace',
            parameter_name='/uni-prop/namespaces/web',
            string_value='unicorn-web',
            description='Namespace for Unicorn Web service.',
            simple_name=False
        )