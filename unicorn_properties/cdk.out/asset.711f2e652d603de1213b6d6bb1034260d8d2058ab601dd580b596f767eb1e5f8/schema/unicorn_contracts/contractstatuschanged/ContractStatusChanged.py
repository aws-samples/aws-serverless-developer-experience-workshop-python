# coding: utf-8
import pprint
import re  # noqa: F401

import six
from enum import Enum

class ContractStatusChanged(object):


    _types = {
        'contract_id': 'str',
        'contract_last_modified_on': 'str',
        'contract_status': 'str',
        'property_id': 'str'
    }

    _attribute_map = {
        'contract_id': 'contract_id',
        'contract_last_modified_on': 'contract_last_modified_on',
        'contract_status': 'contract_status',
        'property_id': 'property_id'
    }

    def __init__(self, contract_id=None, contract_last_modified_on=None, contract_status=None, property_id=None):  # noqa: E501
        self._contract_id = None
        self._contract_last_modified_on = None
        self._contract_status = None
        self._property_id = None
        self.discriminator = None
        self.contract_id = contract_id
        self.contract_last_modified_on = contract_last_modified_on
        self.contract_status = contract_status
        self.property_id = property_id


    @property
    def contract_id(self):

        return self._contract_id

    @contract_id.setter
    def contract_id(self, contract_id):


        self._contract_id = contract_id


    @property
    def contract_last_modified_on(self):

        return self._contract_last_modified_on

    @contract_last_modified_on.setter
    def contract_last_modified_on(self, contract_last_modified_on):


        self._contract_last_modified_on = contract_last_modified_on


    @property
    def contract_status(self):

        return self._contract_status

    @contract_status.setter
    def contract_status(self, contract_status):


        self._contract_status = contract_status


    @property
    def property_id(self):

        return self._property_id

    @property_id.setter
    def property_id(self, property_id):


        self._property_id = property_id

    def to_dict(self):
        result = {}

        for attr, _ in six.iteritems(self._types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        if issubclass(ContractStatusChanged, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        return self.to_str()

    def __eq__(self, other):
        if not isinstance(other, ContractStatusChanged):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

