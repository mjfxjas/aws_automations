from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("ebs_cleanup")


def ensure_tz(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def volume_has_required_tag(volume: dict, required_tag: dict) -> bool:
    if not required_tag:
        return True
    
    tags = {tag["Key"]: tag["Value"] for tag in volume.get("Tags", [])}
    key = required_tag["key"]
    value = required_tag.get("value")
    
    if key not in tags:
        return False
    if value is not None and tags.get(key) != value:
        return False
    return True


def should_target_volume(volume: dict, config: dict, now: datetime) -> bool:
    volume_id = volume["VolumeId"]
    state = volume["State"]
    create_time = ensure_tz(volume["CreateTime"])
    size = volume["Size"]
    
    # Check target/ignore lists
    if config.get("ignore_volumes") and volume_id in config["ignore_volumes"]:
        return False
    
    # Check state filter
    if state not in config.get("target_states", ["available"]):
        return False
    
    # Check age
    cutoff = now - timedelta(days=config.get("volume_retention_days", 7))
    if create_time > cutoff:
        logger.debug("Skipping %s: volume age below retention", volume_id)
        return False
    
    # Check minimum size
    min_size = config.get("min_volume_size_gb", 1)
    if size < min_size:
        logger.debug("Skipping %s: volume size below minimum", volume_id)
        return False
    
    # Check required tag
    if not volume_has_required_tag(volume, config.get("require_tag")):
        return False
    
    return True


def should_target_snapshot(snapshot: dict, config: dict, now: datetime) -> bool:
    snapshot_id = snapshot["SnapshotId"]
    start_time = ensure_tz(snapshot["StartTime"])
    
    # Check target list
    if config.get("target_snapshots") and snapshot_id not in config["target_snapshots"]:
        return False
    
    # Check age
    cutoff = now - timedelta(days=config.get("snapshot_retention_days", 30))
    if start_time > cutoff:
        logger.debug("Skipping %s: snapshot age below retention", snapshot_id)
        return False
    
    return True


def delete_volume(ec2_client, volume_id: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete volume %s", volume_id)
        return False
    
    try:
        ec2_client.delete_volume(VolumeId=volume_id)
        logger.info("Deleted volume %s", volume_id)
        return True
    except ClientError as exc:
        logger.warning("Could not delete volume %s: %s", volume_id, exc)
        return False


def delete_snapshot(ec2_client, snapshot_id: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete snapshot %s", snapshot_id)
        return False
    
    try:
        ec2_client.delete_snapshot(SnapshotId=snapshot_id)
        logger.info("Deleted snapshot %s", snapshot_id)
        return True
    except ClientError as exc:
        logger.warning("Could not delete snapshot %s: %s", snapshot_id, exc)
        return False


def run_ebs_cleanup(
    config: dict,
    *,
    dry_run: bool = True,
    session: Optional[boto3.Session] = None,
    progress_callback: Optional[Callable[[Dict[str, object]], None]] = None,
) -> dict:
    now = datetime.now(timezone.utc)
    sess = session or boto3.Session(region_name=config.get("region_name"))
    ec2_client = sess.client("ec2", region_name=config.get("region_name"))
    
    # Get volumes
    volumes_response = ec2_client.describe_volumes()
    volumes = volumes_response.get("Volumes", [])
    
    # Get snapshots (only owned by this account)
    snapshots_response = ec2_client.describe_snapshots(OwnerIds=["self"])
    snapshots = snapshots_response.get("Snapshots", [])
    
    summary = {
        "dry_run": dry_run,
        "volumes_scanned": len(volumes),
        "snapshots_scanned": len(snapshots),
        "volumes_deleted": 0,
        "snapshots_deleted": 0,
        "volume_reports": [],
        "snapshot_reports": [],
    }
    
    # Process volumes
    for volume in volumes:
        if not should_target_volume(volume, config, now):
            continue
        
        volume_id = volume["VolumeId"]
        logger.info("Processing volume %s", volume_id)
        
        if progress_callback:
            progress_callback(
                {
                    "resource": volume_id,
                    "resource_type": "volume",
                    "status": "planned",
                    "deleted": 0,
                }
            )
        
        if delete_volume(ec2_client, volume_id, dry_run):
            summary["volumes_deleted"] += 1

        if progress_callback:
            progress_callback(
                {
                    "resource": volume_id,
                    "resource_type": "volume",
                    "status": "completed",
                    "deleted": 1 if not dry_run else 0,
                }
            )
        
        summary["volume_reports"].append({
            "volume_id": volume_id,
            "state": volume["State"],
            "size": volume["Size"],
        })
    
    # Process snapshots
    for snapshot in snapshots:
        if not should_target_snapshot(snapshot, config, now):
            continue
        
        snapshot_id = snapshot["SnapshotId"]
        logger.info("Processing snapshot %s", snapshot_id)
        
        if progress_callback:
            progress_callback(
                {
                    "resource": snapshot_id,
                    "resource_type": "snapshot",
                    "status": "planned",
                    "deleted": 0,
                }
            )
        
        if delete_snapshot(ec2_client, snapshot_id, dry_run):
            summary["snapshots_deleted"] += 1
        
        summary["snapshot_reports"].append({
            "snapshot_id": snapshot_id,
            "state": snapshot["State"],
            "volume_size": snapshot["VolumeSize"],
        })
        
        if progress_callback:
            progress_callback(
                {
                    "resource": snapshot_id,
                    "resource_type": "snapshot",
                    "status": "completed",
                    "deleted": 1 if not dry_run else 0,
                }
            )
    
    return summary
