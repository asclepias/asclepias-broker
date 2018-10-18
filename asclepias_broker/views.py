# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
"""Views for receiving and querying events and relationships."""
from flask import Blueprint

blueprint = Blueprint('asclepias_root', __name__, template_folder='templates')


@blueprint.route('/ping')
def ping():
    """Load balancer ping view."""
    return 'OK'


ping.talisman_view_options = {'force_https': False}
