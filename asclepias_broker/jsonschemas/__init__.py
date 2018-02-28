import json
import os


_CUR_DIR = os.path.dirname(__file__)

with open(os.path.join(_CUR_DIR, 'definitions.json'), 'r') as fp:
    DEFINITIONS_SCHEMA = json.load(fp)

with open(os.path.join(_CUR_DIR, 'scholix-v3.json'), 'r') as fp:
    SCHOLIX_SCHEMA = json.load(fp)

with open(os.path.join(_CUR_DIR, 'event.json'), 'r') as fp:
    EVENT_SCHEMA = json.load(fp)
