# app/unicorn_web_api_stack.py
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from aws_cdk import Stack, RemovalPolicy
import aws_cdk.aws_apigateway as apigateway
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_logs as logs

from lib.helper import get_default_logs_retention_period, StackHelper, STAGE, UNICORN_NAMESPACES

class WebApiStack(Stack):
    """Stack that defines the Unicorn Web API infrastructure"""
    
    def __init__(self, scope, id, *, stage: STAGE, **kwargs):
        
        super().__init__(scope, id, **kwargs)
        
        # Name of SSM Parameter that holds the DynamoDB table tracking property status.
        self.web_table_name_parameter = "UnicornWebTableName"

        # Name of SSM Parameter that holds the RestApId of Web service's Rest Api
        self.web_rest_api_id_parameter = "UnicornWebRestApiId"

        # Name of SSM Parameter that holds the RootResourceId of Web service's Rest Api
        self.web_api_root_resource_id_parameter = "UnicornWebRestApiRootResourceId"

        # Name of SSM Parameter that holds the Url of Web service's Rest Api
        self.web_api_url_parameter = "UnicornWebRestApiUrl"
        
        # Add standard tags to the CloudFormation stack
        StackHelper.add_stack_tags(self, {
            "namespace": UNICORN_NAMESPACES.WEB,
            "stage": stage
        })
        
        # STORAGE
        table = dynamodb.TableV2(self, "WebTable",
            table_name=f"uni-prop-{stage.value}-WebTable",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            dynamo_stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        StackHelper.create_output(self, {
            "name": self.web_table_name_parameter,
            "description": "DynamoDB table storing property information",
            "value": table.table_name,
            "stage": stage.value,
            "create_ssm_string_parameter": True
        })
        
        # API GATEWAY
        api_log_group = logs.LogGroup(self, "UnicornWebApiLogGroup",
            retention=get_default_logs_retention_period(stage),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        api = apigateway.RestApi(self, "UnicornWebApi",
            cloud_watch_role=True,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
            deploy=False,
            endpoint_types=[apigateway.EndpointType.REGIONAL]
        )
        
        api.root.add_method("OPTIONS")
        
        deployment = apigateway.Deployment(self, f"WebApi-{stage.value}-deployment",
            api=api
        )
        
        api_stage = apigateway.Stage(self, f"WebApi-{stage.value}-stage",
            stage_name=stage.value,
            deployment=deployment,
            data_trace_enabled=True,
            tracing_enabled=True,
            metrics_enabled=True,
            access_log_destination=apigateway.LogGroupLogDestination(api_log_group),
            method_options={
                "/*/*": {
                    "logging_level": apigateway.MethodLoggingLevel.ERROR if stage == STAGE.PROD else apigateway.MethodLoggingLevel.INFO
                }
            },
            throttling_burst_limit=10,
            throttling_rate_limit=100
        )
        
        api.deployment_stage = api_stage
        
        StackHelper.create_output(self, {
            "name": self.web_api_url_parameter,
            "description": "Web service API endpoint",
            "value": api.url,
            "stage": stage.value,
            "create_ssm_string_parameter": True
        })
        
        StackHelper.create_output(self, {
            "name": self.web_rest_api_id_parameter,
            "description": "Web service API endpoint",
            "value": api.rest_api_id,
            "stage": stage.value,
            "create_ssm_string_parameter": True
        })
        
        StackHelper.create_output(self, {
            "name": self.web_api_root_resource_id_parameter,
            "description": "Web service API endpoint",
            "value": api.rest_api_root_resource_id,
            "stage": stage.value,
            "create_ssm_string_parameter": True
        })
