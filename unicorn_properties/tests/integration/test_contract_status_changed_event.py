# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import json
from time import sleep
from datetime import datetime

import boto3
from unittest import TestCase

from . import get_stack_output


evb = boto3.client('events')
ddb = boto3.client('dynamodb')


properties_bus = get_stack_output('UnicornPropertiesEventBusName')


def send_contract_status_changed(property_id, contract_id, contract_status):
    return evb.put_events(Entries=[{
        'Source': 'unicorn.contracts',
        'DetailType': 'ContractStatusChanged',
        'EventBusName': properties_bus,
        'Detail': json.dumps({
            'contract_last_modified_on': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'property_id': property_id,
            'contract_id': contract_id,
            'contract_status': contract_status}),
    }])


def send_publication_approval_requested(property_id, contract_id, contract_status):
    return evb.put_events(Entries=[{
        'Source': 'unicorn.web',
        'DetailType': 'PublicationApprovalRequested',
        'EventBusName': properties_bus,
        'Detail': json.dumps({
            'contract_last_modified_on': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'property_id': property_id,
            'contract_id': contract_id,
            'contract_status': contract_status}),
    }])



# {
#     "DetailType": "PublicationApprovalRequested",
#     "Source": "unicorn.properties.web",
#     "EventBusName": "UnicornPropertiesEventBus-Local",
#     "Detail": "{\"property_id\":\"usa/anytown/main-street/222\",\"address\":{\"country\":\"USA\",\"city\":\"Anytown\",\"street\":\"Main Street\",\"number\":222},\"description\":\"This classic Anytown estate comes with a covetable lake view. The romantic and comfortable backyard is the perfect setting for unicorn get-togethers. The open concept Main Stable is fully equipped with all the desired amenities. Second floor features 6 straw bales including large Rainbow Suite with private training pool terrace and Jr Sparkles Suite.\",\"contract\":\"sale\",\"listprice\":200,\"currency\":\"SPL\",\"images\":[\"prop1_exterior1.jpg\",\"prop1_interior1.jpg\",\"prop1_interior2.jpg\",\"prop1_interior3.jpg\"]}"
# }

# x = {
#     "property_id":"usa/anytown/main-street/222",
#     "address":{
#         "country":"USA",
#         "city":"Anytown",
#         "street":"Main Street",
#         "number":222
#     },
#     "description":"This classic Anytown estate comes with a covetable lake view. The romantic and comfortable backyard is the perfect setting for unicorn get-togethers. The open concept Main Stable is fully equipped with all the desired amenities. Second floor features 6 straw bales including large Rainbow Suite with private training pool terrace and Jr Sparkles Suite.",
#     "contract":"sale",
#     "listprice":200,
#     "currency":"SPL",
#     "images":[
#         "prop1_exterior1.jpg",
#         "prop1_interior1.jpg",
#         "prop1_interior2.jpg",
#         "prop1_interior3.jpg"
#     ]
# }




class TestCreateContract(TestCase):
    properties_bus: str
    contract_status_table_name: str

    def setUp(self) -> None:
        self.contract_status_table_name = get_stack_output('ContractStatusTableName')


    def test_contract_status_draft(self):
        evp_resp = send_contract_status_changed(property_id='usa/anytown/main-street/111',
                                                contract_id='f2bedc80-3dc8-4544-9140-9b606d71a6ee',
                                                contract_status='DRAFT')

        sleep(2)

        ddb_resp = ddb.get_item(TableName=self.contract_status_table_name,
                                Key={'property_id': {'S': 'usa/anytown/main-street/111'}})
        
        assert ddb_resp['Item']['contract_status']['S'] == 'DRAFT'
        assert ddb_resp['Item'].get('sfn_wait_approved_task_token', None) is None

    def test_contract_status_approved(self):
        evp_resp = send_contract_status_changed(property_id='usa/anytown/main-street/111',
                                                contract_id='f2bedc80-3dc8-4544-9140-9b606d71a6ee',
                                                contract_status='APPROVED')

        sleep(2)

        ddb_resp = ddb.get_item(TableName=self.contract_status_table_name,
                                Key={'property_id': {'S': 'usa/anytown/main-street/111'}})
        
        assert ddb_resp['Item']['contract_status']['S'] == 'APPROVED'
        assert ddb_resp['Item'].get('sfn_wait_approved_task_token', None) is not None
