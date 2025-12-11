from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("lambda_cleanup")


def ensure_tz(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def function_matches_patterns(name: str, patterns: List[str]) -> bool:
    if not patterns:
        return True
    import fnmatch
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def function_has_required_tag(lambda_client, function_name: str, required_tag: dict) -> bool:
    if not required_tag:
        return True
    
    try:
        response = lambda_client.list_tags(Resource=function_name)
        tags = response.get("Tags", {})
        
        key = required_tag["key"]
        value = required_tag.get("value")
        
        if key not in tags:
            return False
        if value is not None and tags.get(key) != value:
            return False
        return True
    except ClientError:
        return False


def get_function_last_invocation(cloudwatch_client, function_name: str, days: int) -> Optional[datetime]:
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        response = cloudwatch_client.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Invocations",
            Dimensions=[{"Name": "FunctionName", "Value": function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # 1 day
            Statistics=["Sum"]
        )
        
        if response["Datapoints"]:
            return max(dp["Timestamp"] for dp in response["Datapoints"])
        return None
    except ClientError:
        return None


def should_target_function(function: dict, config: dict, now: datetime, cloudwatch_client) -> bool:
    function_name = function["FunctionName"]
    
    # Check target/ignore lists
    if config.get("target_functions") and function_name not in config["target_functions"]:
        return False
    if function_name in config.get("ignore_functions", []):
        return False
    
    # Check name patterns
    if not function_matches_patterns(function_name, config.get("name_patterns", [])):
        return False
    
    # Check last invocation
    retention_days = config.get("function_retention_days", 30)
    last_invocation = get_function_last_invocation(cloudwatch_client, function_name, retention_days)
    
    if last_invocation:
        cutoff = now - timedelta(days=retention_days)
        if ensure_tz(last_invocation) > cutoff:
            logger.debug("Skipping %s: recent invocation", function_name)
            return False
    
    return True


def delete_function_versions(lambda_client, function_name: str, keep_versions: int, dry_run: bool) -> int:
    try:
        response = lambda_client.list_versions_by_function(FunctionName=function_name)
        versions = [v for v in response["Versions"] if v["Version"] != "$LATEST"]
        
        # Sort by version number and keep the latest N
        versions.sort(key=lambda x: int(x["Version"]), reverse=True)
        to_delete = versions[keep_versions:]
        
        deleted = 0
        for version in to_delete:
            if dry_run:
                logger.info("Dry run: would delete version %s of %s", version["Version"], function_name)
                deleted += 1
            else:
                try:
                    lambda_client.delete_function(
                        FunctionName=function_name,
                        Qualifier=version["Version"]
                    )
                    deleted += 1
                except ClientError as exc:
                    logger.warning("Could not delete version %s: %s", version["Version"], exc)
        
        return deleted
    except ClientError as exc:
        logger.warning("Could not list versions for %s: %s", function_name, exc)
        return 0


def delete_function(lambda_client, function_name: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete function %s", function_name)
        return False
    
    try:
        lambda_client.delete_function(FunctionName=function_name)
        logger.info("Deleted function %s", function_name)
        return True
    except ClientError as exc:
        logger.warning("Could not delete function %s: %s", function_name, exc)
        return False


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


def run_lambda_cleanup(config: dict, *, dry_run: bool = True, session: Optional[boto3.Session] = None) -> dict:
    now = datetime.now(timezone.utc)
    sess = session or boto3.Session(region_name=config.get("region_name"))
    lambda_client = sess.client("lambda", region_name=config.get("region_name"))
    cloudwatch_client = sess.client("cloudwatch", region_name=config.get("region_name"))
    logs_client = sess.client("logs", region_name=config.get("region_name"))
    
    response = lambda_client.list_functions()
    functions = response.get("Functions", [])
    
    summary = {
        "dry_run": dry_run,
        "functions_scanned": len(functions),
        "functions_deleted": 0,
        "versions_deleted": 0,
        "log_groups_deleted": 0,
        "function_reports": [],
    }
    
    for function in functions:
        function_name = function["FunctionName"]
        
        if not should_target_function(function, config, now, cloudwatch_client):
            continue
        
        logger.info("Processing function %s", function_name)
        
        # Delete old versions first
        versions_deleted = delete_function_versions(
            lambda_client, 
            function_name, 
            config.get("keep_versions", 3), 
            dry_run
        )
        summary["versions_deleted"] += versions_deleted
        
        # Delete the function entirely if configured
        if delete_function(lambda_client, function_name, dry_run):
            summary["functions_deleted"] += 1
            
            # Delete associated log group
            if config.get("delete_logs", True):
                log_group_name = f"/aws/lambda/{function_name}"
                if delete_log_group(logs_client, log_group_name, dry_run):
                    summary["log_groups_deleted"] += 1
        
        summary["function_reports"].append({
            "function_name": function_name,
            "versions_deleted": versions_deleted,
        })
    
    return summary