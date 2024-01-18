import aws_cdk as cdk
from aws_cdk import Tags

from constructs import Construct
from aws_cdk import (aws_apigateway as apigateway,
                     aws_s3 as s3,
                     aws_lambda as lambda_,
                     aws_sqs as sqs,
                     aws_iam as iam,
                     aws_ssm as ssm,
                     aws_dynamodb as dynamodb,
                     )

from aws_cdk.aws_lambda_event_sources import SqsEventSource

AWS_PARTITION = ""
AWS_REGION = ""
AWS_ACCOUNT_ID = ""
STAGE = "Testing"


class ContractsService(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        STAGE = "Testing"

        ## SSM Parameters
        unicorn_contracts_eventbus_name = ssm.StringParameter.from_string_parameter_attributes(self, "UnicornContractsEventBusNameParam",
            parameter_name="/uni-prop/{Stage}/UnicornContractsEventBus".format(Stage=STAGE) # TODO: fix stage param
        ).string_value

        unicorn_contracts_eventbus_arn = ssm.StringParameter.from_string_parameter_attributes(self, "UnicornContractsEventBusArnParam",
            parameter_name="/uni-prop/{Stage}/UnicornContractsEventBusArn".format(Stage=STAGE) # TODO: fix stage param
        ).string_value


        ## SQS Queue
        queue = sqs.Queue(self, "UnicornContractsIngestQueue-Dev")
        event_source = SqsEventSource(
            queue,
            batch_size=1,
            enabled=True,
            max_concurrency=5
        )

        ## DynamoDB Table

        contracts_table = dynamodb.Table(
            self, "ContractsTable",
            partition_key=dynamodb.Attribute(
                name="property_id",
                type=dynamodb.AttributeType.STRING
            ),
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY # This corresponds to UpdateReplacePolicy and DeletionPolicy in SAM
        )

        # Adding tags
        stage_value = cdk.Fn.ref("Stage")
        project_value = cdk.Fn.find_in_map("Constants", "ProjectName", "Value")
        namespace_value = cdk.Fn.sub("{{resolve:ssm:/uni-prop/${Stage}/UnicornContractsNamespace}}")

        Tags.of(contracts_table).add("stage", stage_value)
        Tags.of(contracts_table).add("project", project_value)
        Tags.of(contracts_table).add("namespace", namespace_value)

        ## IAM Policy
        table_arn = "arn:{AWS_Partition}:dynamodb:{AWS_Region}:{AWS_AccountId}:table/{table_name}".format(
                    AWS_Partition=AWS_PARTITION,
                    AWS_Region=AWS_REGION,
                    AWS_AccountId=AWS_ACCOUNT_ID,
                    table_name=""
                ), # TODO: fix concatenation
        table_arn_index = "{table_arn}/index/*".format(table_arn=table_arn)

        iam_policy_ddb_write = iam.PolicyStatement(
            actions=[
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:BatchWriteItem"
            ],
            resources=[table_arn, table_arn_index]
        )
        
        iam_policy_ddb_read = iam.PolicyStatement(
            actions=[
                        "dynamodb:GetItem",
                        "dynamodb:Scan",
                        "dynamodb:Query",
                        "dynamodb:BatchGetItem",
                        "dynamodb:DescribeTable"
                    ],
                resources=[table_arn, table_arn_index] 
        )
        
        ## Lambda Function
        handler = lambda_.Function(
            self, "ContractEventHandlerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("../src"),
            handler="contract_event_handler.lambda_handler",
            events=[event_source],
            initial_policy=[iam_policy_ddb_write, iam_policy_ddb_read]
        )
        


