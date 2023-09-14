# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
from pathlib import Path


TABLE_NAME = 'table1'
EVENTBUS_NAME = 'test-eventbridge'
EVENTS_DIR = Path(__file__).parent / 'events'


def load_event(filename):
    return json.load(open(EVENTS_DIR / f'{filename}.json', 'r'))


def return_env_vars_dict(k={}):
    d = {
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "CONTRACT_STATUS_TABLE": TABLE_NAME, 
            "EVENT_BUS": EVENTBUS_NAME, 
            "SERVICE_NAMESPACE": "unicorn.properties", 
            "POWERTOOLS_SERVICE_NAME":"unicorn.properties",
            "POWERTOOLS_TRACE_DISABLED":"true",
            "POWERTOOLS_LOGGER_LOG_EVENT":"true",
            "POWERTOOLS_LOGGER_SAMPLE_RATE":"0.1",
            "POWERTOOLS_METRICS_NAMESPACE":"unicorn.properties",
            "LOG_LEVEL": "INFO",
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


def create_test_eventbridge_bus(eventbridge):
    bus = eventbridge.create_event_bus(Name=EVENTBUS_NAME)
    return bus
