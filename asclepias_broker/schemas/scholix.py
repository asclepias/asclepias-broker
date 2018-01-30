from marshmallow import Schema, fields, validate, pre_dump

# TODO: Use context to provide missing metadata. Example
# schema = RelationshipSchema()
# schema.context['source_object'] = {'title': 'Whatever'}
# schema.context['relation_type'] = {'type': 'literature', 'subtype': 'foo'}
# ...

SCHOLIX_RELATIONS = {'References', 'IsReferencedBy', 'IsSupplementTo',
                     'IsSupplementedBy'}


class IdentifierSchema(Schema):

    ID = fields.String(required=True, attribute='value')
    IDScheme = fields.String(required=True, attribute='scheme')
    IDURL = fields.String()  # TODO: attribute=???


class PersonOrOrgSchema(Schema):

    Name = fields.String()
    Identifier = fields.Nested(IdentifierSchema, many=True)


class ObjectSchema(Schema):

    @pre_dump
    def identifier_envelope(self, obj):
        # wtf..
        obj.Identifier = obj
        return obj

    Identifier = fields.Nested(IdentifierSchema)
    Type = fields.String()  # TODO: required=True
    Title = fields.String()  # TODO: required=True
    Creator = fields.Nested(PersonOrOrgSchema, many=True)
    PublicationDate = fields.Date()
    Publisher = fields.Nested(PersonOrOrgSchema, many=True)


class RelationshipTypeSchema(Schema):

    Name = fields.String(
        required=True, validate=validate.OneOf(SCHOLIX_RELATIONS))
    SubType = fields.String()
    SubTypeSchema = fields.String()

    @pre_dump
    def dump_rel_type(self, obj):
        if obj.name not in SCHOLIX_RELATIONS:
            obj.Name = 'IsRelatedTo'
            obj.SubType = obj.name
            obj.SubTypeSchema = 'DataCite'
        else:
            obj.Name = obj.name
        return obj


class RelationshipSchema(Schema):

    LinkPublicationDate = fields.Date()  # TODO: required=True
    LinkProvider = fields.Nested(PersonOrOrgSchema, many=True)
    RelationshipType = fields.Nested(
        RelationshipTypeSchema, required=True, attribute='relation')
    Source = fields.Nested(ObjectSchema, required=True, attribute='source')
    Target = fields.Nested(ObjectSchema, required=True, attribute='target')
