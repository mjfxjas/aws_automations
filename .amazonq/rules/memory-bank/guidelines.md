# AWS Automations - Development Guidelines

## Code Quality Standards

### Import Organization (5/5 files follow this pattern)
```python
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
```
- **Future annotations** - Always use `from __future__ import annotations` for forward compatibility
- **Standard library first** - Group standard library imports together
- **Third-party imports** - Separate section for external dependencies
- **Local imports** - Project-specific imports last
- **Alphabetical ordering** - Within each group, maintain alphabetical order

### Type Annotations (5/5 files demonstrate this)
```python
def run_iam_cleanup(
    config: dict,
    *,
    dry_run: bool = True,
    session: Optional[boto3.Session] = None,
    progress_callback: Optional[Callable[[Dict[str, object]], None]] = None,
) -> dict:
```
- **Complete type coverage** - All function parameters and return types annotated
- **Optional types** - Use `Optional[Type]` for nullable parameters
- **Complex types** - Leverage `Dict`, `List`, `Callable` for structured data
- **Union types** - Use `str | Path` syntax for modern Python versions

### Dataclass Usage (2/5 files show this pattern)
```python
@dataclass
class CleanupConfig:
    """User configurable settings for S3 cleanup."""
    
    region_name: Optional[str] = None
    bucket_prefixes: List[str] = field(default_factory=list)
    ignore_buckets: List[str] = field(default_factory=list)
    delete_empty_buckets: bool = False
```
- **Immutable defaults** - Use `field(default_factory=list)` for mutable defaults
- **Type hints** - All fields must have type annotations
- **Documentation** - Include class-level docstrings
- **Optional fields** - Use `Optional[Type]` with `None` defaults

## Structural Conventions

### Function Naming Patterns (5/5 files follow this)
- **Verb-based naming** - Functions start with action verbs (`run_`, `delete_`, `should_`, `get_`)
- **Snake case** - All functions use snake_case naming
- **Descriptive names** - Names clearly indicate function purpose
- **Consistent prefixes** - Related functions share common prefixes

### Error Handling Strategy (4/5 files demonstrate this)
```python
try:
    iam_client.delete_role(RoleName=role_name)
    logger.info("Deleted role %s", role_name)
    return True
except ClientError as exc:
    logger.warning("Could not delete role %s: %s", role_name, exc)
    return False
```
- **Specific exceptions** - Catch `ClientError` for AWS operations
- **Logging integration** - Log both success and failure cases
- **Boolean returns** - Return success/failure status for operations
- **Graceful degradation** - Continue processing after individual failures

### Logging Standards (4/5 files implement this)
```python
logger = logging.getLogger("iam_cleanup")

logger.info("Processing role %s", role_name)
logger.debug("Skipping %s: recent activity", role_name)
logger.warning("Could not delete role %s: %s", role_name, exc)
```
- **Module-level loggers** - One logger per module with descriptive name
- **Parameterized messages** - Use `%s` formatting for performance
- **Appropriate levels** - Info for operations, debug for filtering, warning for errors
- **Structured logging** - Include relevant context in log messages

## Textual Standards

### Documentation Patterns (5/5 files follow this)
```python
def ensure_tz(dt: datetime) -> datetime:
    """Ensure datetime has timezone information."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
```
- **Docstring format** - Use triple quotes with concise descriptions
- **Function documentation** - Brief, action-oriented descriptions
- **Class documentation** - Explain purpose and usage patterns
- **Parameter documentation** - Include when behavior is non-obvious

### Variable Naming (5/5 files demonstrate this)
- **Descriptive names** - `retention_days`, `last_activity`, `cutoff`
- **Consistent terminology** - Use same terms across modules (`dry_run`, `config`)
- **Abbreviation avoidance** - Prefer full words over abbreviations
- **Context clarity** - Names indicate data type and purpose

### String Formatting (4/5 files show this pattern)
```python
logger.info("Processing role %s", role_name)
f"Config file not found: {config_path}"
```
- **Logger formatting** - Use `%s` style for logger messages
- **F-strings** - Use f-strings for general string formatting
- **Consistent style** - Don't mix formatting styles within functions

