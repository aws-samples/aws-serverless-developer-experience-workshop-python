# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from typing import Iterator

import json
from pathlib import Path

import boto3
from arnparse import arnparse
from yaml import load, Loader


#### CONSTANTS
DEFAULT_SAM_CONFIG_FILE = Path(__file__).parent.parent.parent.resolve() / 'samconfig.yaml'
STACK_OUTPUTS = dict()
EVENTS_DIR = Path(__file__).parent / 'events'


#### AWS SDK Objects
cfn = boto3.client('cloudformation')
cwl = boto3.client('logs')
ddb = boto3.client('dynamodb')


def get_stack_name(samconfig: Path | str = DEFAULT_SAM_CONFIG_FILE) -> str:
    with open(samconfig, 'r') as f:
        conf = load(f, Loader=Loader)
        stack_name = conf['default']['global']['parameters']['stack_name']

    return stack_name


def get_stack_output(output_name: str, stack_name: str = get_stack_name()) -> str:
    """
    Get the value of an output 
    """

    if not (outputs := STACK_OUTPUTS.get(stack_name, dict())):
        try:
            response = cfn.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(f"Cannot find stack {stack_name}. \n" f'Please make sure stack "{stack_name}" exists.') from e

        outputs = {o['OutputKey']: o['OutputValue'] for o in response["Stacks"][0]["Outputs"]}
        STACK_OUTPUTS[stack_name] = outputs

    try:
        return outputs[output_name]
    except KeyError as e:
        raise Exception(f"Unable to find Output {output_name} on stack {stack_name}") from e


def get_event_payload(file) -> dict:
    return json.load(open(EVENTS_DIR / f'{file}.json', 'r'))


def override_payload_number(p: dict, number: int) -> dict:
    p['address']['number'] = number
    a = p["address"]
    p['property_id'] = f'{a["country"]}/{a["city"]}/{a["street"]}/{a["number"]}'.replace(' ', '-').lower()
    return p


def get_cw_logs_values(eb_log_group_arn: str, property_id: str) -> Iterator[dict]:
    group_name = arnparse(eb_log_group_arn).resource

    # Get the CW LogStream with the latest log messages
    stream_response = cwl.describe_log_streams(logGroupName=group_name, orderBy='LastEventTime',descending=True,limit=3)
    latestlogStreamNames = [s["logStreamName"] for s in stream_response["logStreams"]]
    # Fetch log events from that stream
    responses = [cwl.get_log_events(logGroupName=group_name, logStreamName=name) for name in latestlogStreamNames] 

    # Filter log events that match the required `property_id`
    for response in responses:
        for event in response["events"]:
            if (ev := json.loads(event["message"])).get('detail', {}).get('property_id', '') == property_id:
                yield ev


def clean_ddb(table_name, property_id):
    ddb.delete_item(TableName=table_name, Key={ 'property_id': { 'S': property_id } })
