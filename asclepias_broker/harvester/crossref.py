# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Crossref client."""

from copy import deepcopy
from datetime import datetime
from typing import Iterator

import requests
from flask import current_app
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from ..events.api import EventAPI
from ..utils import chunks
from .proxies import current_harvester


class CrossrefAPIException(Exception):
    """Crossref REST API exception."""


class CrossrefAPIParametersException(Exception):
    """Crossref REST API parameters exception."""


class CrossrefHarvester:
    """."""

    DEFAULT_API_BASE_URL = 'https://api.eventdata.crossref.org/v1/events'

    VALID_API_PARAMS = {
        'from-occurred-date', 'until-occurred-date',
        'from-collected-date', 'until-collected-date',
        'from-updated-date', 'until-updated-date',
        'subj-id', 'obj-id',
        'subj-id.prefix', 'obj-id.prefix',
        'subj-id.domain', 'obj-id.domain',
        'subj.url', 'obj.url',
        'subj.url.domain', 'obj.url.domain',
        'subj.alternative-id', 'obj.alternative-id',
        'source', 'relation-type',
        'rows', 'cursor',
        'mailto',
    }

    def __init__(self, *, id: str = None, base_url: str = None,
                 params: dict = None):
        """."""
        self.id = id
        self.base_url = base_url or self.DEFAULT_API_BASE_URL
        self.params = params or {}
        self._session = None

    @property
    def session(self):
        """Create a session for making HTTP requests to the API."""
        if self._session is None:
            _session = requests.Session()
            retry = Retry(
                total=5, read=5, connect=5,
                backoff_factor=0.3,
                status_forcelist=(500, 502, 504),
            )
            adapter = HTTPAdapter(max_retries=retry)
            _session.mount('http://', adapter)
            _session.mount('https://', adapter)
            self._session = _session
        return self._session

    def _clean_scholix(self, data):
        data.pop('Url', None)
        for k in ('Source', 'Target'):
            t = data[k]['Type']
            if not t.get('Name'):
                t['Name'] = 'unknown'
            if not t.get('SubType'):
                t.pop('SubType', None)
            if not t.get('SubTypeSchema'):
                t.pop('SubTypeSchema', None)
            if t['Name'].lower() == 'other':
                if t.get('SubType') == 'software':
                    t['Name'] = 'software'
                else:
                    t['Name'] = 'unknown'
            # Rename IDUrl -> IDURL
            data[k]['Identifier']['IDURL'] = data[k]['Identifier'].pop('IDUrl')
        return data

    def search_events(self, *, scholix: bool = True) -> Iterator[dict]:
        """Search the Crossref events API."""
        url = f'{self.base_url}/scholix' if scholix else self.base_url
        params = deepcopy(self.params)

        # Add 'mailto' parameter from config if available
        email = params.get('mailto') or current_app.config.get(
            'ASCLEPIAS_HARVESTER_CROSSREF_API_EMAIL')
        if email:
            params['mailto'] = email

        if set(params.keys()) > self.VALID_API_PARAMS:
            raise CrossrefAPIParametersException()

        while True:
            resp = self.session.get(url, params=params)
            if not resp.ok or resp.json().get('status') != 'ok':
                raise CrossrefAPIException()
            payload = resp.json()
            items = payload.get('message', {}).get(
                'link-packages' if scholix else 'events', [])
            for item in items:
                yield self._clean_scholix(item) if scholix else item

            cursor_id = payload.get('message', {}).get('next-cursor')
            if cursor_id:
                params['cursor'] = cursor_id
            else:
                break

    def harvest(self, eager: bool = False, no_index: bool = True):
        """."""
        last_run = current_harvester.history.get(self.id)
        current_datetime = datetime.now()
        if last_run:
            self.params.setdefault(
                'from-occurred-date', last_run.date().isoformat())

        results = self.search_events()
        for events in chunks(results, 100):
            EventAPI.handle_event(list(events), no_index=no_index, eager=eager)

        current_harvester.history.set(self.id, value=current_datetime)
