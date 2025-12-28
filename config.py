#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Compat: conserver `config.py` à la racine.

La config runtime vit désormais dans `redcam.app.config`.
Ce fichier existe uniquement pour éviter de casser les anciens imports.
"""

from __future__ import annotations

import os
import sys


def _ensure_src_on_path() -> None:
	if getattr(sys, "frozen", False):
		return
	repo_root = os.path.dirname(os.path.abspath(__file__))
	src_path = os.path.join(repo_root, "src")
	if src_path not in sys.path:
		sys.path.insert(0, src_path)


_ensure_src_on_path()

from redcam.app.config import *  # noqa: F401,F403,E402
