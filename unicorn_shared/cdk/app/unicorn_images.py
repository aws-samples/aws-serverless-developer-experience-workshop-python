# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from aws_cdk import Stack, CfnOutput
from constructs import Construct
from app.constructs.images_construct import ImagesInfraConstruct, STAGE

class UnicornImagesStack(Stack):
    def __init__(self, scope: Construct, id: str, *, stage: STAGE, **kwargs):
        super().__init__(scope, id, **kwargs)

        images_infra = ImagesInfraConstruct(
            self,
            f'ImagesInfra-{stage.name}',
            stage=stage.name
        )

        # Images infrastructure Output
        CfnOutput(self, f'ImageUploadBucketName-{stage.name}',
            description=f'S3 bucket for property images ({stage.name})',
            value=images_infra.images_bucket.bucket_name
        )