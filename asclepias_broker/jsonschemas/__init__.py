import json
from pathlib import Path


_CUR_DIR = Path(__file__).parent

with open(_CUR_DIR / 'definitions.json', 'r') as fp:
    DEFINITIONS_SCHEMA = json.load(fp)

with open(_CUR_DIR / 'scholix-v3.json', 'r') as fp:
    SCHOLIX_SCHEMA = json.load(fp)

with open(_CUR_DIR / 'event.json', 'r') as fp:
    EVENT_SCHEMA = json.load(fp)
