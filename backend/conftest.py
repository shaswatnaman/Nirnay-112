"""Pytest configuration.

Makes the ``app`` package importable when tests are run from the ``backend/``
directory, regardless of pytest's import mode. The deterministic decision-engine
tests depend only on the standard library, so no application services
(OpenAI, FastAPI, etc.) need to be installed to run them.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
