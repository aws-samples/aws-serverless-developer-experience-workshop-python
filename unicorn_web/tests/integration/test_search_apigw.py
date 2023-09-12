# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from typing import List

from time import sleep
from random import randint

import requests
from unittest import TestCase

from . import get_stack_output, get_cw_logs_values, clean_ddb
from . import get_event_payload, override_payload_number


class TestCreateContract(TestCase):
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


    def test_create_contract_invalid_payload_1(self):
        """
        Call the API Gateway endpoint and check the response
        """
        
        payload = get_event_payload('create_contract_invalid_payload_1')
        response = requests.post(f'{self.api_endpoint}contracts', json = payload)
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), response.json() | {"message": "Invalid request body"})


    def test_create_contract_valid_payload_1(self):
        prop_number = randint(1, 9999)
        payload = override_payload_number(get_event_payload('create_contract_valid_payload_1'), prop_number)

        # Call API to create new Contract
        response = requests.post(f'{self.api_endpoint}contracts', json=payload)
        self.properties.append(payload['property_id'])

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), response.json() | {"message": "OK"})

        sleep(5)
        try:
            eb_event = next(get_cw_logs_values(self.eb_log_group, payload['property_id']))
        except Exception:
            raise Exception(f'Unable to get EventBridge Event from CloudWatch Logs group {self.eb_log_group}')

        self.assertEqual(eb_event['detail']['contract_status'], "DRAFT")
