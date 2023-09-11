# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json 
from pathlib import Path


TABLE_NAME = 'table1'
EVENTBUS_NAME = 'test-eventbridge'
SQS_QUEUE_NAME = 'test_sqs'
EVENTS_DIR = Path(__file__).parent / 'events'


def load_event(filename):
    return json.load(open(EVENTS_DIR / f'{filename}.json', 'r'))


def return_env_vars_dict(k=None):
    if k is None:
        k = {}

    env_dict = {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "EVENT_BUS": EVENTBUS_NAME,
        "DYNAMODB_TABLE": TABLE_NAME,
        "SERVICE_NAMESPACE": "unicorn.contracts",
        "POWERTOOLS_LOGGER_CASE": "PascalCase",
        "POWERTOOLS_SERVICE_NAME":"unicorn.contracts",
        "POWERTOOLS_TRACE_DISABLED":"true",
        "POWERTOOLS_LOGGER_LOG_EVENT":"true",
        "POWERTOOLS_LOGGER_SAMPLE_RATE":"0.1",
        "POWERTOOLS_METRICS_NAMESPACE":"unicorn.contracts",
        "LOG_LEVEL":"INFO",
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
        "contract_created": "01/08/2022 20:36:30",
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


def create_test_sqs_ingestion_queue(sqs):
    queue = sqs.create_queue(QueueName=SQS_QUEUE_NAME)
    return queue
