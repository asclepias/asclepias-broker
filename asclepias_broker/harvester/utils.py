# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Harvester is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Harvester utilities."""

from datetime import datetime

from invenio_cache import current_cache


class HarvesterHistory:
    """."""

    def __init__(self, prefix: str):
        """."""
        self.prefix = prefix

    def get(self, key: str) -> datetime:
        """."""
        return current_cache.get(f'{self.prefix}:{key}')

    def set(self, key: str, value: datetime = None):
        """."""
        return current_cache.set(
            f'{self.prefix}:{key}', value or datetime.now(), timeout=-1)

class GitHubAPIException(Exception):
    """Github exception."""

class GithubUtility:
    @classmethod
    def parse_url_info(cls, url):
            parts = url.split('/')
            github_index = next(i for i,p in enumerate(parts) if 'github.com' in p)
            
            if len(parts) - github_index < 3:
                    raise GitHubAPIException('Not a valid github repo url: ' + url, )

            resp = dict()
            resp['identifier'] = url
            resp['scheme'] = 'url'
            resp['user'] = parts[github_index + 1]
            resp['repo'] = parts[github_index + 2]

            # Specific version urls shoudl be either on the form
            # github.com/user/repo/tree/tag_we_want
            # or 
            # github.com/user/repo/releases/tag/tag_we_want
            # or 
            # github.com/user/repo/commit/tag_we_want
            if len(parts) - github_index > 4:
                resp['sub_type'] = parts[github_index + 3]
                if resp['sub_type'] == 'tree' or resp['sub_type'] == 'commit':  
                    resp['tag'] = parts[github_index + 4]
                elif resp['sub_type'] == 'releases':
                    resp['tag'] = parts[github_index + 5]
                else:
                    raise GitHubAPIException('Not a valid github repo url: ' + url, )
            return resp