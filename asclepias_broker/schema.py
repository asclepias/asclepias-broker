# For now this is a toy datastore that is completely unoptimized

import enum

from .datastore import RelationshipType, Identifier


DATACITE_RELATION_MAP = {
    'Cites': [
        ('Cites', False),
        ('IsCitedBy', True),
        ('References', False),
        ('IsReferencedBy', True),
    ],
    'IsSupplementTo': [
        ('IsSupplementTo', False),
        ('IsSupplementedBy', True),
    ],
    'HasVersion': [
        ('HasVersion', False),
        ('IsVersionOf', True),
        ('HasPart', False),
        ('IsPartOf', True),
    ],
    'IsIdenticalTo': [
        ('IsIdenticalTo', False),
    ]
}
INV_DATACITE_RELATION_MAP = dict(sum([[(vv, (k, inv)) for vv, inv in v] for k, v in DATACITE_RELATION_MAP.items()], []))


def from_scholix_relationship_type(rel_type):
    datacite_subtype = rel_type.get('SubType')
    if datacite_subtype and rel_type.get('SubTypeSchema') == 'DataCite':
        type_name = datacite_subtype
    else:
        type_name = rel_type['Name']
    rel_name, inversed = INV_DATACITE_RELATION_MAP.get(type_name, ('IsRelatedTo', False))
    return getattr(RelationshipType, rel_name), inversed
