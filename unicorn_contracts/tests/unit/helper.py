# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import inspect
import json 

TABLE_NAME = 'table1'


def load_event(filename):
    file_dir = os.path.dirname(os.path.abspath((inspect.stack()[0])[1]))
    print(file_dir)

    with open(os.path.join(file_dir, filename), 'r') as f:
        return json.load(f)


def return_env_vars_dict(k=None):
    if k is None:
        k = {}

    env_dict = {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "DYNAMODB_TABLE": TABLE_NAME,
        "EVENT_BUS": "test-eventbridge",
        "LOG_LEVEL":"INFO",
        "POWERTOOLS_LOGGER_LOG_EVENT":"true",
        "POWERTOOLS_LOGGER_SAMPLE_RATE":"0.1",
        "POWERTOOLS_METRICS_NAMESPACE":"unicorn.contracts",
        "POWERTOOLS_SERVICE_NAME":"unicorn.contracts",
        "POWERTOOLS_TRACE_DISABLED":"true",
        "SERVICE_NAMESPACE": "unicorn.contracts",
    }

    env_dict |= k

    return env_dict


def create_ddb_table_contracts(dynamodb):
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
            },
        ],
        ProvisionedThroughput={
                'ReadCapacityUnits':1,
                'WriteCapacityUnits':1
        }
    )
    table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
    return table


def create_ddb_table_contracts_with_entry(dynamodb):
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
            },
        ],
        ProvisionedThroughput={
                'ReadCapacityUnits':1,
                'WriteCapacityUnits':1
        }
    )
    table.meta.client.get_waiter('table_exists').wait(TableName=TABLE_NAME)
    contract = {
        "property_id": "usa/anytown/main-street/123",  # PK
        "contact_created": "01/08/2022 20:36:30",
        "contract_last_modified_on": "01/08/2022 20:36:30",
        "contract_id": "11111111",
        "address": {
            "country": "USA",
            "city": "Anytown",
            "street": "Main Street",
            "number": 123
        },
        "seller_name": "John Smith",
        "contract_status": "DRAFT",
    }
    table.put_item(Item=contract)
    return table
