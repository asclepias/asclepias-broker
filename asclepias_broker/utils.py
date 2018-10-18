# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for Asclepias broker."""

from __future__ import absolute_import, print_function

import glob


def find_ext(dirpath, ext):
    """Finds all files of a given extension in given subdirectory.

    :param str dirpath: Path to search (e.g. ``/some/foo/bar/dir``).
    :param str ext: The extension of the files to search for (e.g. ``.json``)
    """
    return glob.glob(dirpath + f'/**/*{ext}', recursive=True)


def chunks(l, n, size):
    """Yield successive n-sized chunks from l."""
    for i in range(0, size, n):
        yield l[i:i + n]
