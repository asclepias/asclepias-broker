# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Asynchronous tasks."""

from celery import shared_task

from ..graph.models import GroupRelationship
from ..utils import chunks
from .indexer import build_doc, index_documents


@shared_task(ignore_result=True)
def reindex_all_relationships():
    """Reindex all relationship documents."""
    q = GroupRelationship.query.yield_per(1000)
    for chunk in chunks(q, 1000, q.count()):
        index_documents(map(build_doc, chunk), bulk=True)
