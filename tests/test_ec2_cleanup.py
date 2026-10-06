"""Verify progress reports reflect actual termination outcomes."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from aws_automations.ec2_cleanup import run_ec2_cleanup


@pytest.mark.parametrize('dry_run, denied, status, count', [
    (True, False, 'planned', 0),
    (False, False, 'completed', 1),
    (False, True, 'failed', 0),
])
def test_termination_progress_matches_result(dry_run, denied, status, count):
    session = Mock()
    ec2 = session.client.return_value
    ec2.get_paginator.return_value.paginate.return_value = [{
        'Reservations': [{'Instances': [{
            'InstanceId': 'i-test', 'State': {'Name': 'stopped'},
            'LaunchTime': datetime.now(timezone.utc) - timedelta(days=30),
        }]}],
    }]
    if denied:
        ec2.terminate_instances.side_effect = ClientError(
            {'Error': {'Code': 'UnauthorizedOperation', 'Message': 'Denied'}}, 'TerminateInstances')
    events = []
    summary = run_ec2_cleanup({'delete_volumes': False}, dry_run=dry_run,
                              session=session, progress_callback=events.append)
    assert summary['instances_terminated'] == count
    assert events[-1]['deleted'] == count
    assert events[-1]['status'] == status
    if dry_run:
        ec2.terminate_instances.assert_not_called()
    else:
        ec2.terminate_instances.assert_called_once_with(InstanceIds=['i-test'])
