# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for Asclepias broker."""

from __future__ import absolute_import, print_function

import glob
from itertools import islice
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

from flask import current_app
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