## Practices Followed Throughout Codebase

### Configuration Management (3/5 files implement this)
```python
@staticmethod
def from_file(path: str | Path) -> "CleanupConfig":
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    raw = yaml.safe_load(config_path.read_text()) or {}
    return CleanupConfig.from_dict(raw)
```
- **Static factory methods** - Use `from_file()` and `from_dict()` patterns
- **Path handling** - Accept both string and Path objects
- **Validation** - Check file existence before processing
- **Safe defaults** - Handle empty/None configuration gracefully

### AWS Client Management (4/5 files follow this)
```python
sess = session or boto3.Session(region_name=config.get("region_name"))
iam_client = sess.client("iam")
```
- **Session injection** - Accept optional session parameter for testing
- **Default sessions** - Create session with region from config
- **Client creation** - Create service clients from session
- **Resource cleanup** - No explicit cleanup needed for clients

### Dry Run Implementation (4/5 files implement this)
```python
def delete_role(iam_client, role_name: str, dry_run: bool) -> bool:
    if dry_run:
        logger.info("Dry run: would delete role %s", role_name)
        return False
    
    # Actual deletion logic here
```
- **Early return** - Check dry_run flag at function start
- **Consistent messaging** - Use "Dry run: would..." format
- **Boolean returns** - Return False for dry runs, True for actual operations
- **Safety first** - Default to dry_run=True in function signatures

## Semantic Patterns Overview

### Resource Filtering Pattern (4/5 files use this)
```python
def should_target_role(role: dict, config: dict, now: datetime, iam_client) -> bool:
    # Skip system resources
    if role["Path"].startswith("/aws-service-role/"):
        return False
    
    # Check ignore list
    if role_name in config.get("ignore_roles", []):
        return False
    
    # Check patterns and retention
    # Return True if resource should be processed
```
- **Boolean predicates** - Functions return True/False for inclusion
- **Multiple criteria** - Check system resources, ignore lists, patterns, age
- **Early returns** - Exit immediately when exclusion criteria met
- **Consistent naming** - Use `should_target_*` naming convention

### Progress Callback Pattern (3/5 files implement this)
```python
if progress_callback:
    progress_callback({
        "resource": role_name,
        "resource_type": "role", 
        "status": "planned",
        "deleted": 0,
    })
```
- **Optional callbacks** - Check for None before calling
- **Structured data** - Pass dictionaries with consistent keys
- **Status tracking** - Include resource info, type, and operation status
- **Consistent schema** - Same keys across all service modules

### Pagination Handling (3/5 files show this)
```python
roles_paginator = iam_client.get_paginator("list_roles")
roles = []
for page in roles_paginator.paginate():
    roles.extend(page.get("Roles", []))
```
- **Paginator usage** - Use AWS SDK paginators for large result sets
- **List accumulation** - Collect all results before processing
- **Safe access** - Use `.get()` with defaults for optional keys
- **Consistent pattern** - Same approach across all AWS service calls

### Entry Point Patterns (3/5 files demonstrate this)
```python
# Console script entry points
"aws-cleanup=aws_automations.main:main"
"aws-menu=aws_automations.menu:interactive_menu"

# Module execution
if __name__ == "__main__":
    interactive_menu()
```
- **Console scripts** - Define entry points in setup configuration
- **Module execution** - Support `python -m` execution pattern
- **Function delegation** - Entry points call main functions
- **Consistent naming** - Use descriptive command names

### Summary Return Pattern (4/5 files implement this)
```python
summary = {
    "dry_run": dry_run,
    "roles_scanned": len(roles),
    "roles_deleted": 0,
    "iam_reports": [],
}
return summary
```
- **Dictionary returns** - Return structured summary data
- **Consistent keys** - Use same naming patterns across services
- **Metrics tracking** - Include counts of scanned and processed resources
- **Report lists** - Maintain detailed lists of affected resources