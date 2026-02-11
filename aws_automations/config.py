from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class BucketTagFilter:
    """Optional tag requirement for selecting buckets."""

    key: str
    value: Optional[str] = None


@dataclass
class CleanupConfig:
    """User configurable settings for S3 cleanup."""

    region_name: Optional[str] = None
    bucket_prefixes: List[str] = field(default_factory=list)
    ignore_buckets: List[str] = field(default_factory=list)
    target_buckets: List[str] = field(default_factory=list)
    bucket_retention_days: Optional[int] = 30
    object_retention_days: Optional[int] = 30
    delete_empty_buckets: bool = False
    delete_all_objects: bool = False
    include_versioned_objects: bool = True
    require_tag: Optional[BucketTagFilter] = None
    max_delete_batch: int = 1000

    @staticmethod
    def from_file(path: str | Path) -> "CleanupConfig":
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        raw = yaml.safe_load(config_path.read_text()) or {}
        if isinstance(raw, dict) and isinstance(raw.get("s3"), dict):
            s3_raw = dict(raw["s3"])
            if "region_name" in raw and "region_name" not in s3_raw:
                s3_raw["region_name"] = raw["region_name"]
            raw = s3_raw
        return CleanupConfig.from_dict(raw)

    @staticmethod
    def from_dict(data: dict) -> "CleanupConfig":
        tag_filter = CleanupConfig._parse_tag_filter(data.get("require_tag"))
        return CleanupConfig(
            region_name=data.get("region_name"),
            bucket_prefixes=list(data.get("bucket_prefixes", []) or []),
            ignore_buckets=list(data.get("ignore_buckets", []) or []),
            target_buckets=list(data.get("target_buckets", []) or []),
            bucket_retention_days=data.get("bucket_retention_days", 30),
            object_retention_days=data.get("object_retention_days", 30),
            delete_empty_buckets=bool(data.get("delete_empty_buckets", False)),
            delete_all_objects=bool(data.get("delete_all_objects", False)),
            include_versioned_objects=bool(data.get("include_versioned_objects", True)),
            require_tag=tag_filter,
            max_delete_batch=int(data.get("max_delete_batch", 1000)),
        )

    @staticmethod
    def _parse_tag_filter(raw: Optional[dict]) -> Optional[BucketTagFilter]:
        if not raw:
            return None
        if isinstance(raw, BucketTagFilter):
            return raw
        if not isinstance(raw, dict) or "key" not in raw:
            raise ValueError("require_tag must be a mapping with at least a 'key'")

        return BucketTagFilter(key=str(raw["key"]), value=None if raw.get("value") is None else str(raw["value"]))


__all__ = ["BucketTagFilter", "CleanupConfig"]
