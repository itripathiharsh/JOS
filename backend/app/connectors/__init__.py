"""
App connectors wrapper to provide convenient imports from within the backend application.
"""
import sys
import os

# Ensure root workspace directory is in python path
workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from connectors import JobSource, RemotiveSource, NormalizedJob, SourceHealth, IngestionStats

__all__ = [
    "JobSource",
    "RemotiveSource",
    "NormalizedJob",
    "SourceHealth",
    "IngestionStats",
]
