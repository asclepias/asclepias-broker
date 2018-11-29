# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester tasks."""

from typing import List, Tuple

from celery import shared_task
from invenio_db import db

from ..graph.api import get_group_from_id
from .proxies import current_harvester


@shared_task(ignore_result=True)
def harvest_metadata_identifier(identifier: str, scheme: str):
    """."""
    for harvester in current_harvester.metadata_harvesters.values():
        if harvester.can_harvest(identifier, scheme):
            harvester.harvest(identifier, scheme)


@shared_task(ignore_result=True)
def harvest_metadata(identifiers: List[Tuple[str, str]], eager: bool = False):
    """."""
    identifiers_to_harvest = {(i, v) for i, v in identifiers}

    # Expand provided identifiers to their Identity groups
    for value, scheme in identifiers:
        id_group = get_group_from_id(value, scheme)
        if id_group:
            identifiers_to_harvest |= \
                {(i.value, i.scheme) for i in id_group.identifiers}
    for value, scheme in identifiers_to_harvest:
        task = harvest_metadata_identifier.s(value, scheme)
        if eager:
            task.apply(throw=True)
        else:
            task.apply_async()


@shared_task(ignore_result=True)
def harvest_events(harvester_ids: List[str], eager: bool = False):
    """."""
    for h in harvester_ids:
        with db.session.begin_nested():
            harvester = current_harvester.event_harvesters[h]
            harvester.harvest(eager=eager)
        db.session.commit()
