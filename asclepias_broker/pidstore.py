# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""PIDStore fetchers and minters."""

from invenio_pidstore.fetchers import FetchedPID


def relid_fetcher(dummy_record_uuid, data):
    """Fetch a relationship's ID."""
    return FetchedPID(
        provider=None,
        pid_type='relid',
        pid_value=str(data['ID']),
    )


def relid_minter(dummy_record_uuid, data):
    """Dummy minter."""
    return None
