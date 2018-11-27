# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Asynchronous tasks."""

from celery import shared_task
from invenio_search import current_search

from ..graph.models import GroupRelationship
from ..utils import chunks
from .indexer import build_doc, index_documents


@shared_task(ignore_result=True)
def reindex_all_relationships(destroy: bool = False):
    """Reindex all relationship documents."""
    if destroy:
        list(current_search.delete(ignore=[400, 404]))
        list(current_search.create(ignore=[400, 404]))
    q = GroupRelationship.query.yield_per(1000)
    for chunk in chunks(q, 1000):
        index_documents(map(build_doc, chunk), bulk=True)
