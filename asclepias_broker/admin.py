# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Admin model views for Asclepias broker."""

from __future__ import absolute_import, print_function

from flask_admin.contrib.sqla import ModelView

from .core.models import Identifier, Relationship
from .events.models import Event


class IdentifierModelView(ModelView):
    """ModelView for the Indentifier."""

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_display_all_relations = True

    column_list = (
        'id',
        'value',
        'scheme',
    )

    column_searchable_list = ('value',)


class RelationshipModelView(ModelView):
    """ModelView for the Relationship."""

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_display_all_relations = True

    column_list = (
        'id',
        'source_id',
        'target_id',
        'relation',
        'deleted',
        'source',
        'target',

    )


class EventModelView(ModelView):
    """ModelView for the Event."""

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    column_display_all_relations = True

    column_list = (
        'id',
        'user_id',
        'status',
        'payload',
    )

    column_searchable_list = ('payload',)


identifier_adminview = dict(
    model=Identifier,
    modelview=IdentifierModelView,
)


relationship_adminview = dict(
    model=Relationship,
    modelview=RelationshipModelView,
)


event_adminview = dict(
    model=Event,
    modelview=EventModelView,
)
