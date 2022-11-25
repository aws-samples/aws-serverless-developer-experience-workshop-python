# coding: utf-8
import pprint
import re  # noqa: F401

import six
from enum import Enum

class PublicationApprovalRequested(object):


    _types = {
        'city': 'str',
        'contract': 'str',
        'country': 'str',
        'currency': 'str',
        'description': 'str',
        'images': 'list[str]',
        'listprice': 'float',
        'number': 'float',
        'property_id': 'str',
        'street': 'str'
    }

    _attribute_map = {
        'city': 'city',
        'contract': 'contract',
        'country': 'country',
        'currency': 'currency',
        'description': 'description',
        'images': 'images',
        'listprice': 'listprice',
        'number': 'number',
        'property_id': 'property_id',
        'street': 'street'
    }

    def __init__(self, city=None, contract=None, country=None, currency=None, description=None, images=None, listprice=None, number=None, property_id=None, street=None):  # noqa: E501
        self._city = None
        self._contract = None
        self._country = None
        self._currency = None
        self._description = None
        self._images = None
        self._listprice = None
        self._number = None
        self._property_id = None
        self._street = None
        self.discriminator = None
        self.city = city
        self.contract = contract
        self.country = country
        self.currency = currency
        self.description = description
        self.images = images
        self.listprice = listprice
        self.number = number
        self.property_id = property_id
        self.street = street


    @property
    def city(self):

        return self._city

    @city.setter
    def city(self, city):


        self._city = city


    @property
    def contract(self):

        return self._contract

    @contract.setter
    def contract(self, contract):


        self._contract = contract


    @property
    def country(self):

        return self._country

    @country.setter
    def country(self, country):


        self._country = country


    @property
    def currency(self):

        return self._currency

    @currency.setter
    def currency(self, currency):


        self._currency = currency


    @property
    def description(self):

        return self._description

    @description.setter
    def description(self, description):


        self._description = description


    @property
    def images(self):

        return self._images

    @images.setter
    def images(self, images):


        self._images = images


    @property
    def listprice(self):

        return self._listprice

    @listprice.setter
    def listprice(self, listprice):


        self._listprice = listprice


    @property
    def number(self):

        return self._number

    @number.setter
    def number(self, number):


        self._number = number


    @property
    def property_id(self):

        return self._property_id

    @property_id.setter
    def property_id(self, property_id):


        self._property_id = property_id


    @property
    def street(self):

        return self._street

    @street.setter
    def street(self, street):


        self._street = street

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
        if issubclass(PublicationApprovalRequested, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        return self.to_str()

    def __eq__(self, other):
        if not isinstance(other, PublicationApprovalRequested):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

