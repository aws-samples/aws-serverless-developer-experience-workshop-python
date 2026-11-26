# coding: utf-8
import pprint
import re  # noqa: F401

import six
from enum import Enum


class Address(object):
    _types = {
        "country": "str",
        "city": "str",
        "street": "str",
        "number": "int",
    }

    _attribute_map = {
        "country": "country",
        "city": "city",
        "street": "street",
        "number": "number",
    }

    def __init__(
        self,
        country=None,
        city=None,
        street=None,
        number=None,
    ):  # noqa: E501
        self._country = None
        self._city = None
        self._street = None
        self._number = None
        self.discriminator = None
        self.country = country
        self.city = city
        self.street = street
        self.number = number

    @property
    def country(self):
        return self._country

    @country.setter
    def country(self, country):
        self._country = country

    @property
    def city(self):
        return self._city

    @city.setter
    def city(self, city):
        self._city = city

    @property
    def street(self):
        return self._street

    @street.setter
    def street(self, street):
        self._street = street

    @property
    def number(self):
        return self._number

    @number.setter
    def number(self, number):
        self._number = number

    def to_dict(self):
        result = {}

        for attr, _ in six.iteritems(self._types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(lambda x: x.to_dict() if hasattr(x, "to_dict") else x, value))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(
                    map(
                        lambda item: (item[0], item[1].to_dict()) if hasattr(item[1], "to_dict") else item,
                        value.items(),
                    )
                )
            else:
                result[attr] = value
        if issubclass(Address, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        return self.to_str()

    def __eq__(self, other):
        if not isinstance(other, Address):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
