# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Versioning metadata harvester."""

from copy import deepcopy
from datetime import datetime
from typing import List

from ..events.api import EventAPI

import re
import requests
from flask import current_app
from sqlalchemy.orm import relationship

from asclepias_broker.core.models import Identifier

from ..utils import chunks
from .base import MetadataHarvester


class GitHubAPIException(Exception):
    """Github REST API exception."""


class GitHubClient:
    """GitHub client."""

    base_url = 'https://api.github.com/'
    
    # For some reason a different repo name when using id vs name in the Github API 

    def get_repo_metadata_from_id(self, id) -> dict:
        url = self.base_url + "/repositories/" + id
        return self.query_api(url)
    
    def get_repo_metadata_from_name(self, user, repo) -> dict:
        url = self.base_url + "/repos/" + user + "/" + repo
        return self.query_api(url)

    def get_repo_release_from_name(self, user, repo, tag) -> dict:
        repo_meta = self.get_repo_metadata_from_name(user, repo)
        releases_url = repo_meta['releases_url'].replace('{/id}','')
        return self.get_repo_release(releases_url, repo_meta, tag)

    def get_repo_release_from_id(self, id, tag) -> dict:
        repo_meta = self.get_repo_metadata_from_id(id)
        releases_url = repo_meta['releases_url'].replace('{/id}','')
        return self.get_repo_release(releases_url, repo_meta, tag)

    def get_repo_release(self, url, repo_meta, tag) -> dict:
        releases = self.query_api(url)
        for release in releases:
            if release['tag_name'] == tag:
                release['repo_id'] = repo_meta['ID']
                release['repo_name'] = repo_meta['full_name']
                return release

    def query_api(self,url):
        try:
            headers = {'X-GitHub-Media-Type':'application/vnd.github.v3.raw+json'}
            res = requests.get(url, headers=headers)
            if res.ok:
                return res.json()
            else:
                res.raise_for_status()
        except Exception as exc:
            raise GitHubAPIException(exc)

class GitHubHarvester(MetadataHarvester):
    """Metadata harvester for Zenodo records' versioning."""

    def __init__(self, *, provider_name: str = None):
        """."""
        self.provider_name = provider_name or "Github versioning harvester"

    def can_harvest(self, identifier: str, scheme: str,
                    providers: List[str] = None) -> bool:
        """."""
        is_provider = False
        if providers:
            is_provider = self.provider_name in providers

        return (self._is_github_url(scheme, identifier) or\
            self._is_github_repo_id(scheme, identifier) or\
            self._is_github_release_id(scheme, identifier) )\
            and not is_provider

    def harvest(self, identifier: str, scheme: str,
                providers: List[str] = None):
        """."""
        try:
            providers = set(providers) if providers else set()
            providers.add(self.provider_name)
            payloads = []
            if self._is_github_url(scheme, identifier):
                parsed_info = self.parse_url_info(identifier)
            elif self._is_github_repo_id(scheme,identifier):
                parsed_info = dict(id=identifier, identifier=identifier, scheme='github')
            elif self._is_github_repo_release_id(scheme,identifier):
                id, release_id = identifier.split('/')
                parsed_info = dict(id=id, sub_type='release_id', release_id=release_id, identifier=identifier, scheme='github')
           
            child = None
            if 'sub_type' in parsed_info.keys():
                for payload in add_version_identifiers(parsed_info, providers):
                    payloads.append(payload)
                child = {
                    "ID": parsed_info['identifier'],
                    "IDScheme": parsed_info['scheme']
                }
            
            for payload in add_parent_identifiers(parsed_info, providers, child):
                payloads.append(payload)

            for event_chunk in chunks(payloads, 100):
                try:
                    EventAPI.handle_event(list(event_chunk), no_index=True, eager=True)
                except ValueError:
                    current_app.logger.exception(
                        'Error while processing versioning event.')
        except Exception as exc:
            raise GitHubAPIException(exc)

    def _is_github_repo_id(self,  scheme: str, identifier: str) -> bool:
        if scheme.lower() == 'github' and re.match('^\d+$',identifier):
            return True
        return False

    def _is_github_release_id(self,  scheme: str, identifier: str) -> bool:
        if scheme.lower() == 'github' and re.match('^\d+/releases/\d+$',identifier):
            return True
        return False
        
    def _is_github_url(self,  scheme: str, identifier: str) -> bool:
        if scheme.lower() == 'url' and 'github.com' in identifier.lower():
            return True
        else:
            return False
    
    def parse_url_info(self, url):
        parts = url.split('/')
        github_index = next(i for i,p in enumerate(parts) if 'github.com' in p)
        
        if len(parts) - github_index < 2:
                raise GitHubAPIException('Not a valid github url: ', )

        resp = dict()
        resp['identifier'] = url
        resp['scheme'] = 'url'
        resp['user'] = parts[github_index + 1]
        resp['repo'] = parts[github_index + 2]

        # Specific version urls shoudl be either on the form
        # github.com/user/repo/tree/tag_we_want
        # or 
        # github.com/user/repo/releases/tag/tag_we_want
        if len(parts) - github_index > 2:
            resp['sub_type'] = parts[github_index + 3]
            if resp['sub_type'] == 'tree': 
                resp['tag'] = parts[github_index + 4]
            elif resp['sub_type'] == 'releases':
                resp['tag'] = parts[github_index + 5]
        return resp

