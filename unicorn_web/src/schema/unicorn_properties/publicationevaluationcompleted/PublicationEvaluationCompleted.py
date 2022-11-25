# coding: utf-8
import pprint
import re  # noqa: F401

import six
from enum import Enum

class PublicationEvaluationCompleted(object):


    _types = {
        'evaluation_result': 'str',
        'property_id': 'str'
    }

    _attribute_map = {
        'evaluation_result': 'evaluation_result',
        'property_id': 'property_id'
    }

    def __init__(self, evaluation_result=None, property_id=None):  # noqa: E501
        self._evaluation_result = None
        self._property_id = None
        self.discriminator = None
        self.evaluation_result = evaluation_result
        self.property_id = property_id


    @property
    def evaluation_result(self):

        return self._evaluation_result

    @evaluation_result.setter
    def evaluation_result(self, evaluation_result):


        self._evaluation_result = evaluation_result


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
        if issubclass(PublicationEvaluationCompleted, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        return self.to_str()

    def __eq__(self, other):
        if not isinstance(other, PublicationEvaluationCompleted):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

