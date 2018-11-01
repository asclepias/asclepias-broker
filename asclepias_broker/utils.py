# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 CERN.
#
# Asclepias Broker is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for Asclepias broker."""

from __future__ import absolute_import, print_function

import glob
from pathlib import Path
from typing import List


def find_ext(file_or_dir: str, ext: str = None) -> List[str]:
    """Finds all files of a given extension in given subdirectory.

    :param file_or_dir: Path to search (e.g. ``/some/foo/bar/dir``) or file.
    :param ext: The extension of the files to search for (e.g. ``.json``)
    """
    if Path(file_or_dir).is_file():
        return [file_or_dir]
    return glob.glob(file_or_dir + f'/**/*{ext}', recursive=True)


def chunks(l: List, n: int, size: int):
    """Yield successive n-sized chunks from l."""
    for i in range(0, size, n):
        yield l[i:i + n]
