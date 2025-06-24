# lib/helper.py
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from enum import Enum
from aws_cdk import CfnOutput, Tags, Aws
from aws_cdk import (
    aws_lambda as lambda_,
)
import aws_cdk.aws_ssm as ssm
import aws_cdk.aws_logs as logs
from constructs import Construct


class STAGE(str, Enum):
    """Deployment stages for the application"""

    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class UNICORN_NAMESPACES(str, Enum):
    """Service namespaces for different components of the Unicorn Properties application"""

    CONTRACTS = "unicorn.contracts"
    PROPERTIES = "unicorn.properties"
    WEB = "unicorn.web"


def get_stage_from_context(app):
    """
    Retrieves the deployment stage from CDK context, defaulting to 'local' if not specified
    """
    stage_from_context = app.node.try_get_context("stage")

    if stage_from_context:
        if stage_from_context not in [s.value for s in STAGE]:
            raise ValueError(
                f"Invalid stage '{stage_from_context}'. Must be one of: {', '.join([s.value for s in STAGE])}"
            )
        return stage_from_context

    return STAGE.LOCAL


class StackHelper:
    """Helper class providing utility methods for AWS CDK stack operations"""

    @staticmethod
    def create_output(scope, props, id=None):
        """Creates a CloudFormation output with standardized formatting"""
        output = CfnOutput(
            scope,
            id or props["name"],
            value=props["value"],
            export_name=props["name"] if props.get("export") else None,
            description=props.get("description"),
        )

        parameter = None
        if props.get("create_ssm_string_parameter"):
            parameter_props = {
                "parameter_name": f"/uni-prop/{props['stage']}/{props['name']}",
                "string_value": props["value"],
            }
            if props.get("description"):
                parameter_props["description"] = props["description"]

            parameter = ssm.StringParameter(
                scope,
                f"/uni-prop/{props['stage']}/{props['name']}Parameter",
                **parameter_props,
            )

        return {"output": output, "parameter": parameter}

    @staticmethod
    def lookup_ssm_parameter(scope, name):
        """Looks up an SSM parameter by name"""
        parameter = ssm.StringParameter.from_string_parameter_name(scope, name, name)
        return parameter.string_value

    @staticmethod
    def add_stack_tags(scope, props):
        """Adds standard tags to a CDK stack"""
        Tags.of(scope).add("namespace", props["namespace"].value)
        Tags.of(scope).add("stage", props["stage"].value)
        Tags.of(scope).add(
            "project", props.get("project", "AWS Serverless Developer Experience")
        )


def get_default_logs_retention_period(stage=None):
    """Returns the CloudWatch Logs retention period based on the deployment stage"""
    if stage == STAGE.LOCAL.value:
        return logs.RetentionDays.ONE_DAY
    elif stage == STAGE.DEV.value:
        return logs.RetentionDays.ONE_WEEK
    elif stage == STAGE.PROD.value:
        return logs.RetentionDays.TWO_WEEKS
    else:
        return logs.RetentionDays.ONE_DAY
