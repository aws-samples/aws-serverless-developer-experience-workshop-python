# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from enum import Enum, auto
import aws_cdk as cdk
from aws_cdk import (
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_lambda_nodejs as nodejs,
    aws_logs as logs,
    aws_ssm as ssm,
    Duration
)
from constructs import Construct
from typing import Dict, List, Optional, Any, Union, TypedDict


class STAGE(str, Enum):
    """Deployment stages for the application"""
    LOCAL = 'local'  # Local development environment
    DEV = 'dev'      # Development environment
    PROD = 'prod'    # Production environment


class UNICORN_NAMESPACES(str, Enum):
    """Service namespaces for different components of the Unicorn Properties application"""
    CONTRACTS = 'unicorn.contracts'  # Namespace for contract-related services
    PROPERTIES = 'unicorn.properties'  # Namespace for property-related services
    WEB = 'unicorn.web'  # Namespace for web-related services


def is_valid_stage(stage: Any) -> bool:
    """
    Check if a value is a valid STAGE
    
    Args:
        stage: Value to check against STAGE enum
        
    Returns:
        bool: True if the value is a valid STAGE
    
    Example:
        is_valid = is_valid_stage('dev')  # returns True
        is_invalid = is_valid_stage('test')  # returns False
    """
    return stage in [s.value for s in STAGE]


def get_stage_from_context(app: cdk.App) -> STAGE:
    """
    Retrieves the deployment stage from CDK context, defaulting to 'local' if not specified
    
    Args:
        app: The CDK App instance
        
    Returns:
        STAGE: The deployment stage
        
    Raises:
        ValueError: If the stage from context is not a valid STAGE value
    
    Example:
        app = cdk.App()
        stage = get_stage_from_context(app)
        
        # With context -c stage=dev
        # Returns STAGE.dev
        
        # Without context
        # Returns STAGE.local
        
        # With invalid stage -c stage=invalid
        # Raises ValueError: Invalid stage "invalid". Must be one of: local, dev, prod
    """
    stage_from_context = app.node.try_get_context('stage')
    
    if stage_from_context:
        if not is_valid_stage(stage_from_context):
            valid_stages = ', '.join([s.value for s in STAGE])
            raise ValueError(f'Invalid stage "{stage_from_context}". Must be one of: {valid_stages}')
        return STAGE(stage_from_context)
    
    return STAGE.LOCAL


class StackHelper:
    """Helper class providing utility methods for AWS CDK stack operations"""
    
    @staticmethod
    def create_output(
        scope: cdk.Stack,
        props: Dict[str, Any],
        id: Optional[str] = None
    ) -> Dict[str, Union[cdk.CfnOutput, Optional[ssm.StringParameter]]]:
        """
        Creates a CloudFormation output with standardized formatting
        
        Args:
            scope: The CDK Stack
            props: Configuration properties
                name: Name to be used for export/key and construct ID (if id not provided)
                value: Value of the output
                stage: Stage of the stack this output is in
                description: Optional description of the output
                export: Optional flag to determine if name should be used as exportName (default: False)
                create_ssm_string_parameter: Optional flag to create SSM Parameter (default: False)
            id: Optional construct ID
            
        Returns:
            Dict containing the output and optional parameter
        """
        # Create the CloudFormation output
        output_props = {
            'value': props['value'],
            'export_name' if props.get('export') else 'key': props['name']
        }
        
        if 'description' in props:
            output_props['description'] = props['description']
            
        output = cdk.CfnOutput(scope, id or props['name'], **output_props)
        
        parameter = None
        
        # Create SSM Parameter if requested
        if props.get('create_ssm_string_parameter'):
            parameter_props = {
                'parameter_name': f"/uni-prop/{props['stage']}/{props['name']}",
                'string_value': props['value']
            }
            
            if 'description' in props:
                parameter_props['description'] = props['description']
                
            parameter = ssm.StringParameter(
                scope,
                f"/uni-prop/{props['stage']}/{props['name']}Parameter",
                **parameter_props
            )
            
        return {'output': output, 'parameter': parameter}
    
    @staticmethod
    def lookup_ssm_parameter(
        scope: cdk.Stack,
        name: str
    ) -> str:
        """
        Looks up an SSM parameter value
        
        Args:
            scope: The CDK Stack
            name: Name to be used for ParameterName and construct Id
            
        Returns:
            str: The parameter value as a string token
        """
        # Create a token that will be resolved at deployment time
        return ssm.StringParameter.value_for_string_parameter(scope, name)
    
    @staticmethod
    def add_stack_tags(
        scope: cdk.Stack,
        props: Dict[str, Any]
    ) -> None:
        """
        Adds standard tags to a CDK stack
        
        Args:
            scope: The CDK Stack
            props: Configuration properties
                namespace: The namespace tag value
                stage: The stage tag value
                project: Optional project tag value
        """
        cdk.Tags.of(scope).add('namespace', props['namespace'].value)
        cdk.Tags.of(scope).add('stage', props['stage'].value)
        cdk.Tags.of(scope).add(
            'project',
            props.get('project', 'AWS Serverless Developer Experience')
        )


