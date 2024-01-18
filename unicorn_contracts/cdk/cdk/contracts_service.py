import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (aws_apigateway as apigateway,
                     aws_s3 as s3,
                     aws_lambda as lambda_,
                     aws_sqs as sqs,
                     aws_iam as iam,
                     aws_ssm as ssm)

from aws_cdk.aws_lambda_event_sources import SqsEventSource

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

        ## IAM Policy
        iam_policy_ddb_write = iam.PolicyStatement(
            actions=[
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:BatchWriteItem"
            ],
            resources=[
                "arn:${AWS::Partition}:dynamodb:${AWS::Region}:${AWS::AccountId}:table/${tableName}", # TODO: fix concatenation
                "arn:${AWS::Partition}:dynamodb:${AWS::Region}:${AWS::AccountId}:table/${tableName}/index/*" # TODO: fix concatenation
            ])
        
        iam_policy_ddb_read = iam.PolicyStatement(
            actions=[
                        "dynamodb:GetItem",
                        "dynamodb:Scan",
                        "dynamodb:Query",
                        "dynamodb:BatchGetItem",
                        "dynamodb:DescribeTable"
                    ],
                resources=[
                    "arn:${AWS::Partition}:dynamodb:${AWS::Region}:${AWS::AccountId}:table/${tableName}", # TODO: fix concatenation
                    "arn:${AWS::Partition}:dynamodb:${AWS::Region}:${AWS::AccountId}:table/${tableName}/index/*" # TODO: fix concatenation
                ] 
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
        


