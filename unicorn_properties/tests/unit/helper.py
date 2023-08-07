# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json

TABLE_NAME = "table1"

def load_event(filename):
    with open(filename) as f:
        data = json.load(f)
    return data


def return_env_vars_dict(k={}):
    d = {
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "CONTRACT_STATUS_TABLE": TABLE_NAME, 
            "EVENT_BUS": "test-eventbridge", 
            "POWERTOOLS_LOGGER_LOG_EVENT":"true",
            "POWERTOOLS_LOGGER_SAMPLE_RATE":"0.1",
            "POWERTOOLS_METRICS_NAMESPACE":"unicorn.contracts",
            "POWERTOOLS_SERVICE_NAME":"unicorn.contracts",
            "POWERTOOLS_TRACE_DISABLED":"true",
            "SERVICE_NAMESPACE": "unicorn.properties", 
        }
    d.update(k)
    return d


def create_ddb_table_properties(dynamodb):
    table = dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema= [
            {
               'AttributeName': 'property_id',
               'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'property_id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits':1,
            'WriteCapacityUnits':1,
        }
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='table1')
    return table
