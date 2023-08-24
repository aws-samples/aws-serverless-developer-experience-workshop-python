# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from unittest import TestCase
import requests

from . import get_stack_output


class TestUpdateContract(TestCase):
    api_endpoint: str

    def setUp(self) -> None:
        self.api_endpoint = get_stack_output('ApiUrl')


    # NOTE: This test is not working as it supposed to.
    #       Need a way for OpenApi Spec to validate extra keys on payload
    def test_update_existing_contract_invalid_payload_1(self):
        payload = {
            "property_id": "usa/anytown/main-street/123",
            "add": "St.1 , Building 10",
            "sell": "John Smith",
            "prop": "4781231c-bc30-4f30-8b30-7145f4dd1adb"
        }

        response = requests.put(f'{self.api_endpoint}contract', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), response.json() | {"message": "OK"})

    def test_update_existing_contract_valid_payload(self):
        payload = payload = {
            "property_id": "usa/anytown/main-street/123"
        }

        response = requests.put(f'{self.api_endpoint}contract', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), response.json() | {"message": "OK"})

    def test_update_missing_contract_invalid_payload_1(self):
        payload = {
            "add": "St.1 , Building 10",
            "sell": "John Smith",
            "prop": "4781231c-bc30-4f30-8b30-7145f4dd1adb"
        }

        response = requests.put(f'{self.api_endpoint}contract', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), response.json() | {"message": "Invalid request body"})

    def test_update_missing_contract_valid_payload(self):
        payload = {
            "property_id": "usa/some_other_town/street/878828"
        }

        response = requests.put(f'{self.api_endpoint}contract', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), response.json() | {"message": "OK"})
