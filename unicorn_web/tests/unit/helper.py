# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
from pathlib import Path


TABLE_NAME = 'table1'
EVENTBUS_NAME = 'test-eventbridge'
SQS_QUEUE_NAME = 'test_sqs'
EVENTS_DIR = Path(__file__).parent / 'events'


def load_event(filename) -> dict:
    return json.load(open(EVENTS_DIR / f'{filename}.json', 'r'))


def return_env_vars_dict(k={}):
    if k is None:
        k = {}

    env_dict = {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "DYNAMODB_TABLE": TABLE_NAME,
        "EVENT_BUS": "test-eventbridge",
        "LOG_LEVEL":"INFO",
        "POWERTOOLS_LOGGER_LOG_EVENT":"true",
        "POWERTOOLS_LOGGER_SAMPLE_RATE":"0.1",
        "POWERTOOLS_METRICS_NAMESPACE":"unicorn.web",
        "POWERTOOLS_SERVICE_NAME":"unicorn.web",
        "POWERTOOLS_TRACE_DISABLED":"true",
        "SERVICE_NAMESPACE":"unicorn.web",
    }

    env_dict |= k

    return env_dict


def create_ddb_table_property_web(dynamodb):
    print("Creating Table Property Web")
    table = dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema= [
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'},
        ],
        ProvisionedThroughput={
                'ReadCapacityUnits':1,
                'WriteCapacityUnits':1
        }
    )
    table.meta.client.get_waiter('table_exists').wait(TableName='table1')
    table.put_item(Item={
        'PK': 'PROPERTY#usa#anytown',
        'SK': 'main-street#123',
        'country': 'USA',
        'city': 'Anytown',
        'street': 'Main Street',
        'number': '123',
        'description': 'Test Description',
        'contract': 'sale',
        'listprice': '200',
        'currency': 'USD',
        'images': [],
        'status': 'PENDING',
    })
    table.put_item(Item={
        'PK': 'PROPERTY#usa#anytown',
        'SK': 'main-street#124',
        'country': 'USA',
        'city': 'Anytown',
        'street': 'Main Street',
        'number': '124',
        'description': 'Test Description',
        'contract': 'sale',
        'listprice': '200',
        'currency': 'USD',
        'images': [],
        'status': 'APPROVED',
    })
    table.put_item(Item={
        'PK': 'PROPERTY#usa#anytown',
        'SK': 'main-street#125',
        'country': 'USA',
        'city': 'Anytown',
        'street': 'Main Street',
        'number': '125',
        'description': 'Test Description',
        'contract': 'sale',
        'listprice': '200',
        'currency': 'USD',
        'images': [],
        'status': 'DECLINED',
    })
    table.put_item(Item={
        'PK': 'PROPERTY#usa#anytown',
        'SK': 'main-street#126',
        'country': 'USA',
        'city': 'Anytown',
        'street': 'Main Street',
        'number': '126',
        'description': 'Test Description',
        'contract': 'sale',
        'listprice': '200',
        'currency': 'USD',
        'images': [],
        'status': 'PENDING',
    })
    return table


def create_test_eventbridge_bus(eventbridge):
    bus = eventbridge.create_event_bus(Name=EVENTBUS_NAME)
    return bus


def create_test_sqs_ingestion_queue(sqs):
    queue = sqs.create_queue(QueueName=SQS_QUEUE_NAME)
    return queue


def prop_id_to_pk_sk(property_id: str) -> dict[str, str]:
    country, city, street, number = property_id.split('/')
    pk_details = f"{country}#{city}".replace(' ', '-').lower()

    return {
        'PK': f"PROPERTY#{pk_details}",
        'SK': f"{street}#{str(number)}".replace(' ', '-').lower(),
    }
