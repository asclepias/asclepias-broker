# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester base classes."""

from typing import List


class MetadataHarvester:
    """."""

    def can_harvest(self, identifier: str, scheme: str,
                    providers: List[str]) -> bool:
        """."""
        return NotImplementedError()

    def harvest(self, identifier: str, scheme: str,
                providers: List[str]):
        """."""
        return NotImplementedError()
