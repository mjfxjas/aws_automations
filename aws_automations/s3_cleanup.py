from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Iterable, List, Optional, Sequence

import boto3
from botocore.exceptions import ClientError
from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import BucketTagFilter, CleanupConfig

logger = logging.getLogger("s3_cleanup")


def chunked(items: Sequence[dict], size: int) -> Iterable[List[dict]]:
    for idx in range(0, len(items), size):
        yield list(items[idx : idx + size])


def ensure_tz(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def bucket_matches_prefixes(name: str, prefixes: List[str]) -> bool:
    if not prefixes:
        return True
    return any(name.startswith(prefix) for prefix in prefixes)


def bucket_has_required_tag(client, bucket: str, required_tag: BucketTagFilter) -> bool:
    try:
        response = client.get_bucket_tagging(Bucket=bucket)
    except ClientError as exc:  # noqa: PERF203 - explicit branches help logging
        logger.info("Skipping %s: cannot read tags (%s)", bucket, exc.response.get("Error", {}).get("Code"))
        return False

    tags = {tag["Key"]: tag["Value"] for tag in response.get("TagSet", [])}
    if required_tag.key not in tags:
        logger.debug("Skipping %s: tag %s missing", bucket, required_tag.key)
        return False
    if required_tag.value is not None and tags.get(required_tag.key) != required_tag.value:
        logger.debug("Skipping %s: tag %s value mismatch", bucket, required_tag.key)
        return False
    return True


def should_target_bucket(
    bucket_name: str,
    creation_date: datetime,
    config: CleanupConfig,
    now: datetime,
    s3_client,
    targeted_bucket_override: Optional[List[str]] = None,
) -> bool:
    override = targeted_bucket_override or []
    if override and bucket_name not in override:
        return False
    if config.target_buckets and bucket_name not in config.target_buckets:
        return False
    if bucket_name in config.ignore_buckets:
        return False
    if not bucket_matches_prefixes(bucket_name, config.bucket_prefixes):
        return False
    if config.bucket_retention_days is not None:
        cutoff = now - timedelta(days=config.bucket_retention_days)
        if ensure_tz(creation_date) > cutoff:
            logger.debug("Skipping %s: bucket age below retention", bucket_name)
            return False
    if config.require_tag and not bucket_has_required_tag(s3_client, bucket_name, config.require_tag):
        return False
    return True


def collect_objects_for_deletion(s3_client, bucket: str, config: CleanupConfig, now: datetime) -> List[dict]:
    if config.object_retention_days is None and not config.delete_all_objects:
        return []

    cutoff = None if config.delete_all_objects else now - timedelta(days=config.object_retention_days or 0)
    paginator = s3_client.get_paginator("list_objects_v2")
    deletions: List[dict] = []

    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            last_modified = ensure_tz(obj["LastModified"])
            if config.delete_all_objects or last_modified <= cutoff:
                deletions.append({"Key": obj["Key"]})
    return deletions


def collect_versions_for_deletion(s3_client, bucket: str, config: CleanupConfig, now: datetime) -> List[dict]:
    if not config.include_versioned_objects:
        return []
    if config.object_retention_days is None and not config.delete_all_objects:
        return []
    cutoff = None if config.delete_all_objects else now - timedelta(days=config.object_retention_days or 0)
    paginator = s3_client.get_paginator("list_object_versions")
    deletions: List[dict] = []

    try:
        page_iterator = paginator.paginate(Bucket=bucket)
    except ClientError as exc:  # noqa: PERF203 - explicit branch for logging
        logger.info("Skipping version scan for %s: %s", bucket, exc.response.get("Error", {}).get("Code"))
        return []

    for page in page_iterator:
        versions = page.get("Versions", []) + page.get("DeleteMarkers", [])
        for version in versions:
            last_modified = ensure_tz(version["LastModified"])
            if config.delete_all_objects or last_modified <= cutoff:
                deletions.append({"Key": version["Key"], "VersionId": version.get("VersionId")})
    return deletions


def delete_objects(s3_client, bucket: str, objects: List[dict], dry_run: bool, batch_size: int) -> int:
    if not objects:
        return 0

    deleted = 0
    for batch in chunked(objects, batch_size):
        if dry_run:
            logger.info("Dry run: would delete %s objects from %s", len(batch), bucket)
            deleted += len(batch)
            continue

        resp = s3_client.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
        deleted += len(resp.get("Deleted", []))
    return deleted


def bucket_is_empty(s3_client, bucket: str) -> bool:
    obj_resp = s3_client.list_objects_v2(Bucket=bucket, MaxKeys=1)
    if obj_resp.get("KeyCount", 0) > 0:
        return False

    try:
        ver_resp = s3_client.list_object_versions(Bucket=bucket, MaxKeys=1)
        if ver_resp.get("Versions") or ver_resp.get("DeleteMarkers"):
            return False
    except ClientError:
        # Bucket is likely not versioned
        pass
    return True


def maybe_delete_bucket(s3_client, bucket: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete bucket %s", bucket)
        return False

    try:
        s3_client.delete_bucket(Bucket=bucket)
        return True
    except ClientError as exc:  # noqa: PERF203
        logger.warning("Could not delete bucket %s: %s", bucket, exc)
        return False


def run_cleanup(
    config: CleanupConfig,
    *,
    dry_run: bool = True,
    buckets_override: Optional[List[str]] = None,
    session: Optional[boto3.Session] = None,
    collect_details: bool = False,
    progress_callback: Optional[Callable[[Dict[str, object]], None]] = None,
) -> dict:
    now = datetime.now(timezone.utc)
    sess = session or boto3.Session(region_name=config.region_name)
    s3_client = sess.client("s3", region_name=config.region_name)

    response = s3_client.list_buckets()
    buckets = response.get("Buckets", [])

    summary = {
        "dry_run": dry_run,
        "buckets_scanned": len(buckets),
        "buckets_targeted": 0,
        "objects_deleted": 0,
        "versions_deleted": 0,
        "buckets_deleted": 0,
        "bucket_reports": [],
    }

    for bucket_info in buckets:
        bucket_name = bucket_info["Name"]
        creation_date = ensure_tz(bucket_info["CreationDate"])

        if not should_target_bucket(bucket_name, creation_date, config, now, s3_client, buckets_override):
            continue

        logger.info("Processing bucket %s", bucket_name)
        summary["buckets_targeted"] += 1

        objects_to_delete = collect_objects_for_deletion(s3_client, bucket_name, config, now)
        versions_to_delete = collect_versions_for_deletion(s3_client, bucket_name, config, now)

        if progress_callback:
            progress_callback(
                {
                    "resource": bucket_name,
                    "bucket": bucket_name,
                    "status": "planned",
                    "objects_planned": len(objects_to_delete),
                    "versions_planned": len(versions_to_delete),
                    "objects_deleted": 0,
                    "versions_deleted": 0,
                    "dry_run": dry_run,
                }
            )

        deleted_objects = delete_objects(
            s3_client,
            bucket_name,
            objects_to_delete,
            dry_run,
            config.max_delete_batch,
        )

        deleted_versions = delete_objects(
            s3_client,
            bucket_name,
            versions_to_delete,
            dry_run,
            config.max_delete_batch,
        )
        summary["objects_deleted"] += deleted_objects
        summary["versions_deleted"] += deleted_versions

        if progress_callback:
            progress_callback(
                {
                    "resource": bucket_name,
                    "bucket": bucket_name,
                    "status": "completed",
                    "objects_planned": len(objects_to_delete),
                    "versions_planned": len(versions_to_delete),
                    "objects_deleted": deleted_objects,
                    "versions_deleted": deleted_versions,
                    "dry_run": dry_run,
                }
            )

        if config.delete_empty_buckets:
            if bucket_is_empty(s3_client, bucket_name):
                if maybe_delete_bucket(s3_client, bucket_name, dry_run):
                    summary["buckets_deleted"] += 1
            else:
                logger.info("Bucket %s not empty; skipping deletion", bucket_name)

        if collect_details:
            summary["bucket_reports"].append(
                {
                    "bucket": bucket_name,
                    "objects_planned": len(objects_to_delete),
                    "versions_planned": len(versions_to_delete),
                    "objects_deleted": deleted_objects,
                    "versions_deleted": deleted_versions,
                }
            )

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean up S3 buckets with safe defaults.")
    parser.add_argument("--config", default="config.example.yaml", help="Path to cleanup config file")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply deletions (defaults to dry-run)",
    )
    parser.add_argument("--bucket", action="append", help="Process only the specified bucket(s)")
    parser.add_argument(
        "--delete-all-objects",
        action="store_true",
        help="Delete all objects in targeted buckets regardless of age",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show a dry-run plan and exit (no deletions).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt per bucket before applying deletions (requires --apply).",
    )
    parser.add_argument(
        "--include",
        action="append",
        dest="include_buckets",
        help="Temporarily include bucket(s) without editing the config.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        dest="exclude_buckets",
        help="Temporarily exclude bucket(s) without editing the config.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit summary as JSON.",
    )
    parser.add_argument(
        "--force-zero-retention",
        action="store_true",
        help="Allow apply when object_retention_days is 0 or below.",
    )
    parser.add_argument(
        "--force-delete-all",
        action="store_true",
        help="Allow apply when delete_all_objects is enabled.",
    )
    parser.add_argument(
        "--live",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show a live table while running (default on TTY).",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def policy_summary(config: CleanupConfig) -> str:
    if config.delete_all_objects:
        return "delete all objects in targeted buckets"
    if config.object_retention_days is None:
        return "object cleanup disabled"
    return f"delete objects older than {config.object_retention_days} day(s)"


def render_plan(summary: dict, config: CleanupConfig, *, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(summary, default=str, indent=2))
        return

    reports = summary.get("bucket_reports") or []
    print("\nPlan (dry-run)")
    print(f"  Buckets: {summary.get('buckets_targeted', 0)} of {summary.get('buckets_scanned', 0)} matched filters")
    if config.delete_all_objects:
        policy = "delete all objects in targeted buckets"
    elif config.object_retention_days is None:
        policy = "object cleanup disabled"
    else:
        policy = f"delete objects older than {config.object_retention_days} day(s)"
    print(f"  Policy: {policy}")
    print(f"  Versions: {'included' if config.include_versioned_objects else 'skipped'}")

    if not reports:
        print("  No buckets matched. Adjust filters or retention and retry.")
        return

    header = f"{'Bucket':40} {'Objs':>6} {'Vers':>6}"
    print(header)
    print("-" * len(header))
    total_objs = 0
    total_versions = 0
    for rep in reports:
        total_objs += rep.get("objects_planned", 0)
        total_versions += rep.get("versions_planned", 0)
        print(f"{rep['bucket']:<40} {rep.get('objects_planned', 0):>6} {rep.get('versions_planned', 0):>6}")
    print("-" * len(header))
    print(f"{'Totals':40} {total_objs:>6} {total_versions:>6}\n")


def prompt_bucket_selection(reports: List[dict]) -> List[str]:
    selected: List[str] = []
    for rep in reports:
        answer = input(
            f"Apply deletions for {rep['bucket']} (objs={rep.get('objects_planned', 0)}, "
            f"vers={rep.get('versions_planned', 0)})? [y/N]: "
        ).strip().lower()
        if answer in {"y", "yes"}:
            selected.append(rep["bucket"])
    return selected


def render_live_state(
    bucket_state: Dict[str, dict],
    messages: List[str],
    config: CleanupConfig,
    *,
    dry_run: bool,
) -> Panel:
    table = Table(title="S3 Cleanup", expand=True, box=box.MINIMAL)
    table.add_column("Bucket", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Objs", justify="right")
    table.add_column("Vers", justify="right")
    table.add_column("Deleted", justify="right")

    for bucket in sorted(bucket_state.keys()):
        info = bucket_state[bucket]
        status = info.get("status", "pending")
        objs_planned = info.get("objects_planned", 0)
        vers_planned = info.get("versions_planned", 0)
        deleted_total = info.get("objects_deleted", 0) + info.get("versions_deleted", 0)
        table.add_row(
            bucket,
            status,
            str(objs_planned),
            str(vers_planned),
            str(deleted_total),
        )

    warning_body = "\n".join(messages) if messages else "No warnings."
    warning_panel = Panel(warning_body, title="Messages", style="yellow", expand=True)

    footer = Text(
        f"Mode: {'dry-run' if dry_run else 'apply'} | Policy: {policy_summary(config)} | "
        f"Buckets processed: {len(bucket_state)}",
        style="bold",
    )

    grid = Table.grid(expand=True)
    grid.add_row(table, warning_panel)
    grid.add_row(footer)
    return Panel(Group(grid), box=box.SQUARE)


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    console = Console()
    live_enabled = args.live if getattr(args, "live", None) is not None else sys.stdout.isatty()
    if args.json_output:
        live_enabled = False

    try:
        config = CleanupConfig.from_file(args.config)
    except FileNotFoundError as exc:
        logger.error(exc)
        raise SystemExit(1) from exc
    except ValueError as exc:
        logger.error("Invalid config: %s", exc)
        raise SystemExit(1) from exc

    if args.delete_all_objects:
        config.delete_all_objects = True

    # One-off include/exclude tweaks without editing the config file.
    if args.include_buckets:
        for bucket in args.include_buckets:
            if bucket not in config.target_buckets:
                config.target_buckets.append(bucket)
    if args.exclude_buckets:
        for bucket in args.exclude_buckets:
            if bucket not in config.ignore_buckets:
                config.ignore_buckets.append(bucket)

    buckets_override = args.bucket
    bucket_state: Dict[str, dict] = {}
    messages: List[str] = []
    live_instance: Optional[Live] = None

    def progress_cb(report: Dict[str, object]) -> None:
        bucket_state[report["bucket"]] = report  # type: ignore[index]
        if live_instance:
            live_instance.update(
                render_live_state(
                    bucket_state,
                    messages,
                    config,
                    dry_run=not args.apply,
                )
            )

    if args.apply:
        if config.delete_all_objects and not args.force_delete_all:
            logger.error("delete_all_objects is enabled; use --force-delete-all to proceed with --apply.")
            raise SystemExit(1)
        if (
            config.object_retention_days is not None
            and config.object_retention_days <= 0
            and not args.force_zero_retention
            and not config.delete_all_objects
        ):
            logger.error(
                "object_retention_days is %s; raise it or pass --force-zero-retention to apply.",
                config.object_retention_days,
            )
            raise SystemExit(1)

    if args.plan or args.interactive:
        plan_summary = run_cleanup(
            config,
            dry_run=True,
            buckets_override=buckets_override,
            collect_details=True,
        )
        render_plan(plan_summary, config, json_output=args.json_output)

        if args.plan:
            return
        if not args.apply:
            logger.info("Interactive mode requires --apply; showing plan only.")
            return
        if not plan_summary.get("bucket_reports"):
            logger.info("No buckets matched filters; nothing to approve.")
            return

        approved = prompt_bucket_selection(plan_summary["bucket_reports"])
        if not approved:
            logger.info("No buckets approved; exiting.")
            return
        buckets_override = approved

    collect_details = args.json_output
    if live_enabled:
        with Live(
            render_live_state(bucket_state, messages, config, dry_run=not args.apply),
            console=console,
            refresh_per_second=4,
        ) as live:
            live_instance = live
            summary = run_cleanup(
                config,
                dry_run=not args.apply,
                buckets_override=buckets_override,
                collect_details=collect_details,
                progress_callback=progress_cb,
            )
            live_instance = None
    else:
        summary = run_cleanup(
            config,
            dry_run=not args.apply,
            buckets_override=buckets_override,
            collect_details=collect_details,
        )

    if args.json_output:
        print(json.dumps(summary, default=str, indent=2))

    logger.info(
        "Finished cleanup | dry_run=%s targeted=%s objects=%s versions=%s buckets_deleted=%s",
        summary["dry_run"],
        summary["buckets_targeted"],
        summary["objects_deleted"],
        summary["versions_deleted"],
        summary["buckets_deleted"],
    )


if __name__ == "__main__":
    main()
