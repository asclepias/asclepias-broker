# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Schema utilities."""

from marshmallow import post_load


def to_model(model_cls):
    """Marshmallow schema decorator for creating SQLAlchemy models."""
    def inner(Cls):
        class ToModelSchema(Cls):

            def __init__(self, *args, check_existing=False, **kwargs):
                kwargs.setdefault('context', {})
                kwargs['context'].setdefault('check_existing', check_existing)
                super().__init__(*args, **kwargs)

            @post_load
            def to_model(self, data):
                if self.context.get('check_existing'):
                    return model_cls.get(**data) or model_cls(**data)
                return model_cls(**data)
        return ToModelSchema
    return inner
