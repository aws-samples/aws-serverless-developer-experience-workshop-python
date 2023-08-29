# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import requests
from unittest import TestCase

from . import get_stack_output


class TestCreateContract(TestCase):
    api_endpoint: str

    def setUp(self) -> None:
        self.api_endpoint = get_stack_output('ApiUrl')


    def create_contract_invalid_payload_1(self):
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

    def test_create_contract_valid_payload_1(self):
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

        response = requests.put(f'{self.api_endpoint}contract', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), response.json() | {"message": "OK"})
