# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester tasks."""

from typing import List, Optional
from uuid import uuid4
import datetime

from celery import shared_task
from invenio_db import db

from .proxies import current_harvester
from ..monitoring.models import ErrorMonitoring, HarvestMonitoring, HarvestStatus
from .cli import rerun_event

@shared_task(bind=True, ignore_result=True, max_retries=1, default_retry_delay=10 * 60)
def harvest_metadata_identifier(self, harvester: str, identifier: str, scheme: str,
                                event_uuid: str, providers: List[str] = None):
    """."""
    try:
        _set_event_status(event_uuid, HarvestStatus.Processing)
        h = current_harvester.metadata_harvesters[harvester]
        h.harvest(identifier, scheme, providers)
        _set_event_status(event_uuid, HarvestStatus.Done)
    except Exception as exc:
        db.session.rollback()
        _set_event_status(event_uuid, HarvestStatus.Error)
        payload = {'identifier':identifier, 'scheme': scheme, 'providers': providers}
        error_obj = ErrorMonitoring.getFromEvent(event_uuid)
        if not error_obj:
            error_obj = ErrorMonitoring(event_id = event_uuid, origin=self.__class__.__name__, error=repr(exc), n_retries=self.request.retries, payload=payload)
            db.session.add(error_obj)
        else:
            error_obj.n_retries += 1
        db.session.commit()
        self.retry(exc=exc)


@shared_task(ignore_result=True)
def harvest_metadata(identifiers: Optional[List[dict]] = None,
                     eager: bool = False):
    """."""
    if identifiers:
        identifiers_to_harvest = (dict(identifier=i, scheme=v, providers=None)
                                  for i, v in identifiers)
    else:  # use queue
        identifiers_to_harvest = current_harvester.metadata_queue.consume()
    for payload in identifiers_to_harvest:
        value = payload['identifier']
        scheme = payload['scheme']
        providers = payload['providers']
        for h_id, harvester in current_harvester.metadata_harvesters.items():
            if harvester.can_harvest(value, scheme, providers):
                if not HarvestMonitoring.isRecentlyAdded(identifier=value, scheme=scheme, harvester=harvester.__class__.__name__):
                    harvest_event_obj = HarvestMonitoring(identifier=value, scheme=scheme,harvester=harvester.__class__.__name__, status=HarvestStatus.New)
                    db.session.add(harvest_event_obj)
                    db.session.commit()
                    task = harvest_metadata_identifier.s(h_id, value, scheme,
                                                        str(harvest_event_obj.id), providers)
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

def _set_event_status(event_uuid, status):
    """Set the status of the Event."""
    event = HarvestMonitoring.get(event_uuid)
    event.status = status
    db.session.commit()

@shared_task(ignore_result=True)
def rerun_errors():
    two_days_ago = datetime.datetime.now() - datetime.timedelta(days = 2)
    resp = HarvestMonitoring.query.filter(HarvestMonitoring.status == HarvestStatus.Error, HarvestMonitoring.created > str(two_days_ago)).all()
    for event in resp:
        rerun_event(event, no_index=True, eager=False)