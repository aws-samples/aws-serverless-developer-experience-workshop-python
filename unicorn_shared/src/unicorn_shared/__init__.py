from enum import Enum
from aws_cdk import (
    aws_logs as logs
)


class UNICORN_NAMESPACES(Enum):
    CONTRACTS = 'unicorn.contracts'
    PROPERTIES = 'unicorn.properties'
    WEB = 'unicorn.web'


class STAGE(Enum):
    local = 'local'
    dev = 'dev'
    prod = 'prod'


def isProd(stage: STAGE) -> bool:
    return stage == STAGE.prod


def logsRetentionPeriod(stage: STAGE) -> logs.RetentionDays:
    match stage:
        case STAGE.local:
            return logs.RetentionDays.ONE_DAY
        case STAGE.dev:
            return logs.RetentionDays.ONE_WEEK
        case STAGE.prod:
            return logs.RetentionDays.TWO_WEEKS
        case _:
            return logs.RetentionDays.ONE_DAY


def eventBusName(stage: STAGE, namespace: UNICORN_NAMESPACES) -> str:
    match namespace:
        case UNICORN_NAMESPACES.CONTRACTS:
            return f'UnicornContractsBus-{stage.value}'
        case UNICORN_NAMESPACES.PROPERTIES:
            return f'UnicornPropertiesBus-{stage.value}'
        case UNICORN_NAMESPACES.WEB:
            return f'UnicornWebBus-{stage.value}'
        case _:
            raise Exception(f'Error generatinig Event Bus Name Unknown namespace: {namespace}')
        