class LambdaOptionsProps(TypedDict):
    table: dynamodb.ITableV2
    stage: STAGE
    service_namespace: UNICORN_NAMESPACES


class LambdaHelper:
    """Helper class providing default configurations for Lambda functions"""
    
    # Default NodeJS Lambda function properties with standardized settings
    default_lambda_options = {
        'runtime': lambda_.Runtime.PYTHON_3_13,
        'handler': 'lambdaHandler',
        'tracing': lambda_.Tracing.ACTIVE,
        'memory_size': 128,
        'timeout': Duration.seconds(15),
        'architecture': lambda_.Architecture.X86_64,
    }
    
    @staticmethod
    def get_default_environment_variables(props: LambdaOptionsProps) -> Dict[str, str]:
        """
        Returns the default environment variables for Lambda functions
        
        Args:
            props: Configuration properties including DynamoDB table and stage
                table: DynamoDB table reference
                stage: Deployment stage
                service_namespace: Service namespace
                
        Returns:
            Dict[str, str]: Environment variables configuration
            
        Example:
            env_vars = LambdaHelper.get_default_environment_variables({
                'table': my_dynamo_table,
                'stage': STAGE.dev,
                'service_namespace': UNICORN_NAMESPACES.WEB
            })
            
            
        """
        return {
            'DYNAMODB_TABLE': props['table'].table_name,
            'SERVICE_NAMESPACE': props['service_namespace'].value,
            'POWERTOOLS_LOGGER_CASE': 'PascalCase',
            'POWERTOOLS_SERVICE_NAME': props['service_namespace'].value,
            'POWERTOOLS_TRACE_DISABLED': 'false',  # Explicitly disables tracing, default
            'POWERTOOLS_LOGGER_LOG_EVENT': str(props['stage'] != STAGE.prod).lower(),
            'POWERTOOLS_LOGGER_SAMPLE_RATE': '0.1' if props['stage'] != STAGE.prod else '0',  # Debug log sampling percentage
            'POWERTOOLS_METRICS_NAMESPACE': props['service_namespace'].value,
            'POWERTOOLS_LOG_LEVEL': 'INFO',  # Log level for Logger (INFO, DEBUG, etc.), default
            'LOG_LEVEL': 'INFO',  # Log level for Logger
        }


def get_default_logs_retention_period(stage: Optional[STAGE] = None) -> logs.RetentionDays:
    """
    Returns the CloudWatch Logs retention period based on the deployment stage.
    If no stage is provided, defaults to ONE_DAY retention.
    
    Args:
        stage: Optional deployment stage of the application
        
    Returns:
        logs.RetentionDays: The retention period for CloudWatch Logs
        
    Example:
        # With specific stage
        stage = get_stage_from_context(app)
        retention = get_default_logs_retention_period(stage)
        
        # With default retention (ONE_DAY)
        default_retention = get_default_logs_retention_period()
        
        logs.LogGroup(self, 'MyLogGroup', retention=retention)
    """
    if stage == STAGE.LOCAL:
        return logs.RetentionDays.ONE_DAY
    elif stage == STAGE.DEV:
        return logs.RetentionDays.ONE_WEEK
    elif stage == STAGE.PROD:
        return logs.RetentionDays.TWO_WEEKS
    else:
        return logs.RetentionDays.ONE_DAY
