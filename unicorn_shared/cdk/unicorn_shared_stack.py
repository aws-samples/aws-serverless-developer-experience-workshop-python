from aws_cdk import (
    Aws,
    Stack,
    RemovalPolicy,
    Duration,
    CfnOutput
)

from constructs import Construct
from pathlib import Path

import aws_cdk.aws_s3 as s3
import aws_cdk.aws_ssm as ssm
import aws_cdk.aws_s3_deployment as s3deploy

from unicorn_shared import (
    STAGE
)

class UnicornSharedStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, *, stage: STAGE, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        images_bucket = s3.Bucket(self, f'uni-prop-{stage.value}-images')

        ssm.StringParameter(
            self,
            'UnicornImagesBucketParam',
            parameter_name=f'/uni-prop/{stage.value}/ImagesBucket',
            string_value=images_bucket.bucket_name,
        )

        s3deploy.BucketDeployment(
            self,
            'UnicornImagesBucketDeployment',
            sources=[s3deploy.Source.asset(str(Path(__file__).parent.parent.joinpath('assets/property_images.zip')))],
            destination_bucket=images_bucket,
        )

        CfnOutput(self, "ImageUploadBucketName", value=images_bucket.bucket_name)