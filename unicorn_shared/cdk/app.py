#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from aws_cdk import App
from app.unicorn_namespaces import UnicornNamespacesStack
from app.unicorn_images import UnicornImagesStack
from app.constructs.images_construct import STAGE

app = App()

UnicornNamespacesStack(app, 'uni-prop-namespaces', 
    description='Global namespaces for Unicorn Properties applications and services. This only needs to be deployed once.'
)

stages = [STAGE.local, STAGE.dev, STAGE.prod]
for stage in stages:
    UnicornImagesStack(app, f'uni-prop-{stage.name}-shared',
        description='Global namespaces for Unicorn Properties applications and services. This only needs to be deployed once.',
        stage=stage
    )

app.synth()