import sys
import json

from asclepias_broker.broker import SoftwareBroker

if len(sys.argv) == 2:
    event_file = sys.argv[1]
else:
    print("Usage: python run_example.py <event_file>")
    sys.exit(1)

broker = SoftwareBroker()

with open(event_file) as f:
    for event in json.load(f):
        broker.handle_event(event)

broker.show_all()
