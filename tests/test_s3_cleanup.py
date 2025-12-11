from __future__ import annotations

import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.append(str(Path(__file__).resolve().parents[1]))

from aws_automations.config import CleanupConfig  # noqa: E402
from aws_automations.s3_cleanup import run_cleanup  # noqa: E402


@pytest.fixture()
def s3_client():
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")


def test_cleanup_deletes_objects_and_bucket(s3_client):
    bucket = "sandbox-clean-me"
    s3_client.create_bucket(Bucket=bucket)
    s3_client.put_object(Bucket=bucket, Key="old.txt", Body=b"data")

    config = CleanupConfig(
        region_name="us-east-1",
        bucket_prefixes=["sandbox-"],
        bucket_retention_days=0,
        object_retention_days=0,
        delete_all_objects=True,
        delete_empty_buckets=True,
    )

    summary = run_cleanup(config, dry_run=False)

    buckets_remaining = [b["Name"] for b in s3_client.list_buckets().get("Buckets", [])]
    assert summary["objects_deleted"] >= 1
    assert bucket not in buckets_remaining


def test_cleanup_respects_ignore_and_prefix(s3_client):
    target = "sandbox-target"
    ignored = "sandbox-ignored"
    outside = "prod-dont-touch"

    for bucket in (target, ignored, outside):
        s3_client.create_bucket(Bucket=bucket)
        s3_client.put_object(Bucket=bucket, Key="file.txt", Body=b"data")

    config = CleanupConfig(
        region_name="us-east-1",
        bucket_prefixes=["sandbox-"],
        ignore_buckets=[ignored],
        bucket_retention_days=0,
        object_retention_days=0,
        delete_all_objects=True,
    )

    summary = run_cleanup(config, dry_run=False)

    untouched = s3_client.list_objects_v2(Bucket=ignored)
    prod_objects = s3_client.list_objects_v2(Bucket=outside)

    assert summary["objects_deleted"] >= 1
    assert untouched.get("KeyCount", 0) == 1
    assert prod_objects.get("KeyCount", 0) == 1


def test_tag_filter_limits_scope(s3_client):
    tagged = "sandbox-tagged"
    untagged = "sandbox-untagged"

    for bucket in (tagged, untagged):
        s3_client.create_bucket(Bucket=bucket)
        s3_client.put_object(Bucket=bucket, Key="file.txt", Body=b"data")

    s3_client.put_bucket_tagging(
        Bucket=tagged,
        Tagging={"TagSet": [{"Key": "cleanup", "Value": "true"}]},
    )

    config = CleanupConfig(
        region_name="us-east-1",
        bucket_prefixes=["sandbox-"],
        bucket_retention_days=0,
        object_retention_days=0,
        delete_all_objects=True,
        require_tag={"key": "cleanup", "value": "true"},
    )

    # Normalize require_tag through from_dict to exercise parsing
    config = CleanupConfig.from_dict(config.__dict__)
    summary = run_cleanup(config, dry_run=False)

    tagged_objects = s3_client.list_objects_v2(Bucket=tagged)
    untagged_objects = s3_client.list_objects_v2(Bucket=untagged)

    assert summary["objects_deleted"] >= 1
    assert tagged_objects.get("KeyCount", 0) == 0
    assert untagged_objects.get("KeyCount", 0) == 1
