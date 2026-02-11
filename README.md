# AWS Automations - Multi-Service Cleanup

[![CI](https://github.com/mjfxjas/aws_automations/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/mjfxjas/aws_automations/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/aws-automations.svg)](https://pypi.org/project/aws-automations/)

Portfolio-ready AWS cleanup tool with safe defaults, dry-run first, and a live CLI view.

## Highlights
- Multi-service cleanup for S3, EC2, Lambda, EBS, CloudWatch, and IAM
- Dry-run by default; `--apply` required for deletions
- Filters: prefixes, target/ignore lists, optional tag requirement
- Age gates for buckets/objects; supports versioned buckets
- Live Rich table (opt-out with `--no-live`) plus JSON output when needed
- Safety switches to guard zero retention and delete-all modes
- Interactive per-bucket approval and batched deletes

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```
Runtime-only (no dev tools):
```bash
pip install -e .
```

## Configure
Copy `config.example.yaml` to `config.yaml` and adjust:
- `bucket_prefixes`, `target_buckets`, `ignore_buckets`
- `bucket_retention_days`, `object_retention_days`, `delete_all_objects`
- `include_versioned_objects`, `delete_empty_buckets`
- Optional `require_tag: { key, value }`

## Run (S3 direct)
Dry-run (default):
```bash
python -m aws_automations.s3_cleanup --config config.yaml
```
Plan view (no apply) with live table on TTY:
```bash
python -m aws_automations.s3_cleanup --config config.yaml --plan --live
```
Apply deletions for specific buckets:
```bash
python -m aws_automations.s3_cleanup --config config.yaml --apply \
  --bucket sandbox-a --bucket sandbox-b
```
Interactive approval per bucket:
```bash
python -m aws_automations.s3_cleanup --config config.yaml --apply --interactive
```
JSON summary (suppresses live UI):
```bash
python -m aws_automations.s3_cleanup --config config.yaml --plan --json
```
One-off include/exclude without editing config:
```bash
python -m aws_automations.s3_cleanup --config config.yaml --include temp-bucket --exclude ignore-me
```
Toggle live rendering:
```bash
python -m aws_automations.s3_cleanup --config config.yaml --no-live
```

## Run (Interactive Menu)
Start the interactive menu for guided cleanup:
```bash
aws-menu
```
Or run directly:
```bash
python -m aws_automations.start
```

## Run (multi-service orchestrator)
Clean up one or all services with a live table (default on TTY):
```bash
aws-cleanup --config config.yaml --service all --live
```
Or run via module:
```bash
python -m aws_automations.main --config config.yaml --service all --live
```
Focus on a single service (e.g., EC2) in dry-run:
```bash
python -m aws_automations.main --config config.yaml --service ec2
```
Emit JSON summary (suppresses live UI):
```bash
python -m aws_automations.main --config config.yaml --service lambda --json
```

Safety switches:
- `--force-zero-retention` required with `--apply` when `object_retention_days <= 0`
- `--force-delete-all` required with `--apply` when `delete_all_objects: true`

Add `--verbose` for debug logs.

## Tests
```bash
python -m pytest
```

## Smoke Test
Quick verification that install and CLI wiring are healthy:

```bash
python3 -m pip install --upgrade aws-automations
aws-cleanup --help
aws-menu --help
python3 -c "from importlib.metadata import version; print(version('aws-automations'))"
```

## Security Checks
- CI runs Bandit static security analysis on `aws_automations` (Python 3.11 job).
- Failing threshold is set to medium-or-higher severity/confidence.

```bash
bandit -r aws_automations --severity-level medium --confidence-level medium
```

## Changelog
See `CHANGELOG.md` for versioned release notes.

## Notes
- Uses paginated, batched deletes (S3 limits batches to 1,000 objects).
- Live UI is disabled automatically for JSON output or when stdout is not a TTY.
- Keep AWS credentials scoped to the buckets you intend to manage.
