# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Asynchronous tasks."""

from typing import List

from celery import shared_task
from invenio_search import current_search

from ..graph.models import GroupRelationship
from ..utils import chunks
from .indexer import build_doc, index_documents


@shared_task(ignore_result=True)
def index_group_relationships(group_rel_ids: List[str]):
    """."""
    group_rels = GroupRelationship.query.filter(
        GroupRelationship.id.in_(group_rel_ids))
    index_documents(map(build_doc, group_rels), bulk=True)


@shared_task(ignore_result=True)
def reindex_all_relationships(destroy: bool = False, split: bool = True):
    """Reindex all relationship documents."""
    if destroy:
        list(current_search.delete(ignore=[400, 404]))
        list(current_search.create(ignore=[400, 404]))
    q = GroupRelationship.query.yield_per(1000)
    for chunk in chunks(q, 1000):
        if split:
            index_group_relationships.delay([str(gr.id) for gr in chunk])
        else:
            index_documents(map(build_doc, chunk), bulk=True)
