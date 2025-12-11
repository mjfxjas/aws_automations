from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("iam_cleanup")


def ensure_tz(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def resource_matches_patterns(name: str, patterns: List[str]) -> bool:
    if not patterns:
        return True
    import fnmatch
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def get_role_last_activity(iam_client, role_name: str) -> Optional[datetime]:
    try:
        response = iam_client.get_role(RoleName=role_name)
        role = response["Role"]
        
        # Check RoleLastUsed if available
        if "RoleLastUsed" in role and "LastUsedDate" in role["RoleLastUsed"]:
            return ensure_tz(role["RoleLastUsed"]["LastUsedDate"])
        
        # Fall back to creation date
        return ensure_tz(role["CreateDate"])
    except ClientError:
        return None


def get_user_last_activity(iam_client, user_name: str) -> Optional[datetime]:
    try:
        response = iam_client.get_user(UserName=user_name)
        user = response["User"]
        
        # Check password last used
        if "PasswordLastUsed" in user:
            return ensure_tz(user["PasswordLastUsed"])
        
        # Fall back to creation date
        return ensure_tz(user["CreateDate"])
    except ClientError:
        return None


def should_target_role(role: dict, config: dict, now: datetime, iam_client) -> bool:
    role_name = role["RoleName"]
    
    # Skip AWS service roles
    if role["Path"].startswith("/aws-service-role/"):
        return False
    
    # Check ignore list
    if role_name in config.get("ignore_roles", []):
        return False
    
    # Check name patterns
    if not resource_matches_patterns(role_name, config.get("name_patterns", [])):
        return False
    
    # Check last activity
    retention_days = config.get("role_retention_days", 30)
    last_activity = get_role_last_activity(iam_client, role_name)
    
    if last_activity:
        cutoff = now - timedelta(days=retention_days)
        if last_activity > cutoff:
            logger.debug("Skipping %s: recent activity", role_name)
            return False
    
    return True


def should_target_user(user: dict, config: dict, now: datetime, iam_client) -> bool:
    user_name = user["UserName"]
    
    # Check ignore list
    if user_name in config.get("ignore_users", []):
        return False
    
    # Check name patterns
    if not resource_matches_patterns(user_name, config.get("name_patterns", [])):
        return False
    
    # Check last activity
    retention_days = config.get("user_retention_days", 30)
    last_activity = get_user_last_activity(iam_client, user_name)
    
    if last_activity:
        cutoff = now - timedelta(days=retention_days)
        if last_activity > cutoff:
            logger.debug("Skipping %s: recent activity", user_name)
            return False
    
    return True


def should_target_policy(policy: dict, config: dict, now: datetime) -> bool:
    policy_name = policy["PolicyName"]
    
    # Skip AWS managed policies
    if policy["Arn"].startswith("arn:aws:iam::aws:"):
        return False
    
    # Check ignore list
    if policy_name in config.get("ignore_policies", []):
        return False
    
    # Check name patterns
    if not resource_matches_patterns(policy_name, config.get("name_patterns", [])):
        return False
    
    # Check age
    retention_days = config.get("policy_retention_days", 30)
    create_date = ensure_tz(policy["CreateDate"])
    cutoff = now - timedelta(days=retention_days)
    
    if create_date > cutoff:
        logger.debug("Skipping %s: policy age below retention", policy_name)
        return False
    
    return True


def delete_role(iam_client, role_name: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete role %s", role_name)
        return False
    
    try:
        # Detach managed policies
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in response.get("AttachedPolicies", []):
            iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy["PolicyArn"])
        
        # Delete inline policies
        response = iam_client.list_role_policies(RoleName=role_name)
        for policy_name in response.get("PolicyNames", []):
            iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        
        # Delete instance profiles
        response = iam_client.list_instance_profiles_for_role(RoleName=role_name)
        for profile in response.get("InstanceProfiles", []):
            iam_client.remove_role_from_instance_profile(
                InstanceProfileName=profile["InstanceProfileName"],
                RoleName=role_name
            )
        
        # Delete the role
        iam_client.delete_role(RoleName=role_name)
        logger.info("Deleted role %s", role_name)
        return True
    except ClientError as exc:
        logger.warning("Could not delete role %s: %s", role_name, exc)
        return False


def delete_user(iam_client, user_name: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete user %s", user_name)
        return False
    
    try:
        # Delete access keys
        response = iam_client.list_access_keys(UserName=user_name)
        for key in response.get("AccessKeyMetadata", []):
            iam_client.delete_access_key(UserName=user_name, AccessKeyId=key["AccessKeyId"])
        
        # Detach managed policies
        response = iam_client.list_attached_user_policies(UserName=user_name)
        for policy in response.get("AttachedPolicies", []):
            iam_client.detach_user_policy(UserName=user_name, PolicyArn=policy["PolicyArn"])
        
        # Delete inline policies
        response = iam_client.list_user_policies(UserName=user_name)
        for policy_name in response.get("PolicyNames", []):
            iam_client.delete_user_policy(UserName=user_name, PolicyName=policy_name)
        
        # Remove from groups
        response = iam_client.get_groups_for_user(UserName=user_name)
        for group in response.get("Groups", []):
            iam_client.remove_user_from_group(GroupName=group["GroupName"], UserName=user_name)
        
        # Delete login profile if exists
        try:
            iam_client.delete_login_profile(UserName=user_name)
        except ClientError:
            pass  # Login profile might not exist
        
        # Delete the user
        iam_client.delete_user(UserName=user_name)
        logger.info("Deleted user %s", user_name)
        return True
    except ClientError as exc:
        logger.warning("Could not delete user %s: %s", user_name, exc)
        return False


def delete_policy(iam_client, policy_arn: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete policy %s", policy_arn)
        return False
    
    try:
        # Delete all policy versions except default
        response = iam_client.list_policy_versions(PolicyArn=policy_arn)
        for version in response.get("Versions", []):
            if not version["IsDefaultVersion"]:
                iam_client.delete_policy_version(
                    PolicyArn=policy_arn,
                    VersionId=version["VersionId"]
                )
        
        # Delete the policy
        iam_client.delete_policy(PolicyArn=policy_arn)
        logger.info("Deleted policy %s", policy_arn)
        return True
    except ClientError as exc:
        logger.warning("Could not delete policy %s: %s", policy_arn, exc)
        return False


def run_iam_cleanup(config: dict, *, dry_run: bool = True, session: Optional[boto3.Session] = None) -> dict:
    now = datetime.now(timezone.utc)
    sess = session or boto3.Session(region_name=config.get("region_name"))
    iam_client = sess.client("iam")
    
    # Get resources
    roles_paginator = iam_client.get_paginator("list_roles")
    users_paginator = iam_client.get_paginator("list_users")
    policies_paginator = iam_client.get_paginator("list_policies")
    
    roles = []
    for page in roles_paginator.paginate():
        roles.extend(page.get("Roles", []))
    
    users = []
    for page in users_paginator.paginate():
        users.extend(page.get("Users", []))
    
    policies = []
    for page in policies_paginator.paginate(Scope="Local"):  # Only customer managed policies
        policies.extend(page.get("Policies", []))
    
    summary = {
        "dry_run": dry_run,
        "roles_scanned": len(roles),
        "users_scanned": len(users),
        "policies_scanned": len(policies),
        "roles_deleted": 0,
        "users_deleted": 0,
        "policies_deleted": 0,
        "iam_reports": [],
    }
    
    # Process roles
    for role in roles:
        if not should_target_role(role, config, now, iam_client):
            continue
        
        role_name = role["RoleName"]
        logger.info("Processing role %s", role_name)
        
        if delete_role(iam_client, role_name, dry_run):
            summary["roles_deleted"] += 1
        
        summary["iam_reports"].append({
            "resource_type": "role",
            "resource_name": role_name,
        })
    
    # Process users
    for user in users:
        if not should_target_user(user, config, now, iam_client):
            continue
        
        user_name = user["UserName"]
        logger.info("Processing user %s", user_name)
        
        if delete_user(iam_client, user_name, dry_run):
            summary["users_deleted"] += 1
        
        summary["iam_reports"].append({
            "resource_type": "user",
            "resource_name": user_name,
        })
    
    # Process policies
    for policy in policies:
        if not should_target_policy(policy, config, now):
            continue
        
        policy_name = policy["PolicyName"]
        policy_arn = policy["Arn"]
        logger.info("Processing policy %s", policy_name)
        
        if delete_policy(iam_client, policy_arn, dry_run):
            summary["policies_deleted"] += 1
        
        summary["iam_reports"].append({
            "resource_type": "policy",
            "resource_name": policy_name,
        })
    
    return summary