# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Scholix marshmallow serializer."""

from marshmallow import Schema, fields, pre_dump, validate

from ..jsonschemas import SCHOLIX_RELATIONS


class IdentifierSchema(Schema):
    """Scholix identifier schema."""

    ID = fields.String(required=True, attribute='value')
    IDScheme = fields.String(required=True, attribute='scheme')
    IDURL = fields.String()


class PersonOrOrgSchema(Schema):
    """Scholix person or organization schema."""

    Name = fields.String()
    Identifier = fields.Nested(IdentifierSchema, many=True)


class ObjectSchema(Schema):
    """Scholix object schema."""

    @pre_dump
    def identifier_envelope(self, obj):
        """Put identifier in an envelope."""
        obj.Identifier = obj
        return obj

    Identifier = fields.Nested(IdentifierSchema)
    Type = fields.String()  # TODO: required=True
    Title = fields.String()  # TODO: required=True
    Creator = fields.Nested(PersonOrOrgSchema, many=True)
    PublicationDate = fields.Date()
    Publisher = fields.Nested(PersonOrOrgSchema, many=True)


class RelationshipTypeSchema(Schema):
    """Scholix relationship type schema."""

    Name = fields.String(
        required=True, validate=validate.OneOf(SCHOLIX_RELATIONS))
    SubType = fields.String()
    SubTypeSchema = fields.String()

    @pre_dump
    def dump_rel_type(self, obj):
        """Dump the relationship type in its fields."""
        if obj.name not in SCHOLIX_RELATIONS:
            obj.Name = 'IsRelatedTo'
            obj.SubType = obj.name
            obj.SubTypeSchema = 'DataCite'
        else:
            obj.Name = obj.name
        return obj


class RelationshipSchema(Schema):
    """Scholix relationship schema."""

    LinkPublicationDate = fields.Date(
        required=True, attribute='data.LinkPublicationDate')
    LinkProvider = fields.Nested(
        PersonOrOrgSchema, many=True, required=True,
        attribute='data.LinkProvider')
    RelationshipType = fields.Nested(
        RelationshipTypeSchema, required=True, attribute='relation')
    Source = fields.Nested(
        ObjectSchema, required=True, attribute='source.data')
    Target = fields.Nested(
        ObjectSchema, required=True, attribute='target.data')
