"""Managed FASTA dataset pools (filesystem + JSON manifests)."""

from dataset_pools.config import get_datasets_root, path_import_allowed
from dataset_pools.repository import DatasetRepository

__all__ = ["DatasetRepository", "get_datasets_root", "path_import_allowed"]
