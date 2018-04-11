from marshmallow import Schema, fields, pre_dump, validate

SCHOLIX_RELATIONS = {'References', 'IsReferencedBy', 'IsSupplementTo',
                     'IsSupplementedBy'}


class IdentifierSchema(Schema):

    ID = fields.String(required=True, attribute='value')
    IDScheme = fields.String(required=True, attribute='scheme')
    IDURL = fields.String()


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
