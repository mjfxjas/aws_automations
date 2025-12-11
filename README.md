# AWS Automations – S3 Cleanup

Portfolio-ready S3 cleanup tool with safe defaults, dry-run first, and a live CLI view.

## Highlights
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
pip install -r requirements-dev.txt
```

## Configure
Copy `config.example.yaml` to `config.yaml` and adjust:
- `bucket_prefixes`, `target_buckets`, `ignore_buckets`
- `bucket_retention_days`, `object_retention_days`, `delete_all_objects`
- `include_versioned_objects`, `delete_empty_buckets`
- Optional `require_tag: { key, value }`

## Run
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

Safety switches:
- `--force-zero-retention` required with `--apply` when `object_retention_days <= 0`
- `--force-delete-all` required with `--apply` when `delete_all_objects: true`

Add `--verbose` for debug logs.

## Tests
```bash
python -m pytest
```

## Notes
- Uses paginated, batched deletes (S3 limits batches to 1,000 objects).
- Live UI is disabled automatically for JSON output or when stdout is not a TTY.
- Keep AWS credentials scoped to the buckets you intend to manage.
