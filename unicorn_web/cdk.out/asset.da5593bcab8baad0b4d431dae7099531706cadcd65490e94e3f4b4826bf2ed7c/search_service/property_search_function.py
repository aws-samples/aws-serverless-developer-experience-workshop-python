# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from aws_lambda_powertools.logging import Logger, correlation_paths
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.event_handler import content_types
from aws_lambda_powertools.event_handler.api_gateway import ApiGatewayResolver, Response
from aws_lambda_powertools.event_handler.exceptions import NotFoundError, InternalServerError


# Initialise Environment variables
if (SERVICE_NAMESPACE := os.environ.get('SERVICE_NAMESPACE')) is None:
    raise InternalServerError('SERVICE_NAMESPACE environment variable is undefined')
if (DYNAMODB_TABLE := os.environ.get('DYNAMODB_TABLE')) is None:
    raise InternalServerError('DYNAMODB_TABLE environment variable is undefined')

# Initialise PowerTools
logger: Logger = Logger()
tracer: Tracer = Tracer()
metrics: Metrics = Metrics()

# Initialise boto3 clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)  # type: ignore

app = ApiGatewayResolver()


@app.get('/search/<country>/<city>')
@tracer.capture_method
def list_properties_by_city(country, city):
    """Queries database for all properties within a city within a country; requires full city name

    Parameters
    ----------
    country : The country in which to search for Unicorn properties - example: "USA"
    city : The city in which to search for Unicorn properties - example: "Anytown"

    Returns
    -------
    The list of Unicorn properties for this country/city combination
    """
    logger.info(f"List properties by city: country = {country}; city = {city}")
    key_condition = Key('PK').eq(f"PROPERTY#{country}#{city}")

    return query_dynamodb(key_condition)


@app.get('/search/<country>/<city>/<street>')
@tracer.capture_method
def list_properties_by_street(country, city, street):
    """Queries database for all properties within a street within a city; requires full street name

    Parameters
    ----------
    country : The country in which to search for Unicorn properties - example: "USA"
    city : The city in which to search for Unicorn properties - example: "Anytown"
    street : The street in which to search for Unicorn properties - example: "Main Street"

    Returns
    -------
    The list of Unicorn properties for this country/city/street combination
    """
    logger.info(f"List properties by street: country = {country}; city = {city}; street = {street}")
    key_condition = Key('PK').eq(f"PROPERTY#{country}#{city}") & Key('SK').begins_with(f"{street}#")

    return query_dynamodb(key_condition)


@tracer.capture_method
def query_dynamodb(key_condition):
    """Internal utility function to query DynamoDB for a set of fields given a key condition

    Parameters
    ----------
    key_condition : DynamoDB API's key condition to parametrize the query.
        For example `Key('PK').eq("PROPERTY#' + country + '#' + city)`

    Returns
    -------
    DynamoDB query API response scoped to the Items returned by the API, removing any other overhead in the response

    """
    response = table.query(
        ProjectionExpression='country, city, street, #NUM, contract, listprice, currency',
        ExpressionAttributeNames={'#NUM': 'number'},
        KeyConditionExpression=key_condition,
        FilterExpression=Attr('status').eq('APPROVED'),
    )
    return response['Items']


@app.get("/properties/<country>/<city>/<street>/<number>")
@tracer.capture_method
def property_details(country, city, street, number):
    """Get all property details for a single item in DynamoDB

    Parameters
    ----------
    country : The country for this specific Unicorn property - example: "USA"
    city : The city for this specific Unicorn property - example: "Anytown"
    street : The street for this specific Unicorn property - example: "Main Street"
    number :  The house number for this specific Unicorn property - example: "123"

    Returns
    -------
    One specific property item related to the specified address
    """
    logger.info(f"Get property details for: country = {country}; city = {city}; street = {street}; number = {number}")
    response = table.get_item(
        Key={
            'PK': f"PROPERTY#{country}#{city}",
            'SK': f"{street}#{number}",
        }
    )
    if 'Item' not in response:
        logger.exception(f"No property found at address {(country, city, street, number)}")
        raise NotFoundError
    item = response['Item']
    status = item['status']
    if status != 'APPROVED':
        status_message = f"Property is not approved; current status: {status}"
        logger.exception(status_message)
        raise NotFoundError(status_message)
    item.pop("PK")
    item.pop("SK")
    return item


@app.exception_handler(ClientError)
def handle_service_error(ex: ClientError):
    """Handles any error coming from a remote service request made through Boto3 (ClientError)

    Parameters
    ----------
    ex : Boto3 error occuring during an AWS API call anywhere in this Lambda function

    Returns
    -------
    Specific HTTP error code to be returned to the client as well as a friendly error message
    """
    error_code = ex.response['Error']['Code']
    http_status_code = ex.response['ResponseMetadata']['HTTPStatusCode']
    error_message = ex.response['Error']['Message']
    logger.exception(f"EXCEPTION {error_code} ({http_status_code}): {error_message}")
    return Response(
        status_code=http_status_code,
        content_type=content_types.TEXT_PLAIN,
        body=error_code
    )


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)  # type: ignore
@tracer.capture_lambda_handler  # type: ignore
@metrics.log_metrics
def lambda_handler(event, context):
    """Main entry point for PropertyWeb lambda function

    Parameters
    ----------
    event : API Gateway Lambda Proxy Request
        The event passed to the function.
    context : AWS Lambda Context
        The context for the Lambda function.

    Returns
    -------
    API Gateway Lambda Proxy Response
        HTTP response object with Contract and Property ID
    """
    # logger.info(event)
    return app.resolve(event, context)
