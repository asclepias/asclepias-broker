# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2019 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Asynchronous tasks."""

from typing import List

from celery import chain, group, shared_task

from ..graph.models import GroupRelationship
from ..utils import chunks
from .indexer import build_doc, index_documents
from .utils import create_index, rollover_indices


@shared_task(ignore_result=True)
def index_group_relationships(group_rel_ids: List[str]):
    """Index multiple group relationships."""
    group_rels = GroupRelationship.query.filter(
        GroupRelationship.id.in_(group_rel_ids))
    index_documents(map(build_doc, group_rels), bulk=True)


@shared_task(ignore_result=True)
def rollover_task(keep_old_indices=1):
    """Rollover indices."""
    rollover_indices(keep_old_indices)


@shared_task(ignore_result=True)
def reindex_all_relationships(rollover: bool = True, split: bool = True,
                              keep_old_indices: int = 1):
    """Reindex all relationship documents."""
    index_name = create_index()
    q = GroupRelationship.query.yield_per(1000)
    tasks = []
    for chunk in chunks(q, 1000):
        if split:
            tasks.append(
                index_group_relationships.si([str(gr.id) for gr in chunk])
            )
        else:
            index_documents(map(build_doc, chunk), bulk=True)
    task = group(tasks)
    if rollover:
        task = chain(task, rollover_task.si(keep_old_indices))
    task.apply_async()
