from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .datastore import (Identifier, Base, Relationship, RelationshipType)
from .schema import from_scholix_relationship_type


def get_or_create(session, model, **kwargs):
    # https://stackoverflow.com/a/2587041/180783
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        instance2 = session.query(model).filter_by(**kwargs).first()
        if instance is not instance2:
            raise ValueError(f"Error creating instance: {instance}")
        return instance2


class SoftwareBroker(object):

    def __init__(self):
        self.engine = create_engine('sqlite:///:memory:', echo=False)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        Base.metadata.create_all(self.engine)

    def handle_event(self, event):
        handler = getattr(self, event['event_type'])
        handler(event)

    def relation_created(self, event):
        for payload in event['payload']:

            # TODO Do in one transaction
            rel_type  = payload['RelationshipType']
            relationship_type, inversed = from_scholix_relationship_type(rel_type)

            pljson = payload['Source']['Identifier']
            kwargs = {'scheme': pljson['IDScheme'], 'value': pljson['ID']}
            source = get_or_create(self.session, Identifier, **kwargs)

            pljson = payload['Target']['Identifier']
            kwargs = {'scheme': pljson['IDScheme'], 'value': pljson['ID']}
            target = get_or_create(self.session, Identifier, **kwargs)
            if inversed:
                source, target = target, source

            kwargs = {'source_id': source.id,
                      'target_id': target.id,
                      'relationship_type': relationship_type}
            relationship = get_or_create(self.session, Relationship, **kwargs)

            self.session.add(source)
            self.session.add(target)
            self.session.add(relationship)
            self.session.commit()

    def show_all(self):
        print('')
        for cls in [Identifier, Relationship]:
            name = cls.__name__.upper() + 'S'
            print(name)
            print('-' * len(name))
            for obj in self.session.query(cls):
                print(obj)
            print('')
        id_A = self.session.query(Identifier).filter_by(scheme='DOI', value='10.1234/A').one()
        #citations = self.get_citations(id_A)
        full_c = self.get_citations(id_A, with_parents=True, with_siblings=True)
        print(citations)


    def get_citations(self, identifier, with_parents=False, with_siblings=False):
        # At the beginning, frontier is just identities
        frontier = identifier.get_identities(self.session)
        # Expand with parents
        if with_parents:
            iden_parents = sum([[i.id for i in iden.get_parents(self.session,
                                                                RelationshipType.HasVersion)]
                                                                for iden in frontier], [])
            iden_parents = [self.session.query(Identifier).get(uuid) for uuid in set(iden_parents)]
            iden_parents = sum([par.get_identities(self.session) for par in iden_parents], [])
            frontier += iden_parents
        # Expand with siblings
        if with_parents and with_siblings: # TODO, in order to support only siblings, skip frontier addition before
            par_children = sum([[i.id for i in par.get_children(self.session,
                                                                RelationshipType.HasVersion)]
                                                                for par in iden_parents], [])
            par_children = [self.session.query(Identifier).get(uuid) for uuid in set(par_children)]

            par_children = sum([chil.get_identities(self.session) for chil in par_children], [])
            frontier += par_children
        frontier = [f.id for f in frontier]
        frontier = [self.session.query(Identifier).get(uuid) for uuid in set(frontier)]
        citations = sum([[i.id for i in iden.get_parents(self.session)] for iden in frontier], [])

        citations = [self.session.query(Identifier).get(uuid) for uuid in set(citations)]
        return citations
