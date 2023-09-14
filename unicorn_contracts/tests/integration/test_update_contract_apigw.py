# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from typing import List

from time import sleep
from random import randint

import requests
from unittest import TestCase

from . import get_stack_output, get_cw_logs_values, clean_ddb
from . import get_event_payload, override_payload_number


class TestUpdateContract(TestCase):
    api_endpoint: str
    eb_log_group: str
    contracts_table: str
    properties: List[str]

    def setUp(self) -> None:
        self.api_endpoint = get_stack_output('ApiUrl')
        self.eb_log_group = get_stack_output('UnicornContractsCatchAllLogGroupArn').rstrip(":*")
        self.contracts_table = get_stack_output('ContractsTableName')
        self.properties = list()

    def tearDown(self) -> None:
        for i in self.properties:
            clean_ddb(self.contracts_table, i)


    # NOTE: This test is not working as it supposed to.
    #       Need a way for OpenApi Spec to validate extra keys on payload
    # def test_update_existing_contract_invalid_payload_1(self):
    #     payload = get_event_payload('update_existing_contract_invalid_payload_1')

    #     response = requests.put(f'{self.api_endpoint}contracts', json=payload)
    #     self.assertEqual(response.status_code, 400)


    def test_update_existing_contract_valid_payload(self):
        prop_number = randint(1, 9999)
        payload = override_payload_number(get_event_payload('create_contract_valid_payload_1'), prop_number)

        # Call API to create new Contract
        response = requests.post(f'{self.api_endpoint}contracts', json=payload)
        self.properties.append(payload['property_id'])

        # Call API to update contract
        response = requests.put(f'{self.api_endpoint}contracts', json={'property_id': payload['property_id']})
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), response.json() | {"message": "OK"})

        sleep(10)
        try:
            events_contract_statuses = [e['detail']['contract_status'] 
                                        for e in get_cw_logs_values(self.eb_log_group, payload['property_id'])]
            events_contract_statuses.sort()
        except Exception:
            raise Exception(f'Unable to get EventBridge Event from CloudWatch Logs group {self.eb_log_group}')

        # self.assertTrue("APPROVED" in events_contract_statuses)
        self.assertListEqual(events_contract_statuses, ['APPROVED', 'DRAFT'])


    def test_update_missing_contract_invalid_payload_1(self):
        payload = {
            "add": "St.1 , Building 10",
            "sell": "John Smith",
            "prop": "4781231c-bc30-4f30-8b30-7145f4dd1adb"
        }

        response = requests.put(f'{self.api_endpoint}contracts', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), response.json() | {"message": "Invalid request body"})


    def test_update_missing_contract_valid_payload(self):
        payload = {
            "property_id": "usa/some_other_town/street/878828"
        }

        response = requests.put(f'{self.api_endpoint}contracts', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), response.json() | {"message": "OK"})
