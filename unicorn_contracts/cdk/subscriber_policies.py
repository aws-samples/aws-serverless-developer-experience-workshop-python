from typing import List
from constructs import Construct
from aws_cdk import Stack

from unicorn_shared import (
    UNICORN_NAMESPACES,
    STAGE,
    logsRetentionPeriod,
    eventBusName,
    isProd
)

import aws_cdk.aws_events as events
import aws_cdk.aws_iam as iam

class SubscriberPoliciesConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str, *, stage: STAGE, event_bus: events.EventBus, sources: List[UNICORN_NAMESPACES], **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        policy_statement = iam.PolicyStatement(
            principals=[iam.AccountRootPrincipal()],
            actions=[
                'events:PutRule',
                'events:DeleteRule',
                'events:DescribeRule',
                'events:DisableRule',
                'events:EnableRule',
                'events:PutTargets',
                'events:RemoveTargets',
            ],
            resources=[event_bus.event_bus_arn],
            
            conditions={
                'StringEquals': {
                    "events:source": list(map(lambda namespace: namespace.value, sources)),
                },
                'StringEqualsIfExists': {
                    'events:creatorAccount': Stack.of(self).account,
                },
                'Null': {
                    'events:source': "false",
                },
            }
        ).to_json()

        event_bus_policy = events.CfnEventBusPolicy(
            self,
            'ContractEventsBusPublishPolicy',
            statement_id=f'{event_bus.event_bus_name}-{stage.value}-policy',
            event_bus_name=event_bus.event_bus_name,
            statement=policy_statement
        )
