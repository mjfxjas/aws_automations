from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("ec2_cleanup")


def ensure_tz(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def instance_matches_patterns(name: str, patterns: List[str]) -> bool:
    if not patterns:
        return True
    import fnmatch
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def instance_has_required_tag(instance: dict, required_tag: dict) -> bool:
    if not required_tag:
        return True
    
    tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
    key = required_tag["key"]
    value = required_tag.get("value")
    
    if key not in tags:
        return False
    if value is not None and tags.get(key) != value:
        return False
    return True


def should_target_instance(instance: dict, config: dict, now: datetime) -> bool:
    instance_id = instance["InstanceId"]
    state = instance["State"]["Name"]
    launch_time = ensure_tz(instance["LaunchTime"])
    
    # Check target/ignore lists
    if config.get("target_instances") and instance_id not in config["target_instances"]:
        return False
    if instance_id in config.get("ignore_instances", []):
        return False
    
    # Check state filter
    if state not in config.get("target_states", ["stopped"]):
        return False
    
    # Check age
    cutoff = now - timedelta(days=config.get("instance_retention_days", 7))
    if launch_time > cutoff:
        logger.debug("Skipping %s: instance age below retention", instance_id)
        return False
    
    # Check name patterns
    name = next((tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"), "")
    if not instance_matches_patterns(name, config.get("name_patterns", [])):
        return False
    
    # Check required tag
    if not instance_has_required_tag(instance, config.get("require_tag")):
        return False
    
    return True


def collect_instance_volumes(ec2_client, instance_id: str) -> List[str]:
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        volumes = []
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                for bdm in instance.get("BlockDeviceMappings", []):
                    if "Ebs" in bdm:
                        volumes.append(bdm["Ebs"]["VolumeId"])
        return volumes
    except ClientError as exc:
        logger.warning("Could not get volumes for %s: %s", instance_id, exc)
        return []


def terminate_instance(ec2_client, instance_id: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would terminate instance %s", instance_id)
        return False
    
    try:
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        logger.info("Terminated instance %s", instance_id)
        return True
    except ClientError as exc:
        logger.warning("Could not terminate instance %s: %s", instance_id, exc)
        return False


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


def run_ec2_cleanup(
    config: dict,
    *,
    dry_run: bool = True,
    session: Optional[boto3.Session] = None,
    progress_callback: Optional[Callable[[Dict[str, object]], None]] = None,
) -> dict:
    now = datetime.now(timezone.utc)
    sess = session or boto3.Session(region_name=config.get("region_name"))
    ec2_client = sess.client("ec2", region_name=config.get("region_name"))
    
    response = ec2_client.describe_instances()
    instances = []
    for reservation in response["Reservations"]:
        instances.extend(reservation["Instances"])
    
    summary = {
        "dry_run": dry_run,
        "instances_scanned": len(instances),
        "instances_terminated": 0,
        "volumes_deleted": 0,
        "instance_reports": [],
    }
    
    for instance in instances:
        if not should_target_instance(instance, config, now):
            continue
        
        instance_id = instance["InstanceId"]
        logger.info("Processing instance %s", instance_id)
        
        volumes = []
        if config.get("delete_volumes", True):
            volumes = collect_instance_volumes(ec2_client, instance_id)
        
        if progress_callback:
            progress_callback(
                {
                    "resource": instance_id,
                    "resource_type": "instance",
                    "status": "planned",
                    "volumes": len(volumes),
                    "deleted": 0,
                }
            )
        
        if terminate_instance(ec2_client, instance_id, dry_run):
            summary["instances_terminated"] += 1
            
            # Delete associated volumes if configured
            for volume_id in volumes:
                if delete_volume(ec2_client, volume_id, dry_run):
                    summary["volumes_deleted"] += 1

        if progress_callback:
            progress_callback(
                {
                    "resource": instance_id,
                    "resource_type": "instance",
                    "status": "completed",
                    "volumes": len(volumes),
                    "deleted": 1 if not dry_run else 0,
                }
            )
        
        summary["instance_reports"].append({
            "instance_id": instance_id,
            "state": instance["State"]["Name"],
            "volumes": volumes,
        })
    
    return summary
