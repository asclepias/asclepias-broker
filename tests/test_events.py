"""Test relation events against the JSONSchema."""
from jsonschema import validate


def test_ads_relation_events(ads_relation_events, event_schema):
    """Test simple relation event JSONSchema validation."""
    # Will rase in case of schema validation errors
    for data in ads_relation_events:
        validate(data, event_schema)


def test_ads_relation_payloads(ads_relation_payloads, relation_schema):
    """Test simple relation payload JSONSchema validation."""
    # Will rase in case of schema validation errors
    for data in ads_relation_payloads:
        validate(data, relation_schema)


def test_zenodo_object_events(zenodo_object_events, event_schema):
    """Test Zenodo object event JSONSchema validation."""
    # Will rase in case of schema validation errors
    for data in zenodo_object_events:
        validate(data, event_schema)


def test_zenodo_object_payloads(zenodo_object_events, object_schema):
    """Test Zenodo object payload with object JSONSchema validation."""
    # Will rase in case of schema validation errors
    for data in zenodo_object_events:
        payload_items = data['payload']
        for payload in payload_items:
            validate(payload, object_schema)
