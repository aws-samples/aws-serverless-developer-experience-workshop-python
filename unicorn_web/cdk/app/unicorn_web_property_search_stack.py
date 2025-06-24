# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from aws_cdk import (
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    Stack,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct
from dataclasses import dataclass

from lib.helper import (
    get_default_logs_retention_period,
    StackHelper,
    STAGE,
    UNICORN_NAMESPACES,
)


@dataclass
class WebPropertySearchStackProps:
    stage: STAGE
    description: str
    env: dict
    event_bus_name: str
    table_name: str
    rest_api_id: str
    rest_api_root_resource_id: str
    rest_api_url: str
    powertools_layer: lambda_.LayerVersion


class WebPropertySearchStack(Stack):
    """Stack that defines the Unicorn Web property search infrastructure"""

    def __init__(
        self,
        scope: Construct,
        id,
        *,
        props: WebPropertySearchStackProps,
        **kwargs,
    ):
        """
        Creates a new WebPropertySearchStack

        Parameters:
        - scope: The scope in which to define this construct
        - id: The scoped construct ID
        """
        super().__init__(scope, id, **kwargs)

        # Add standard tags to the CloudFormation stack
        StackHelper.add_stack_tags(
            self,
            {
                "namespace": UNICORN_NAMESPACES.WEB,
                "stage": props.stage,
            },
        )

        # Import resources based on details from SSM Parameter Store
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

        search_function = lambda_.Function(
            self,
            f"SearchFunction-{props.stage.value}",
            runtime=lambda_.Runtime.PYTHON_3_13,
            code=lambda_.Code.from_asset("src/"),
            handler="search_service.property_search_function.lambda_handler",
            tracing=lambda_.Tracing.ACTIVE,
            log_group=logs.LogGroup(
                self,
                "PropertySearchFunctionLogs",
                removal_policy=RemovalPolicy.DESTROY,
                retention=get_default_logs_retention_period(props.stage),
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
        )

        # Grant read access to DynamoDB table
        table.grant_read_data(search_function)

        # CloudFormation outputs for Lambda function details
        StackHelper.create_output(
            self,
            {
                "name": "searchFunctionName",
                "value": search_function.function_name,
                "stage": props.stage.value,
            },
        )

        StackHelper.create_output(
            self,
            {
                "name": "searchFunctionArn",
                "value": search_function.function_arn,
                "stage": props.stage.value,
            },
        )

        # API Gateway resources
        api_integration_role = iam.Role(
            self,
            f"WebApiSearchIntegrationRole-{props.stage.value}",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
        )
        search_function.grant_invoke(api_integration_role)

        # Base search endpoint
        search_resource = api.root.add_resource(
            "search",
            default_integration=apigateway.LambdaIntegration(
                search_function,
                credentials_role=api_integration_role,
            ),
        )

        # CloudFormation output for base search endpoint
        StackHelper.create_output(
            self,
            {
                "name": "ApiSearchProperties",
                "description": "GET request to list all properties in a given city",
                "value": f"{api_url}search",
                "stage": props.stage.value,
            },
        )

        # Country-level search endpoint
        list_properties_by_country = search_resource.add_resource("{country}")

        # City-level search endpoint
        list_properties_by_city = list_properties_by_country.add_resource("{city}")
        list_properties_by_city.add_method(
            "GET",
            integration=apigateway.LambdaIntegration(
                search_function,
                credentials_role=api_integration_role,
            ),
            request_parameters={
                "method.request.path.country": True,
                "method.request.path.city": True,
            },
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_models={
                        "application/json": apigateway.Model.EMPTY_MODEL,
                    },
                )
            ],
        )

        # CloudFormation output for city search endpoint
        StackHelper.create_output(
            self,
            {
                "name": "ApiSearchPropertiesByCity",
                "description": "GET request to list all properties in a given city",
                "value": f"{api_url}search/{{country}}/{{city}}",
                "stage": props.stage.value,
            },
        )

        # Street-level search endpoint
        list_properties_by_street = list_properties_by_city.add_resource("{street}")
        list_properties_by_street.add_method("GET")

        # CloudFormation output for street search endpoint
        StackHelper.create_output(
            self,
            {
                "name": "ApiSearchPropertiesByStreet",
                "description": "GET request to list all properties in a given street",
                "value": f"{api_url}search/{{country}}/{{city}}/{{street}}",
                "stage": props.stage.value,
            },
        )

        # Property details resource hierarchy
        properties_resource = api.root.add_resource("properties")
        property_by_country = properties_resource.add_resource("{country}")
        property_by_city = property_by_country.add_resource("{city}")
        property_by_street = property_by_city.add_resource("{street}")

        # Individual property endpoint
        property_by_street.add_resource(
            "{number}",
            default_integration=apigateway.LambdaIntegration(search_function),
        ).add_method("GET")

        # CloudFormation output for property details endpoint
        StackHelper.create_output(
            self,
            {
                "name": "ApiPropertyDetails",
                "description": "GET request to get the full details of a single property",
                "value": f"{api_url}properties/{{country}}/{{city}}/{{street}}/{{number}}",
                "stage": props.stage.value,
            },
        )

        # Create deployment
        deployment = apigateway.Deployment(
            self,
            "deployment",
            api=api,
            description="Unicorn Web API deployment",
            stage_name=props.stage.value,
        )
        deployment.node.add_dependency(
            properties_resource,
            property_by_country,
            property_by_city,
            property_by_street,
        )
        deployment.node.add_dependency(
            search_resource,
            list_properties_by_country,
            list_properties_by_city,
            list_properties_by_street,
        )
