# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Errors and exceptions."""

from invenio_rest.errors import RESTException


class PayloadValidationRESTError(RESTException):
    """Invalid payload error."""

    code = 400

    def __init__(self, error_message, code=None, **kwargs):
        """Initialize the PayloadValidation REST exception."""
        if code:
            self.code = code
        super(PayloadValidationRESTError, self).__init__(**kwargs)
        self.description = error_message
