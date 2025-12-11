from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("cloudwatch_cleanup")


def ensure_tz(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def log_group_matches_patterns(name: str, patterns: List[str]) -> bool:
    if not patterns:
        return True
    import fnmatch
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def get_log_group_last_event(logs_client, log_group_name: str) -> Optional[datetime]:
    try:
        response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy="LastEventTime",
            descending=True,
            limit=1
        )
        
        streams = response.get("logStreams", [])
        if streams and "lastEventTime" in streams[0]:
            return datetime.fromtimestamp(streams[0]["lastEventTime"] / 1000, tz=timezone.utc)
        return None
    except ClientError:
        return None


def should_target_log_group(log_group: dict, config: dict, now: datetime, logs_client) -> bool:
    log_group_name = log_group["logGroupName"]
    
    # Check target/ignore lists
    if config.get("target_log_groups") and log_group_name not in config["target_log_groups"]:
        return False
    if log_group_name in config.get("ignore_log_groups", []):
        return False
    
    # Check name patterns
    if not log_group_matches_patterns(log_group_name, config.get("name_patterns", [])):
        return False
    
    # Check last activity
    retention_days = config.get("log_group_retention_days", 30)
    last_event = get_log_group_last_event(logs_client, log_group_name)
    
    if last_event:
        cutoff = now - timedelta(days=retention_days)
        if last_event > cutoff:
            logger.debug("Skipping %s: recent activity", log_group_name)
            return False
    else:
        # If no events, check creation time
        creation_time = datetime.fromtimestamp(log_group["creationTime"] / 1000, tz=timezone.utc)
        cutoff = now - timedelta(days=retention_days)
        if creation_time > cutoff:
            logger.debug("Skipping %s: log group age below retention", log_group_name)
            return False
    
    return True


def should_target_log_stream(stream: dict, config: dict, now: datetime) -> bool:
    if "lastEventTime" not in stream:
        return False
    
    last_event = datetime.fromtimestamp(stream["lastEventTime"] / 1000, tz=timezone.utc)
    cutoff = now - timedelta(days=config.get("log_stream_retention_days", 7))
    
    return last_event <= cutoff


def delete_log_group(logs_client, log_group_name: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete log group %s", log_group_name)
        return False
    
    try:
        logs_client.delete_log_group(logGroupName=log_group_name)
        logger.info("Deleted log group %s", log_group_name)
        return True
    except ClientError as exc:
        logger.warning("Could not delete log group %s: %s", log_group_name, exc)
        return False


def delete_log_stream(logs_client, log_group_name: str, log_stream_name: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete log stream %s from %s", log_stream_name, log_group_name)
        return False
    
    try:
        logs_client.delete_log_stream(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )
        logger.info("Deleted log stream %s from %s", log_stream_name, log_group_name)
        return True
    except ClientError as exc:
        logger.warning("Could not delete log stream %s: %s", log_stream_name, exc)
        return False


def run_cloudwatch_cleanup(config: dict, *, dry_run: bool = True, session: Optional[boto3.Session] = None) -> dict:
    now = datetime.now(timezone.utc)
    sess = session or boto3.Session(region_name=config.get("region_name"))
    logs_client = sess.client("logs", region_name=config.get("region_name"))
    
    # Get log groups
    paginator = logs_client.get_paginator("describe_log_groups")
    log_groups = []
    for page in paginator.paginate():
        log_groups.extend(page.get("logGroups", []))
    
    summary = {
        "dry_run": dry_run,
        "log_groups_scanned": len(log_groups),
        "log_groups_deleted": 0,
        "log_streams_deleted": 0,
        "log_group_reports": [],
    }
    
    for log_group in log_groups:
        log_group_name = log_group["logGroupName"]
        
        if should_target_log_group(log_group, config, now, logs_client):
            logger.info("Processing log group %s", log_group_name)
            
            if delete_log_group(logs_client, log_group_name, dry_run):
                summary["log_groups_deleted"] += 1
            
            summary["log_group_reports"].append({
                "log_group_name": log_group_name,
                "creation_time": log_group["creationTime"],
            })
        else:
            # Check for old log streams within the group
            try:
                streams_paginator = logs_client.get_paginator("describe_log_streams")
                streams_deleted = 0
                
                for streams_page in streams_paginator.paginate(logGroupName=log_group_name):
                    for stream in streams_page.get("logStreams", []):
                        if should_target_log_stream(stream, config, now):
                            if delete_log_stream(logs_client, log_group_name, stream["logStreamName"], dry_run):
                                streams_deleted += 1
                
                if streams_deleted > 0:
                    summary["log_streams_deleted"] += streams_deleted
                    summary["log_group_reports"].append({
                        "log_group_name": log_group_name,
                        "streams_deleted": streams_deleted,
                    })
            except ClientError as exc:
                logger.warning("Could not process streams for %s: %s", log_group_name, exc)
    
    return summary