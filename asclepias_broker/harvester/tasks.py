# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester tasks."""

from typing import List, Optional, Tuple

from celery import shared_task
from invenio_db import db

from .proxies import current_harvester


@shared_task(ignore_result=True, max_retries=3, default_retry_delay=10 * 60)
def harvest_metadata_identifier(harvester: str, identifier: str, scheme: str):
    """."""
    try:
        h = current_harvester.metadata_harvesters[harvester]
        h.harvest(identifier, scheme)
    except Exception as exc:
        harvest_metadata_identifier.retry(exc=exc)


@shared_task(ignore_result=True)
def harvest_metadata(identifiers: Optional[List[Tuple[str, str]]],
                     eager: bool = False):
    """."""
    if identifiers:
        identifiers_to_harvest = ((i, v) for i, v in identifiers)
    else:  # use queue
        identifiers_to_harvest = current_harvester.metadata_queue.consume()
    for value, scheme in identifiers_to_harvest:
        for h_id, harvester in current_harvester.metadata_harvesters.items():
            if harvester.can_harvest(value, scheme):
                task = harvest_metadata_identifier.s(h_id, value, scheme)
                if eager:
                    task.apply(throw=True)
                else:
                    task.apply_async()


@shared_task(ignore_result=True)
def harvest_events(harvester_ids: List[str], eager: bool = False):
    """."""
    for h in harvester_ids:
        harvester = current_harvester.event_harvesters[h]
        if not eager:
            harvester.harvest(eager=eager)
        else:
            with db.session.begin_nested():
                harvester.harvest(eager=eager)
            db.session.commit()
