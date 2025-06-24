# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from enum import Enum
from aws_cdk import App

class STAGE(str, Enum):
    LOCAL = 'local'
    DEV = 'dev'
    PROD = 'prod'

class UNICORN_NAMESPACES(str, Enum):
    CONTRACTS = 'unicorn.contracts'
    PROPERTIES = 'unicorn.properties'
    WEB = 'unicorn.web'

def is_valid_stage(stage) -> bool:
    return stage in list(STAGE)

def get_stage_from_context(app: App) -> STAGE:
    stage_from_context = app.node.try_get_context('stage')
    
    if stage_from_context:
        if not is_valid_stage(stage_from_context):
            valid_stages = ', '.join([s.value for s in STAGE])
            raise ValueError(f'Invalid stage "{stage_from_context}". Must be one of: {valid_stages}')
        return STAGE(stage_from_context)
    
    return STAGE.LOCAL