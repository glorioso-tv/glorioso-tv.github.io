"""Compatibility shim for legacy OpenWizard imports.

Kodi 21 runs on Python 3, so the bundled Python 2 zipfile fork is no
longer usable. Re-export the standard library module instead.
"""

from zipfile import *  # noqa: F401,F403
