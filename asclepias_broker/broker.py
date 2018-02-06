from itertools import groupby

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .datastore import (Base, Event, Identifier, ObjectEvent, PayloadType,
                        Relation, Relationship)
from .schemas.loaders import EventSchema, RelationshipSchema
from .tasks import update_groups


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
        Session = scoped_session(sessionmaker(bind=self.engine))
        self.session = Session()
        Base.metadata.create_all(self.engine)

    def handle_event(self, event):
        handler = getattr(self, event['event_type'])
        with self.session.begin_nested():
            handler(event)
        self.session.commit()

    def create_event(self, event):
        # TODO: Skip existing events?
        # TODO: Check `errors`
        event_obj, errors = EventSchema(
            session=self.session, check_existing=True).load(event)
        self.session.add(event_obj)
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

    def relationship_created(self, event):
        self._handle_relationship_event(event)

    def relationship_deleted(self, event):
        self._handle_relationship_event(event, delete=True)

    # TODO: Test if this generalization works as expected
    def _handle_relationship_event(self, event, delete=False):
        event_obj = self.create_event(event)
        for payload_idx, payload in enumerate(event['payload']):
            with self.session.begin_nested():
                relationship, errors = RelationshipSchema(
                    session=self.session, check_existing=True).load(payload)
                if relationship.id:
                    relationship.deleted = delete
                self.session.add(relationship)
                # We need ORM relationship with IDs, since Event has
                # 'weak' (non-FK) relations to the objects, hence we need
                # to know the ID upfront
                relationship = relationship.fetch_or_create_id(self.session)
                self.create_relation_object_events(event_obj, relationship, payload_idx)

                # TODO: This should be a task after the ingestion commit
                update_groups(self.session, relationship)

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
                                                    Relation.HasVersion, as_relation=True)
                                    for iden in frontier], []))
            iden_parents = [item.source for item in parents_rel]
            iden_parents = set(sum([p.get_identities(self.session) for p in iden_parents], []))
            if with_parents:
                frontier_rel |= parents_rel
                frontier += iden_parents
        # Expand with siblings
        if with_siblings:
            children_rel = set(sum([p.get_children(self.session,
                                                   Relation.HasVersion, as_relation=True)
                                    for p in iden_parents], []))
            frontier_rel |= children_rel
            par_children = [item.target for item in children_rel]
            par_children = set(sum([c.get_identities(self.session) for c in par_children], []))
            frontier += par_children
        frontier = set(frontier)
        # frontier contains all identifiers which directly cite the resource
        citations = set(sum([iden.get_parents(self.session, Relation.Cites, as_relation=True) for iden in frontier], []))
        # Expand it to identical identifiers and group them if they repeat
        expanded_sources = [c.source.get_identities(self.session) for c in citations]
        zipped = sorted(zip(expanded_sources, citations), key=lambda x: [xi.value for xi in x[0]])
        aggregated_citations = [(k, list(vi for _, vi in v)) for k, v in groupby(zipped, key=lambda x: x[0])]
        frontier_rel = list(frontier_rel) + list(set(sum([item._get_identities(self.session, as_relation=True) for item in frontier], [])))
        if expand_target:
            aggregated_citations = [(list(frontier), frontier_rel)] + aggregated_citations
        return aggregated_citations
