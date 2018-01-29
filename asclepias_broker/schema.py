# For now this is a toy datastore that is completely unoptimized

import enum

from .datastore import Relation, Identifier


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


def from_scholix_relation(scholix_relation):
    datacite_subtype = scholix_relation.get('SubType')
    if datacite_subtype and scholix_relation.get('SubTypeSchema') == 'DataCite':
        type_name = datacite_subtype
    else:
        type_name = scholix_relation['Name']
    rel_name, inversed = INV_DATACITE_RELATION_MAP.get(type_name, ('IsRelatedTo', False))
    return getattr(Relation, rel_name), inversed
