#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Callable, Dict

import yaml
from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from .cloudwatch_cleanup import run_cloudwatch_cleanup
from .ebs_cleanup import run_ebs_cleanup
from .ec2_cleanup import run_ec2_cleanup
from .iam_cleanup import run_iam_cleanup
from .lambda_cleanup import run_lambda_cleanup
from .s3_cleanup import run_cleanup as run_s3_cleanup

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
    parser.add_argument("--interactive", action="store_true", help="Enable interactive approval for each resource")
    parser.add_argument(
        "--live",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show a live table of cleanup progress (default on TTY).",
    )
    
    # Service-specific overrides
    parser.add_argument("--bucket", action="append", help="S3: Target specific buckets")
    parser.add_argument("--delete-all-objects", action="store_true", help="S3: Delete all objects regardless of age")
    parser.add_argument("--force-zero-retention", action="store_true", help="S3: Allow zero retention with --apply")
    parser.add_argument("--force-delete-all", action="store_true", help="S3: Allow delete-all with --apply")
    
    return parser.parse_args()


def run_service_cleanup(
    service: str,
    config: dict,
    dry_run: bool,
    progress_callback: Callable[[Dict[str, object]], None] | None = None,
) -> dict:
    """Run cleanup for a specific service."""
    service_config = config.get(service, {})
    service_config["region_name"] = config.get("region_name")
    
    if service == "s3":
        # Convert flat config to nested for backward compatibility
        from .config import CleanupConfig
        if "s3" not in config:
            # Old format - convert to new format
            s3_config = CleanupConfig.from_dict(config)
            return run_s3_cleanup(s3_config, dry_run=dry_run, progress_callback=progress_callback)
        else:
            # New format
            s3_config = CleanupConfig.from_dict(service_config)
            return run_s3_cleanup(s3_config, dry_run=dry_run, progress_callback=progress_callback)
    elif service == "ec2":
        return run_ec2_cleanup(service_config, dry_run=dry_run, progress_callback=progress_callback)
    elif service == "lambda":
        return run_lambda_cleanup(service_config, dry_run=dry_run, progress_callback=progress_callback)
    elif service == "ebs":
        return run_ebs_cleanup(service_config, dry_run=dry_run, progress_callback=progress_callback)
    elif service == "cloudwatch":
        return run_cloudwatch_cleanup(service_config, dry_run=dry_run, progress_callback=progress_callback)
    elif service == "iam":
        return run_iam_cleanup(service_config, dry_run=dry_run, progress_callback=progress_callback)
    else:
        raise ValueError(f"Unknown service: {service}")


def format_details(report: Dict[str, object]) -> str:
    parts = []
    if "objects_planned" in report:
        parts.append(f"objs {report.get('objects_deleted', 0)}/{report.get('objects_planned', 0)}")
    if "versions_planned" in report:
        parts.append(f"vers {report.get('versions_deleted', 0)}/{report.get('versions_planned', 0)}")
    if "volumes" in report:
        parts.append(f"vols {report.get('volumes')}")
    if "streams_deleted" in report:
        parts.append(f"streams {report.get('streams_deleted')}")
    if "versions_deleted" in report and "objects_planned" not in report:
        parts.append(f"vers_del {report.get('versions_deleted')}")
    if "deleted" in report:
        parts.append(f"deleted {report.get('deleted')}")
    return ", ".join(str(p) for p in parts if p is not None) or "-"


def render_live_state(state: Dict[str, Dict[str, dict]], *, dry_run: bool) -> Table:
    table = Table(title="AWS Cleanup Progress", expand=True, box=box.MINIMAL)
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Resource", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Details")

    for service in sorted(state.keys()):
        for resource in sorted(state[service].keys()):
            report = state[service][resource]
            table.add_row(
                service,
                resource,
                str(report.get("resource_type", "-")),
                str(report.get("status", "-")),
                format_details(report),
            )

    footer = Text(f"Mode: {'dry-run' if dry_run else 'apply'} | Services tracked: {len(state)}", style="bold")
    table.caption = footer
    return table


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s"
    )
    console = Console()
    live_enabled = args.live if args.live is not None else (sys.stdout.isatty() and not args.json)
    state: Dict[str, Dict[str, dict]] = {}
    live_instance: Live | None = None
    
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

    def make_progress_callback(service_name: str) -> Callable[[Dict[str, object]], None]:
        def _cb(report: Dict[str, object]) -> None:
            resource = str(report.get("resource", "unknown"))
            report["status"] = report.get("status", "in_progress")
            report["resource_type"] = report.get("resource_type", report.get("type", "-"))
            state.setdefault(service_name, {})[resource] = report
            if live_instance:
                live_instance.update(render_live_state(state, dry_run=not args.apply))
        return _cb

    try:
        if live_enabled:
            with Live(render_live_state(state, dry_run=not args.apply), console=console, refresh_per_second=4) as live:
                live_instance = live
                for service in services:
                    logger.info(f"Running {service} cleanup...")
                    try:
                        result = run_service_cleanup(
                            service,
                            config,
                            dry_run=not args.apply,
                            progress_callback=make_progress_callback(service),
                        )
                        results[service] = result
                        if not args.json:
                            logger.info(f"{service.upper()} cleanup completed: {result}")
                    except Exception as e:
                        logger.error(f"Error in {service} cleanup: {e}")
                        results[service] = {"error": str(e)}
        else:
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
    finally:
        live_instance = None
    
    # Output results
    if args.json:
        print(json.dumps(results, default=str, indent=2))
    else:
        logger.info("All cleanup operations completed")


if __name__ == "__main__":
    main()
