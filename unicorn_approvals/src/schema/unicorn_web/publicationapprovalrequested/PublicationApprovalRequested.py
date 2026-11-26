# coding: utf-8
import pprint
import re  # noqa: F401

import six
from enum import Enum
from schema.unicorn_web.publicationapprovalrequested.Address import Address  # noqa: F401,E501


class PublicationApprovalRequested(object):
    _types = {
        "property_id": "str",
        "status": "str",
        "description": "str",
        "address": "Address",
        "images": "list[str]",
    }

    _attribute_map = {
        "property_id": "property_id",
        "status": "status",
        "description": "description",
        "address": "address",
        "images": "images",
    }

    def __init__(
        self,
        property_id=None,
        status=None,
        description=None,
        address=None,
        images=None,
    ):  # noqa: E501
        self._property_id = None
        self._status = None
        self._description = None
        self._address = None
        self._images = None
        self.discriminator = None
        self.property_id = property_id
        self.status = status
        self.description = description
        self.address = address
        self.images = images

    @property
    def property_id(self):
        return self._property_id

    @property_id.setter
    def property_id(self, property_id):
        self._property_id = property_id

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, address):
        self._address = address

    @property
    def images(self):
        return self._images

    @images.setter
    def images(self, images):
        self._images = images

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
