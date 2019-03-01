# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Europe PMC harvester."""

from datetime import date

import requests

from ..events.api import EventAPI
from ..metadata.api import update_metadata
from ..utils import chunks


def raise_on_error(res):
    """Helper to check response for errors."""
    if res.status_code != 200:
        data = res.json()
        raise Exception('[{status}] {message}'.format(**data))


class ResultWrapper(object):
    """Helper to work with search results."""

    def __init__(self, session, reqfactory):
        """."""
        self._session = session
        self._reqfactory = reqfactory
        self._response = None

    @property
    def total(self):
        """Get total number of hits."""
        if self._response:
            return self._response.json()['hitCount']

    def prepare_request(self, cursor_mark):
        """Prepare a request to the API."""
        return self._session.prepare_request(self._reqfactory(cursor_mark))

    @property
    def pages(self):
        """Helper to fetch all result pages."""
        cursor = '*'
        page_length = 1
        while cursor and page_length > 0:
            req = self.prepare_request(cursor)
            self._response = self._session.send(req)
            raise_on_error(self._response)
            yield self._response
            payload = self._response.json()
            cursor = payload.get('nextCursorMark')
            page_length = len(payload.get('resultList', {}).get('result', []))

    @property
    def hits(self):
        """Helper to iterate over each hit."""
        for res in self.pages:
            for h in res.json()['resultList']['result']:
                yield h


class PMCClient(object):
    """Europe PMC API client."""

    def __init__(self, email: str = None):
        """Initialize client."""
        self._email = email or current_app.config.get(
            'ASCLEPIAS_HARVESTER_EUROPE_PMC_API_EMAIL')
        self._session = None
        self._endpoint_search = (
            'https://www.ebi.ac.uk'
            '/europepmc/webservices/rest/search'
        )
        self._endpoint_datalinks = (
            'https://www.ebi.ac.uk'
            '/europepmc/webservices/rest/MED/{pmid}/datalinks'
        )

    @property
    def session(self):
        """Create a session for making HTTP requests to the API."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({'Accept': 'application/json'})
        return self._session

    def datalinks(self, id: str, filter_=None):
        """."""
        res = self.session.get(
            self._endpoint_datalinks.format(pmid=id),
            params={
                'format': 'json',
                'category': 'Data Citations',
                'email': self._email,
            }
        )
        return filter_(res) if filter_ else res

    def search(self, query: str = None, restype: str = 'core',
               size: int = 100):
        """Search Europe PMC."""
        params = {
            'query': query or '',
            'resultType': restype,
            'format': 'json',
            'pageSize': size,
        }
        if self._email:
            params['email'] = self._email

        def reqfactory(cursor):
            params['cursorMark'] = cursor
            return requests.Request(
                'GET', self._endpoint_search, params=params)

        return ResultWrapper(self.session, reqfactory)


class EuropePMCHarvester:
    """Europe PMC citation harvester."""

    def __init__(self, *, id: str = None, email: str = None,
                 query: str = None, doi_prefix: str = None):
        """Initialize harvester."""
        self.id = id
        self.client = PMCClient(email=email)
        self.query = query
        self.doi_prefix = doi_prefix

    @classmethod
    def _clean_scholix(cls, link):
        # remove non-standard fields
        for f in ('ObtainedBy', 'Frequency'):
            link.pop(f, None)

        # fix publication date (14-01-2019 -> 2019-01-14)
        link_pub_date = link.pop('PublicationDate', None)
        try:
            day, month, year = link_pub_date.split('-')
            link_pub_date = '-'.join((year, month, day))
        except Exception:
            pass
        link['LinkPublicationDate'] = link_pub_date or date.today().isoformat()

        # fix link provider envelope
        link['LinkProvider'] = [link['LinkProvider']]

        # remove target Publisher if "Europe PMC"
        target_publisher = link['Target'].get('Publisher')
        if isinstance(target_publisher, dict):
            if link['Target']['Publisher'].get('Name') == 'Europe PMC':
                link['Target'].pop('Publisher', None)

        # fix publisher envelope
        for obj_key in ('Target', 'Source'):
            if isinstance(link[obj_key].get('Publisher'), dict):
                link[obj_key]['Publisher'] = [link[obj_key]['Publisher']]
        return link

    @classmethod
    def _metadata_from_hit(cls, hit):
        """Build Scholix metadata from a Europe PMC API search result hit."""
        source_ids = []
        for field in ('doi', 'pmid', 'pmcid'):
            if hit.get(field):
                source_ids.append({'ID': hit[field], 'IDScheme': field})
        source_creators = []
        for author in hit.get('authorList', {}).get('author', []):
            if author.get('firstName') and author.get('lastName'):
                source_creators.append(
                    {'Name': '{firstName}, {lastName}'.format(**author)})
            elif author.get('fullName'):
                source_creators.append({'Name': author.get('fullName')})
        source_pub_date = None
        if hit.get('firstPublicationDate'):
            source_pub_date = hit.get('firstPublicationDate')
        elif hit.get('pubYear'):
            source_pub_date = '{}-01-01'.format(hit.get('pubYear'))
        source_metadata = {
            'Title': hit.get('title'),
            'Identifier': source_ids,
            'Creator': source_creators,
            'Type': {'Name': 'literature'},
        }
        if source_pub_date:
            source_metadata['PublicationDate'] = source_pub_date
        return source_metadata

    @classmethod
    def _doi_prefix_filter(cls, doi_prefix: str = None):
        """Extract links from a datalinks response."""
        def _filter(res):
            data = res.json()
            try:
                links = (
                    data['dataLinkList']['Category'][0]
                    ['Section'][0]
                    ['Linklist']['Link']
                )
                for l in links:
                    target_id = l['Target']['Identifier']['ID']
                    if not doi_prefix or target_id.startswith(doi_prefix):
                        yield l
            except (KeyError, IndexError, TypeError):  # skip missing data
                return
        return _filter

    def harvest(self):
        """Harvest links."""
        events = []
        for hit in self.client.search(query=self.query).hits:
            target_ids = set()
            _filter_func = self._doi_prefix_filter(doi_prefix=self.doi_prefix)
            links = list(self.client.datalinks(hit['id'], _filter_func))
            for link in links:
                target_id = link['Target']['Identifier']['ID']
                target_scheme = link['Target']['Identifier']['IDScheme']
                target_ids.add((target_id, target_scheme))
            if target_ids:
                source_metadata = self._metadata_from_hit(hit)
                for scheme in ('pmid', 'pmcid', 'doi'):
                    source_id, source_scheme = hit.get(scheme), scheme
                    if source_id:
                        break
                update_metadata(
                    source_id, source_scheme, source_metadata,
                    providers=['Europe PMC'])
                events.append([self._clean_scholix(l) for l in links])
        for chunk in chunks(events, 100):
            EventAPI.handle_event(list(chunk), no_index=True)
