# app/unicorn_web_api_stack.py
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from aws_cdk import Stack, RemovalPolicy
import aws_cdk.aws_apigateway as apigateway
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_logs as logs

from lib.helper import get_default_logs_retention_period, StackHelper, STAGE, UNICORN_NAMESPACES

class WebApiStack(Stack):
    """
    Stack that defines the Unicorn Web API infrastructure
    
    Example:
    ```python
    app = cdk.App()
    WebApiStack(app, 'WebApiStack', 
        stage=STAGE.DEV,
        env={
            'account': os.environ.get('CDK_DEFAULT_ACCOUNT'),
            'region': os.environ.get('CDK_DEFAULT_REGION')
        }
    )
    ```
    """
    
    # Current deployment stage of the application
    stage: STAGE
    
    def __init__(self, scope, id, *, stage: STAGE, **kwargs):
        """
        Creates a new WebApiStack
        
        Args:
            scope: The scope in which to define this construct
            id: The scoped construct ID
            stage: Deployment stage of the application
            
        Remarks:
        This stack creates:
        - DynamoDB table for data storage
        - API Gateway REST API
        - EventBridge event bus
        - Property publication Construct
        - Property eventing Construct
        - Associated IAM roles and permissions
        """
        super().__init__(scope, id, **kwargs)
        
        # Name of SSM Parameter that holds the DynamoDB table tracking property status.
        self.web_table_name_parameter = "UnicornWebTableName"

        # Name of SSM Parameter that holds the RestApId of Web service's Rest Api
        self.web_rest_api_id_parameter = "UnicornWebRestApiId"

        # Name of SSM Parameter that holds the RootResourceId of Web service's Rest Api
        self.web_api_root_resource_id_parameter = "UnicornWebRestApiRootResourceId"

        # Name of SSM Parameter that holds the Url of Web service's Rest Api
        self.web_api_url_parameter = "UnicornWebRestApiUrl"
        
        # Add standard tags to the CloudFormation stack for resource organization
        # and cost allocation
        StackHelper.add_stack_tags(self, {
            "namespace": UNICORN_NAMESPACES.WEB,
            "stage": stage
        })
        
        # --------------------------------------------------------------------------
        #                                  STORAGE
        # --------------------------------------------------------------------------
        
        # DynamoDB table for storing web application data
        # Uses a composite key (PK/SK) design pattern for flexible querying
        # Includes stream configuration for change data capture
        table = dynamodb.TableV2(self, "WebTable",
            table_name=f"uni-prop-{stage.value}-WebTable",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            dynamo_stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy=RemovalPolicy.DESTROY  # be careful with this in production
        )
        
        # CloudFormation output exposing the DynamoDB table name
        # Useful for cross-stack references and operational visibility
        StackHelper.create_output(self, {
            "name": self.web_table_name_parameter,
            "description": "DynamoDB table storing property information",
            "value": table.table_name,
            "stage": stage.value,
            "create_ssm_string_parameter": True
        })
        
        # --------------------------------------------------------------------------
        #                              API GATEWAY
        # --------------------------------------------------------------------------
        
        # CloudWatch log group for API Gateway access logs
        # Configured with stage-appropriate retention period and removal policy
        api_log_group = logs.LogGroup(self, "UnicornWebApiLogGroup",
            retention=get_default_logs_retention_period(stage),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # REST API Gateway instance
        # Handles all HTTP requests for the Unicorn Web application
        #
        # Configuration includes:
        # - CloudWatch role for logging
        # - Stage-specific deployment options
        # - Access logging to CloudWatch
        # - Stage-appropriate logging levels
        # - Regional endpoint type
        api = apigateway.RestApi(self, "UnicornWebApi",
            cloud_watch_role=True,
            cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
            deploy=False,  # Disable automated deployments
            endpoint_types=[apigateway.EndpointType.REGIONAL]  # Configure as regional endpoint for better latency
        )
        
        api.root.add_method("OPTIONS")
        
        # Create manual Deployment and Stage
        deployment = apigateway.Deployment(self, f"WebApi-{stage.value}-deployment",
            api=api
        )
        
        api_stage = apigateway.Stage(self, f"WebApi-{stage.value}-stage",
            stage_name=stage.value,
            deployment=deployment,
            data_trace_enabled=True,  # Enable detailed request tracing and metrics
            tracing_enabled=True,
            metrics_enabled=True,
            access_log_destination=apigateway.LogGroupLogDestination(api_log_group),  # Configure access logging to CloudWatch
            method_options={
                "/*/*": {
                    "logging_level": apigateway.MethodLoggingLevel.ERROR if stage == STAGE.PROD else apigateway.MethodLoggingLevel.INFO
                    # Only errors in prod, Full logging in non-prod
                }
            },
            throttling_burst_limit=10,
            throttling_rate_limit=100
        )
        
        api.deployment_stage = api_stage
        
        # CloudFormation output exposing the API endpoint URL
        # Used for client configuration and integration testing
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
