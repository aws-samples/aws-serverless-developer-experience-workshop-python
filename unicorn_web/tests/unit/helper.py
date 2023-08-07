import os
import json
import inspect


TABLE_NAME = 'table1'


def load_event(filename):
    file_dir = os.path.dirname(os.path.abspath((inspect.stack()[0])[1]))
    print(file_dir)
    with open(os.path.join(file_dir, filename), 'r') as f:
        return json.load(f)


def return_env_vars_dict(k={}):
    d = {
        "DYNAMODB_TABLE": TABLE_NAME,
        "EVENT_BUS": "test-eventbridge",
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "SERVICE_NAMESPACE":"unicorn.web",
        "POWERTOOLS_SERVICE_NAME":"unicorn.web",
        "POWERTOOLS_TRACE_DISABLED":"true",
        "POWERTOOLS_LOGGER_LOG_EVENT":"true",
        "POWERTOOLS_LOGGER_SAMPLE_RATE":"0.1",
        "POWERTOOLS_METRICS_NAMESPACE":"unicorn.web",
        "LOG_LEVEL":"INFO"
    }
    d.update(k)
    return d


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
        'status': 'NEW',
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
