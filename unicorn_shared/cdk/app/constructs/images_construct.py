# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from enum import Enum
from aws_cdk import RemovalPolicy, Stack
from constructs import Construct
import aws_cdk.aws_s3_deployment as s3deploy
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_ssm as ssm
from cdk_nag import NagSuppressions

class STAGE(str, Enum):
    local = 'local'
    dev = 'dev'
    prod = 'prod'

class ImagesInfraConstruct(Construct):
    def __init__(self, scope: Construct, id: str, *, stage: str):
        super().__init__(scope, id)

        # S3 Property Images Bucket
        bucket_name = f'uni-prop-{stage}-images-{Stack.of(self).account}-{Stack.of(self).region}'
        common_bucket_properties = {
            'removal_policy': RemovalPolicy.DESTROY,
            'auto_delete_objects': True,
            'block_public_access': s3.BlockPublicAccess.BLOCK_ALL,
            'encryption': s3.BucketEncryption.S3_MANAGED,
            'enforce_ssl': True,
        }

        # Prod environment requires S3 access logging while other environments do not.
        if stage == STAGE.prod.name:
            access_logs_bucket = s3.Bucket(
                self,
                'UnicornPropertiesAccessLogBucket',
                **common_bucket_properties,
                bucket_name=f'{bucket_name}-logs'
            )
            self.images_bucket = s3.Bucket(
                self, 
                'UnicornPropertiesImagesBucket',
                **common_bucket_properties,
                bucket_name=f'uni-prop-{stage}-images-{Stack.of(self).account}-{Stack.of(self).region}',
                server_access_logs_bucket=access_logs_bucket,
                server_access_logs_prefix='access-logs'
            )
        else:
            self.images_bucket = s3.Bucket(
                self, 
                'UnicornPropertiesImagesBucket',
                **common_bucket_properties,
                bucket_name=f'uni-prop-{stage}-images-{Stack.of(self).account}-{Stack.of(self).region}'
            )
            NagSuppressions.add_resource_suppressions(
                self.images_bucket, 
                [
                    {
                        'id': 'AwsSolutions-S1',
                        'reason': 'Access logs for images bucket not required in local or dev environments'
                    }
                ]
            )

        # SSM Parameter
        self.images_bucket_parameter = ssm.StringParameter(
            self,
            'UnicornPropertiesImagesBucketParam',
            parameter_name=f'/uni-prop/{stage}/ImagesBucket',
            string_value=self.images_bucket.bucket_name,
            description=f'Images bucket for {stage} environment.',
            simple_name=False
        )

        property_images_bucket = s3.Bucket.from_bucket_name(
            self,
            'propertyImagesBucket',
            'aws-serverless-developer-experience-workshop-assets'
        )
        
        s3deploy.BucketDeployment(
            self, 
            'DeployImages',
            sources=[
                s3deploy.Source.bucket(
                    property_images_bucket,
                    'property_images/property_images.zip'
                )
            ],
            destination_bucket=self.images_bucket,
            destination_key_prefix='/',
            retain_on_delete=False,
            extract=True
        )