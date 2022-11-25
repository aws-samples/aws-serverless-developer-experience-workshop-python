# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import os
from unittest import TestCase

import boto3
import requests

"""
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test. 
"""


class TestApiGateway(TestCase):
    api_endpoint: str

    @classmethod
    def get_stack_name(cls) -> str:
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")   
        if not stack_name:
            raise Exception(
                "Cannot find env var AWS_SAM_STACK_NAME. \n"
                "Please setup this environment variable with the stack name where we are running integration tests."
            )

        return stack_name

    def setUp(self) -> None:
        """
        Based on the provided env variable AWS_SAM_STACK_NAME,
        here we use cloudformation API to find out what the HelloWorldApi URL is
        """
        stack_name = TestApiGateway.get_stack_name()

        client = boto3.client("cloudformation")

        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name}. \n" f'Please make sure stack with the name "{stack_name}" exists.'
            ) from e

        stacks = response["Stacks"]

        stack_outputs = stacks[0]["Outputs"]
        api_outputs = [output for output in stack_outputs if output["OutputKey"] == "ApiUrl"]
        print(api_outputs)
        self.assertTrue(api_outputs, f"Cannot find output ApiUrl in stack {stack_name}")

        self.api_endpoint = api_outputs[0]["OutputValue"]

    def test_create_contract(self):
        """
        Call the API Gateway endpoint and check the response
        """
        
        payload = {
            "address": {
                "country": "USA",
                "city": "Anytown",
                "street": "Main Street",
                "number": 111
            },
            "seller_name": "John Smith",
            "property_id": "usa/anytown/main-street/111"
        }
        response = requests.post(f'{self.api_endpoint}contracts', json = payload)
        self.assertEqual(response.status_code, 200)
        # https://stackoverflow.com/questions/20050913/python-unittests-assertdictcontainssubset-recommended-alternative
        # self.assertDictEqual(response.json(), response.json() | {"message": "New contract has been successfully uploaded"})
    
    def test_create_contract_wrong_payload(self):
        """
        Call the API Gateway endpoint and check the response
        """
        
        payload = {
            "add": "St.1 , Building 10",
            "sell": "John Smith",
            "prop": "4781231c-bc30-4f30-8b30-7145f4dd1adb"
        }
        response = requests.post(f'{self.api_endpoint}contracts', json = payload)
        self.assertEqual(response.status_code, 400)
