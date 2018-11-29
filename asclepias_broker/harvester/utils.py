# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester utilities."""

from datetime import datetime

from invenio_cache import current_cache


class HarvesterHistory:
    """."""

    def __init__(self, prefix: str):
        """."""
        self.prefix = prefix

    def get(self, key: str) -> datetime:
        """."""
        return current_cache.get(f'{self.prefix}:{key}')

    def set(self, key: str, value: datetime = None):
        """."""
        return current_cache.set(
            f'{self.prefix}:{key}', value or datetime.now(), timeout=-1)