def add_parent_identifiers(parsed_info, providers, child = None) -> List[dict]:
    client = GitHubClient()
    add_old_name = False
    if 'user' in parsed_info.keys():
        parent_meta = client.get_repo_metadata_from_name(user=parsed_info['user'], repo=parsed_info['repo'])
        if parent_meta['full_name'] != parsed_info['user'] + '/' + parsed_info['repo']:
            add_old_name = True
    else:
        parent_meta = client.get_repo_metadata_from_id(id=parsed_info['id'])
    id = parent_meta['id']
    full_name = parent_meta['full_name']

    id_identifier = {
            "ID": str(id),
            "IDScheme": 'github'
    }
    name_identifier = {
            "ID": 'https://github.com/' + full_name,
            "IDScheme": 'url'
    }
    payloads = []
    payloads.append(create_relationship_event(src=id_identifier, target=name_identifier, relationship='IsIdenticalTo', providers=providers))
    if child != None:
        payloads.append(create_relationship_event(src=id_identifier, target=child, relationship='HasVersion', providers=providers))
    if add_old_name:
        old_name_identifier = {
            "ID": 'github.com/' + parsed_info['user'] + '/' + parsed_info['repo'],
            "IDScheme": 'url'
        }
        payloads.append(create_relationship_event(src=name_identifier, target=old_name_identifier, relationship='IsIdenticalTo', providers=providers))

    return payloads

def add_version_identifiers(parsed_info, providers)  -> List[dict]:
    client = GitHubClient()
    add_old_name = False
    if 'user' in parsed_info.keys():
        version_meta = client.get_repo_release_from_name(user=parsed_info['user'], repo=parsed_info['repo'], tag=parsed_info['tag'])
        if version_meta['html_url'] != parsed_info['identifier']:
            add_old_name = True
    else:
        version_meta = client.get_repo_release_from_id(user=parsed_info['id'])

    payloads = []

    if version_meta is not None:
        id_identifier = {
                "ID": str(version_meta['repo_id']) + '/releases/' + str(version_meta['id']),
                "IDScheme": 'github'
        }
        name_identifier = {
                "ID": version_meta['html_url'],
                "IDScheme": 'url'
        }
    
        payloads.append(create_relationship_event(src=id_identifier, target=name_identifier, relationship='IsIdenticalTo', providers=providers))
        if add_old_name:
            old_name_identifier = {
                "ID": parsed_info['identifier'],
                "IDScheme": 'url'
            }
            payloads.append(create_relationship_event(src=name_identifier, target=old_name_identifier, relationship='IsIdenticalTo', providers=providers))

    return payloads

def create_relationship_event(src, target, relationship, providers) -> dict:
    link_publication_date = datetime.now().isoformat()
    payload = {
        'RelationshipType': {
            'Name': 'IsRelatedTo',
            'SubTypeSchema': 'DataCite',
            'SubType': relationship
        },
        'Target': {
            'Identifier': src,
            'Type': {'Name': 'unknown'}
        },
        'LinkProvider': providers,
        'Source': {
            'Identifier': target,
            'Type': {'Name': 'unknown'}
        },
        'LinkPublicationDate': link_publication_date,
    }

    return payload