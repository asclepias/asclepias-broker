# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for Asclepias broker."""

from __future__ import absolute_import, print_function

import glob
from functools import wraps
from itertools import islice
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

from flask import current_app
from invenio_cache import current_cache
from werkzeug.utils import import_string


def find_ext(file_or_dir: str, ext: str = None) -> List[str]:
    """Finds all files of a given extension in given subdirectory.

    :param file_or_dir: Path to search (e.g. ``/some/foo/bar/dir``) or file.
    :param ext: The extension of the files to search for (e.g. ``.json``)
    """
    if Path(file_or_dir).is_file():
        return [file_or_dir]
    return glob.glob(file_or_dir + f'/**/*{ext}', recursive=True)


def chunks(iterable: Iterable, size: int) -> Iterator[Tuple]:
    """Yield successive n-sized chunks from an iterable."""
    iterator = iter(iterable)
    while True:
        chunk = tuple(islice(iterator, size))
        if chunk:
            yield chunk
        else:
            break


def obj_or_import_string(value, default=None):
    """Import string or return object.

    :params value: Import path or class object to instantiate.
    :params default: Default object to return if the import fails.
    :returns: The imported object.
    """
    if isinstance(value, str):
        return import_string(value)
    elif value:
        return value
    return default


def load_or_import_from_config(key: str, app=None, default=None):
    """Load or import value from config.

    :returns: The loaded value.
    """
    app = app or current_app
    imp = app.config.get(key)
    return obj_or_import_string(imp, default=default)


def cached_func(prefix: str, key_func, timeout=60 * 60):
    """Decorator for caching function results in invenio-cache."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            key = f'{prefix}:{key_func(f, *args, **kwargs)}'
            res = current_cache.get(key)
            if not res:
                res = f(*args, **kwargs)
                current_cache.set(key, res, timeout=timeout)
            return res
        return decorated
    return decorator

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
            if len(parts) - github_index > 3:
                resp['sub_type'] = parts[github_index + 3]
                if resp['sub_type'] == 'tree' or resp['sub_type'] == 'commit':  
                    resp['tag'] = parts[github_index + 4]
                elif resp['sub_type'] == 'releases':
                    resp['tag'] = parts[github_index + 5]
                else:
                    raise GitHubAPIException('Not a valid github repo url: ' + url, )
            return resp