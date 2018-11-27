# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Event signals."""

from blinker import Namespace

_signals = Namespace()


event_processed = _signals.signal('event-processed')
"""Signal sent when an Event is processed.

Parameters:
- ``sender`` - the current application.
- ``event`` - the processed Event.

Example receiver:

.. code-block:: python

   def receiver(sender, event=None, **kwargs):
       # ...
"""
