import os
import sys
from types import ModuleType
from unittest.mock import MagicMock


class _MockModule(ModuleType):
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return MagicMock()


def _ensure_mock(name, is_package=True):
    if name not in sys.modules:
        mod = _MockModule(name)
        if is_package:
            mod.__path__ = []
        sys.modules[name] = mod


for name in ["pyaudio", "pyttsx3", "transformers"]:
    _ensure_mock(name)

import pytest
from app import app, db
import app as app_module

# Shutdown the background scheduler that app.py starts at module level
try:
    app_module.scheduler.shutdown(wait=False)
except Exception:
    pass
