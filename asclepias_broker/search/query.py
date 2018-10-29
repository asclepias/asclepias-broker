# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Search utilities."""

from typing import Dict

from elasticsearch_dsl import Q
from elasticsearch_dsl.query import Range
from flask import request
from invenio_rest.errors import FieldError, RESTValidationError


def search_factory(self, search, query_parser=None):
    """Parse query using elasticsearch DSL query.

    :param self: REST view.
    :param search: Elastic search DSL search instance.
    :returns: Tuple with search instance and URL arguments.
    """
    from invenio_records_rest.facets import default_facets_factory
    from invenio_records_rest.sorter import default_sorter_factory
    search_index = search._index[0]

    # TODO: make "scheme" optional?
    for field in ('id', 'scheme', 'relation'):
        if field not in request.values:
            raise RESTValidationError(
                errors=[FieldError(field, 'Required field.')])

    search, urlkwargs = default_facets_factory(search, search_index)
    search, sortkwargs = default_sorter_factory(search, search_index)
    for key, value in sortkwargs.items():
        urlkwargs.add(key, value)

    # Apply 'identity' grouping by default
    if 'groupBy' not in request.values:
        search = search.filter(Q('term', Grouping='identity'))
        urlkwargs['groupBy'] = 'identity'

    # Exclude the identifiers by which the search was made (large aggregate)
    search = search.source(exclude=['*.SearchIdentifier'])
    return search, urlkwargs


def enum_term_filter(label: str, field: str, choices: Dict[str, str]):
    """Term filter with controlled vocabulary."""
    def inner(values):
        if len(values) != 1:
            raise RESTValidationError(
                errors=[FieldError(label, 'Multiple values specified.')])
        term_value = choices.get(values[0])
        if not term_value:
            raise RESTValidationError(
                errors=[FieldError(
                    label, 'Allowed values: [{}]'.format(', '.join(choices)))])
        return Q('term', **{field: term_value})
    return inner


def nested_terms_filter(field: str, path: str = None):
    """Nested terms filter."""
    path = path or field.rsplit('.', 1)[0]

    def inner(values):
        return Q('nested', path=path, query=dict(terms={field: values}))
    return inner


def nested_range_filter(
        label: str, field: str, path: str = None, op: str = None):
    """Nested range filter."""
    path = path or field.rsplit('.', 1)[0]
    assert op in ('gte', 'gt', 'lte', 'lt')

    def inner(values):
        if len(values) != 1:
            raise RESTValidationError(
                errors=[FieldError(label, 'Multiple values specified.')])
        return Q('nested', path=path, query=Range(**{field: {op: values[0]}}))
    return inner
