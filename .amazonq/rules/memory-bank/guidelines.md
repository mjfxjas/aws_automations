# AWS Automations - Development Guidelines

## Code Quality Standards

### Import Organization (5/5 files)
```python
from __future__ import annotations  # Enable forward references

import logging                      # Standard library first
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import boto3                       # Third-party imports
import yaml
from botocore.exceptions import ClientError
```

### Type Annotations (5/5 files)
- **Mandatory**: All function parameters and return types must be annotated
- **Forward References**: Use `from __future__ import annotations` for complex types
- **Optional Types**: Use `Optional[Type]` for nullable parameters
- **Generic Types**: Use `List[str]`, `Dict[str, Any]` for collections

```python
def get_role_last_activity(iam_client, role_name: str) -> Optional[datetime]:
def run_iam_cleanup(config: dict, *, dry_run: bool = True, session: Optional[boto3.Session] = None) -> dict:
```

### Dataclass Usage (2/5 files)
```python
@dataclass
class CleanupConfig:
    """User configurable settings for S3 cleanup."""
    
    region_name: Optional[str] = None
    bucket_prefixes: List[str] = field(default_factory=list)
    delete_empty_buckets: bool = False
```

### Documentation Standards (5/5 files)
- **Module Docstrings**: Brief description in triple quotes
- **Class Docstrings**: Purpose and usage description
- **Function Docstrings**: Only when behavior is non-obvious
- **Inline Comments**: Explain complex logic, not obvious code

```python
"""AWS automation helpers."""

class BucketTagFilter:
    """Optional tag requirement for selecting buckets."""
```

## Structural Conventions

### Function Naming Patterns (5/5 files)
- **Service Functions**: `run_{service}_cleanup()` for main entry points
- **Helper Functions**: `should_target_{resource}()` for filtering logic
- **Action Functions**: `delete_{resource}()` for deletion operations
- **Utility Functions**: `ensure_tz()`, `resource_matches_patterns()`

### Error Handling Patterns (4/5 files)
```python
try:
    # AWS operation
    iam_client.delete_role(RoleName=role_name)
    logger.info("Deleted role %s", role_name)
    return True
except ClientError as exc:
    logger.warning("Could not delete role %s: %s", role_name, exc)
    return False
```

### Logging Standards (4/5 files)
```python
logger = logging.getLogger("iam_cleanup")  # Module-specific logger

logger.info("Processing role %s", role_name)      # Info for operations
logger.debug("Skipping %s: recent activity", role_name)  # Debug for filtering
logger.warning("Could not delete role %s: %s", role_name, exc)  # Warnings for errors
```

### Configuration Patterns (3/5 files)
```python
# Service-specific config access
retention_days = config.get("role_retention_days", 30)
ignore_list = config.get("ignore_roles", [])
patterns = config.get("name_patterns", [])

# Safe defaults with fallbacks
sess = session or boto3.Session(region_name=config.get("region_name"))
```

## Semantic Patterns

### AWS Client Initialization (4/5 files)
```python
def run_service_cleanup(config: dict, *, dry_run: bool = True, session: Optional[boto3.Session] = None) -> dict:
    sess = session or boto3.Session(region_name=config.get("region_name"))
    client = sess.client("service_name")
```

### Pagination Handling (3/5 files)
```python
paginator = client.get_paginator("list_resources")
resources = []
for page in paginator.paginate():
    resources.extend(page.get("Resources", []))
```

### Dry-Run Pattern (4/5 files)
```python
def delete_resource(client, resource_id: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete %s", resource_id)
        return False
    
    try:
        client.delete_resource(ResourceId=resource_id)
        logger.info("Deleted %s", resource_id)
        return True
    except ClientError as exc:
        logger.warning("Could not delete %s: %s", resource_id, exc)
        return False
```

### Resource Filtering Logic (4/5 files)
```python
def should_target_resource(resource: dict, config: dict, now: datetime) -> bool:
    name = resource["Name"]
    
    # Check ignore list
    if name in config.get("ignore_list", []):
        return False
    
    # Check name patterns
    if not resource_matches_patterns(name, config.get("name_patterns", [])):
        return False
    
    # Check age/activity
    retention_days = config.get("retention_days", 30)
    cutoff = now - timedelta(days=retention_days)
    
    return resource_date < cutoff
```

### Summary Report Structure (4/5 files)
```python
summary = {
    "dry_run": dry_run,
    "resources_scanned": len(resources),
    "resources_deleted": 0,
    "service_reports": [],
}

# Add to reports
summary["service_reports"].append({
    "resource_type": "role",
    "resource_name": resource_name,
})

return summary
```

## Internal API Patterns

### Module Exports (5/5 files)
```python
# __init__.py pattern
from .service_cleanup import run_cleanup as run_service_cleanup

__all__ = [
    "run_service_cleanup",
    "main",
    "__version__"
]
__version__ = "0.1.0"
```

### Configuration Loading (2/5 files)
```python
@staticmethod
def from_file(path: str | Path) -> "CleanupConfig":
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    raw = yaml.safe_load(config_path.read_text()) or {}
    return CleanupConfig.from_dict(raw)
```

### Timezone Handling (2/5 files)
```python
def ensure_tz(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

# Usage
now = datetime.now(timezone.utc)
last_activity = ensure_tz(role["RoleLastUsed"]["LastUsedDate"])
```

## Code Idioms

### Pattern Matching with fnmatch (3/5 files)
```python
def resource_matches_patterns(name: str, patterns: List[str]) -> bool:
    if not patterns:
        return True
    import fnmatch
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)
```

### Safe Dictionary Access (5/5 files)
```python
# Use .get() with defaults
config.get("retention_days", 30)
response.get("Resources", [])

# Check existence before access
if "RoleLastUsed" in role and "LastUsedDate" in role["RoleLastUsed"]:
    return role["RoleLastUsed"]["LastUsedDate"]
```

### List Comprehensions and Generators (3/5 files)
```python
# Extend lists from paginated responses
resources.extend(page.get("Resources", []))

# Convert to lists with defaults
bucket_prefixes=list(data.get("bucket_prefixes", []) or [])
```

### Exception Handling Patterns (4/5 files)
```python
# Specific exception catching
except ClientError as exc:
    logger.warning("Operation failed: %s", exc)

# Silent failures for optional operations
try:
    iam_client.delete_login_profile(UserName=user_name)
except ClientError:
    pass  # Login profile might not exist
```

## Testing Conventions

### Integration Test Structure (1/5 files)
```python
def test_function_name():
    """Test description."""
    try:
        # Test logic
        print("✓ Test passed")
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

# Test runner pattern
if __name__ == "__main__":
    tests = [test_imports, test_config_loading]
    passed = sum(1 for test in tests if test())
    
    if passed == len(tests):
        print("🎉 All tests passed!")
    else:
        sys.exit(1)
```

### Path Manipulation (2/5 files)
```python
# Add package to path for testing
sys.path.insert(0, str(Path(__file__).parent))

# Path handling with pathlib
config_path = Path(path)
if not config_path.exists():
    raise FileNotFoundError(f"Config file not found: {config_path}")
```