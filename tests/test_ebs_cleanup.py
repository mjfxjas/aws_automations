"""Progress must report the result of deletion, including rejected requests."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from aws_automations.ebs_cleanup import run_ebs_cleanup


@pytest.mark.parametrize("kind", ["volume", "snapshot"])
@pytest.mark.parametrize("dry_run, denied, status, count", [
    (True, False, "planned", 0),
    (False, False, "completed", 1),
    (False, True, "failed", 0),
])
def test_deletion_progress_matches_result(kind, dry_run, denied, status, count):
    session = Mock()
    ec2 = session.client.return_value
    old = datetime.now(timezone.utc) - timedelta(days=90)
    volume = {"VolumeId": "vol-test", "State": "available", "CreateTime": old, "Size": 8}
    snapshot = {"SnapshotId": "snap-test", "StartTime": old,
                "State": "completed", "VolumeSize": 8}
    pages = {
        "describe_volumes": [{"Volumes": [volume] if kind == "volume" else []}],
        "describe_snapshots": [{"Snapshots": [snapshot] if kind == "snapshot" else []}],
    }
    ec2.get_paginator.side_effect = lambda operation: Mock(
        paginate=Mock(return_value=pages[operation]))
    delete = ec2.delete_volume if kind == "volume" else ec2.delete_snapshot
    if denied:
        delete.side_effect = ClientError(
            {"Error": {"Code": "UnauthorizedOperation", "Message": "Denied"}}, "Delete")
    events = []
    summary = run_ebs_cleanup({}, dry_run=dry_run, session=session, progress_callback=events.append)
    assert summary[f"{kind}s_deleted"] == count
    assert events[-1]["deleted"] == count
    assert events[-1]["status"] == status
    if dry_run:
        delete.assert_not_called()
    elif kind == "volume":
        delete.assert_called_once_with(VolumeId="vol-test")
    else:
        delete.assert_called_once_with(SnapshotId="snap-test")
