# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
from datetime import datetime, timedelta
from time import sleep, time

import boto3
from pathlib import Path

from yaml import load
# From: https://pyyaml.org/wiki/PyYAMLDocumentation
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

DEFAULT_SAM_CONFIG_FILE = Path(__file__).parent.parent.parent.resolve() / 'samconfig.yaml'
STACK_OUTPUTS = dict()

cfn = boto3.client("cloudformation")


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



################################################################################

cwl = boto3.client('logs')

def get_cw_logs_value(eb_log_group, property_id) -> str:
    startTime = int((datetime.today() - timedelta(hours=5)).timestamp())
    endTime = int(datetime.now().timestamp())

    query = f'fields @message | filter detail.property_id = "{property_id}" | limit 1'
    # query = 'fields @message | filter detail.property_id = "usa/anytown/main-street/2156" | limit 1'
    print(query)
    res = cwl.start_query(logGroupName=eb_log_group, startTime=startTime, endTime=endTime,
                        queryString=query)

    timeout = time() + 60*5   # 5 minutes from now
    response = None
    while response is None or response['status'] == 'Running':
        if time() > timeout:
            raise Exception('Timed out while waiting for CW Logs results')
        sleep(1)
        response = cwl.get_query_results(queryId=res['queryId'])

    # log_entry = [x for x in filter(lambda r: r['field'] == '@message', response['results'][0])][0]
    return response['results']


if __name__ == '__main__':
    result = get_cw_logs_value('uni-prop-local-contract-UnicornContractsCatchAllLogGroup-Cp7ilmQQw4o7', 'usa/anytown/main-street/2156')
    print(json.loads(result[0][0]['value']))