from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .datastore import (Organization, Identifier, Type, Object, Base,
                        Relationship, RelationshipType)


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

    def object_created(self, event):

        for payload in event['payload']:

            obj_payload = payload['object']

            publisher = get_or_create(self.session, Organization, **obj_payload['publisher'])
            identifier = get_or_create(self.session, Identifier, **obj_payload['identifier'])
            object_type = get_or_create(self.session, Type, **obj_payload['type'])
            publication_date = obj_payload['publication_date']

            obj = Object(publisher_id=publisher.id, identifier_id=identifier.id,
                         type_id=object_type.id, publication_date=publication_date)

            self.session.add(publisher)
            self.session.add(identifier)
            self.session.add(object_type)
            self.session.add(obj)
            self.session.commit()

    def relation_created(self, event):

        for payload in event['payload']:

            relationship_type = get_or_create(self.session, RelationshipType, **payload['relationship_type'])
            source = get_or_create(self.session, Identifier, **payload['source']['identifier'])
            target = get_or_create(self.session, Identifier, **payload['target']['identifier'])

            obj = Relationship(source_id=source.id,
                               target_id=target.id,
                               relationship_type=relationship_type.id)

            self.session.add(relationship_type)
            self.session.add(source)
            self.session.add(target)
            self.session.add(obj)
            self.session.commit()

    def show_all(self):
        print('')
        for cls in [Organization, Identifier, Type, Object, RelationshipType, Relationship]:
            name = cls.__name__.upper() + 'S'
            print(name)
            print('-' * len(name))
            for obj in self.session.query(cls):
                print(obj)
            print('')
