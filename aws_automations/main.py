#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from .s3_cleanup import run_cleanup as run_s3_cleanup
from .ec2_cleanup import run_ec2_cleanup
from .lambda_cleanup import run_lambda_cleanup
from .ebs_cleanup import run_ebs_cleanup
from .cloudwatch_cleanup import run_cloudwatch_cleanup
from .iam_cleanup import run_iam_cleanup

logger = logging.getLogger("aws_automations")


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file) as f:
        return yaml.safe_load(f) or {}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AWS Resource Cleanup Automation")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--apply", action="store_true", help="Apply deletions (default: dry-run)")
    parser.add_argument("--service", choices=["s3", "ec2", "lambda", "ebs", "cloudwatch", "iam", "all"], 
                       default="all", help="Service to clean up")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    
    # Service-specific overrides
    parser.add_argument("--bucket", action="append", help="S3: Target specific buckets")
    parser.add_argument("--delete-all-objects", action="store_true", help="S3: Delete all objects regardless of age")
    parser.add_argument("--force-zero-retention", action="store_true", help="S3: Allow zero retention with --apply")
    parser.add_argument("--force-delete-all", action="store_true", help="S3: Allow delete-all with --apply")
    
    return parser.parse_args()


def run_service_cleanup(service: str, config: dict, dry_run: bool) -> dict:
    """Run cleanup for a specific service."""
    service_config = config.get(service, {})
    service_config["region_name"] = config.get("region_name")
    
    if service == "s3":
        # Convert flat config to nested for backward compatibility
        from .config import CleanupConfig
        if "s3" not in config:
            # Old format - convert to new format
            s3_config = CleanupConfig.from_dict(config)
            return run_s3_cleanup(s3_config, dry_run=dry_run)
        else:
            # New format
            s3_config = CleanupConfig.from_dict(service_config)
            return run_s3_cleanup(s3_config, dry_run=dry_run)
    elif service == "ec2":
        return run_ec2_cleanup(service_config, dry_run=dry_run)
    elif service == "lambda":
        return run_lambda_cleanup(service_config, dry_run=dry_run)
    elif service == "ebs":
        return run_ebs_cleanup(service_config, dry_run=dry_run)
    elif service == "cloudwatch":
        return run_cloudwatch_cleanup(service_config, dry_run=dry_run)
    elif service == "iam":
        return run_iam_cleanup(service_config, dry_run=dry_run)
    else:
        raise ValueError(f"Unknown service: {service}")


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s"
    )
    
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)
    
    # Safety checks for S3
    if args.service in ["s3", "all"]:
        s3_config = config.get("s3", config)  # Backward compatibility
        
        if args.apply:
            if args.delete_all_objects or s3_config.get("delete_all_objects"):
                if not args.force_delete_all:
                    logger.error("delete_all_objects enabled; use --force-delete-all with --apply")
                    sys.exit(1)
            
            retention = s3_config.get("object_retention_days")
            if retention is not None and retention <= 0 and not args.force_zero_retention:
                logger.error("object_retention_days is 0; use --force-zero-retention with --apply")
                sys.exit(1)
    
    # Apply CLI overrides for S3
    if args.delete_all_objects and "s3" in config:
        config["s3"]["delete_all_objects"] = True
    elif args.delete_all_objects:
        config["delete_all_objects"] = True
    
    # Run cleanup
    services = ["s3", "ec2", "lambda", "ebs", "cloudwatch", "iam"] if args.service == "all" else [args.service]
    results = {}
    
    for service in services:
        logger.info(f"Running {service} cleanup...")
        try:
            result = run_service_cleanup(service, config, dry_run=not args.apply)
            results[service] = result
            
            if not args.json:
                logger.info(f"{service.upper()} cleanup completed: {result}")
        except Exception as e:
            logger.error(f"Error in {service} cleanup: {e}")
            results[service] = {"error": str(e)}
    
    # Output results
    if args.json:
        print(json.dumps(results, default=str, indent=2))
    else:
        logger.info("All cleanup operations completed")


if __name__ == "__main__":
    main()