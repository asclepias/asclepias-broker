from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils.functions import create_database, database_exists
from itertools import groupby
from copy import deepcopy
import arrow
import json
import uuid

from .datastore import Identifier, Base, Relationship, RelationshipType, \
    Event, ObjectEvent, EventType, PayloadType
from .schema import from_scholix_relationship_type


def get(session, model, **kwargs):
    return session.query(model).filter_by(**kwargs).first()


def create(session, model, **kwargs):
    instance = model(**kwargs)
    session.add(instance)
    return instance


def get_or_create(session, model, **kwargs):
    instance = get(session, model, **kwargs)
    if instance:
        return instance
    else:
        return create(session, model, **kwargs)


class SoftwareBroker(object):

    def __init__(self, db_uri=None):
        db_uri = db_uri or 'sqlite:///:memory:'
        self.engine = create_engine(db_uri, echo=False)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        Base.metadata.create_all(self.engine)

    def handle_event(self, event):
        handler = getattr(self, event['event_type'])
        handler(event)

    def create_event(self, event):
        event_kwargs = deepcopy(event)
        ev_type_map = {
            'relation_created': EventType.RelationCreated,
            'relation_deleted': EventType.RelationDeleted,
        }
        event_kwargs['event_type'] = ev_type_map[event['event_type']]
        event_kwargs['payload'] = event
        event_kwargs['time'] = arrow.get(event_kwargs['time']).datetime
        event_obj = get(self.session, Event, id=event['id'])
        if not event_obj:
            event_obj = create(self.session, Event, **event_kwargs)
        return event_obj

    def create_relation_object_events(self, event, relationship, payload_idx):
        # Create the Relation entry
        rel_obj = get_or_create(self.session, ObjectEvent, event_id=event.id,
            object_uuid=relationship.id,
            payload_type=PayloadType.Relationship,
            payload_index=payload_idx)

        # Create entries for source and target
        src_obj = get_or_create(self.session, ObjectEvent, event_id=event.id,
            object_uuid=relationship.source.id,
            payload_type=PayloadType.Identifier, payload_index=payload_idx)
        tar_obj = get_or_create(self.session, ObjectEvent, event_id=event.id,
            object_uuid=relationship.target.id,
            payload_type=PayloadType.Identifier, payload_index=payload_idx)
        return rel_obj, src_obj, tar_obj


    def relation_created(self, event):
        event_obj = self.create_event(event)
        for payload_idx, payload in enumerate(event['payload']):

            # TODO Do in one transaction
            rel_type  = payload['RelationshipType']
            relationship_type, inversed = from_scholix_relationship_type(rel_type)

            pljson = payload['Source']['Identifier']
            kwargs = {
                'scheme': pljson['IDScheme'],
                'value': pljson['ID'],
            }
            source = get(self.session, Identifier, **kwargs)
            if not source:
                kwargs['id'] = uuid.uuid4()
                source = create(self.session, Identifier, **kwargs)

            pljson = payload['Target']['Identifier']
            kwargs = {
                'scheme': pljson['IDScheme'],
                'value': pljson['ID'],
            }
            target = get(self.session, Identifier, **kwargs)
            if not target:
                kwargs['id'] = uuid.uuid4()
                target = create(self.session, Identifier, **kwargs)

            if inversed:
                source, target = target, source

            kwargs = {
                'source_id': source.id,
                'target_id': target.id,
                'relationship_type': relationship_type,
            }
            relationship = get(self.session, Relationship, **kwargs)
            if not relationship:
                kwargs['id'] = uuid.uuid4()
                relationship = create(self.session, Relationship, **kwargs)
            else:
                # If it existed, unmark the deletion
                relationship.deleted = False

            self.create_relation_object_events(event_obj, relationship, payload_idx)
            self.session.commit()

    def relation_deleted(self, event):
        for payload in event['payload']:

            rel_type  = payload['RelationshipType']
            relationship_type, inversed = from_scholix_relationship_type(rel_type)

            pljson = payload['Source']['Identifier']
            kwargs = {'scheme': pljson['IDScheme'], 'value': pljson['ID']}
            source = get(self.session, Identifier, **kwargs)

            pljson = payload['Target']['Identifier']
            kwargs = {'scheme': pljson['IDScheme'], 'value': pljson['ID']}
            target = get(self.session, Identifier, **kwargs)
            if inversed:
                source, target = target, source

            kwargs = {'source_id': source.id,
                      'target_id': target.id,
                      'relationship_type': relationship_type}
            if source and target:
                relationship = get(self.session, Relationship, **kwargs)
            if relationship:
                relationship.deleted = True
                self.session.add(relationship)
                self.session.commit()

    def show_all(self):
        lines = []
        for cls in [Identifier, Relationship, Event, ObjectEvent]:
            name = cls.__name__.upper()
            lines.append(name)
            lines.append('-' * len(name))
            for obj in self.session.query(cls):
                lines.append(str(obj))
            lines.append("")
        return "\n".join(lines)

    def print_citations(self, pid_value):
        id_A = self.session.query(Identifier).filter_by(scheme='DOI', value=pid_value).one()
        ids = id_A.get_identities(self.session)
        full_c = self.get_citations(id_A, with_parents=True, with_siblings=True, expand_target=True)
        from pprint import pprint
        pprint(full_c)


    def get_citations(self, identifier, with_parents=False, with_siblings=False, expand_target=False):
        # At the beginning, frontier is just identities
        frontier = identifier.get_identities(self.session)
        frontier_rel = set()
        # Expand with parents
        if with_parents or with_siblings:
            parents_rel = set(sum([iden.get_parents(self.session,
                                                    RelationshipType.HasVersion, as_relation=True)
                                    for iden in frontier], []))
            iden_parents = [item.source for item in parents_rel]
            iden_parents = set(sum([p.get_identities(self.session) for p in iden_parents], []))
            if with_parents:
                frontier_rel |= parents_rel
                frontier += iden_parents
        # Expand with siblings
        if with_siblings:
            children_rel = set(sum([p.get_children(self.session,
                                                   RelationshipType.HasVersion, as_relation=True)
                                    for p in iden_parents], []))
            frontier_rel |= children_rel
            par_children = [item.target for item in children_rel]
            par_children = set(sum([c.get_identities(self.session) for c in par_children], []))
            frontier += par_children
        frontier = set(frontier)
        # frontier contains all identifiers which directly cite the resource
        citations = set(sum([iden.get_parents(self.session, RelationshipType.Cites, as_relation=True) for iden in frontier], []))
        # Expand it to identical identifiers and group them if they repeat
        expanded_sources = [c.source.get_identities(self.session) for c in citations]
        zipped = sorted(zip(expanded_sources, citations), key=lambda x: [xi.value for xi in x[0]])
        aggregated_citations = [(k, list(vi for _, vi in v)) for k, v in groupby(zipped, key=lambda x: x[0])]
        frontier_rel = list(frontier_rel) + list(set(sum([item._get_identities(self.session, as_relation=True) for item in frontier], [])))
        if expand_target:
            aggregated_citations = [(list(frontier), frontier_rel)] + aggregated_citations
        return aggregated_citations
