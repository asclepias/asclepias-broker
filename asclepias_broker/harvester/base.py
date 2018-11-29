# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester base classes."""


class MetadataHarvester:
    """."""

    def can_harvest(self, identifier: str, scheme: str) -> bool:
        """."""
        return NotImplementedError()

    def harvest(self, identifier: str, scheme: str):
        """."""
        return NotImplementedError()
