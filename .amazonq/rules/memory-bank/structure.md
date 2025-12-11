# AWS Automations - Project Structure

## Directory Organization

```
aws_automations/
├── .amazonq/rules/memory-bank/     # Amazon Q documentation
├── .github/workflows/              # CI/CD pipeline
├── aws_automations/               # Main package source
├── tests/                         # Unit tests
├── config.example.yaml           # Configuration template
├── config.yaml                   # Active configuration
├── pyproject.toml                # Modern Python packaging
├── setup.py                      # Legacy packaging support
└── requirements*.txt             # Dependencies
```

## Core Components

### Main Package (`aws_automations/`)
- **`main.py`**: CLI entry point and argument parsing
- **`menu.py`**: Interactive menu system with Rich UI
- **`start.py`**: Entry point for interactive menu
- **`config.py`**: Configuration loading and validation
- **Service Modules**: Individual cleanup implementations
  - `s3_cleanup.py` - S3 buckets and objects
  - `ec2_cleanup.py` - EC2 instances and volumes
  - `lambda_cleanup.py` - Lambda functions and versions
  - `ebs_cleanup.py` - EBS volumes and snapshots
  - `cloudwatch_cleanup.py` - CloudWatch logs
  - `iam_cleanup.py` - IAM roles, users, policies

### Configuration System
- **`config.example.yaml`**: Template with all available options
- **`config.yaml`**: Active configuration (gitignored)
- **Service-specific sections**: Each AWS service has dedicated config block
- **Global settings**: Region, credentials, and cross-service options

### Testing Infrastructure
- **`tests/`**: Unit test suite with pytest
- **`test_integration.py`**: Integration testing scenarios
- **`.github/workflows/test.yml`**: Automated CI pipeline

## Architectural Patterns

### Service Module Architecture
Each service cleanup module follows a consistent pattern:
```python
class ServiceCleanup:
    def __init__(self, config, session)
    def list_resources(self) -> List[Resource]
    def filter_resources(self, resources) -> List[Resource]
    def delete_resources(self, resources, dry_run=True)
    def generate_report(self) -> Dict
```

### Configuration Hierarchy
1. **Global Config**: Region, credentials, output format
2. **Service Config**: Service-specific retention rules
3. **Runtime Args**: CLI overrides and safety flags
4. **Environment**: AWS credentials and region fallbacks

### Safety Architecture
- **Dry-run Default**: All operations preview before execution
- **Explicit Apply**: `--apply` flag required for deletions
- **Force Flags**: Additional confirmation for destructive operations
- **Batch Limits**: Configurable limits prevent accidental mass deletion

## Component Relationships

### CLI Flow
```
┌─ Interactive Menu ─┐    ┌─ Direct CLI ─┐
│   menu.py          │    │   main.py    │
│   start.py         │    │              │
└────────┬───────────┘    └──────┬───────┘
         │                       │
         └───────┬───────────────┘
                 ↓
         config.py → service_modules → AWS APIs
             ↓            ↓              ↓
        validation   filtering      operations
             ↓            ↓              ↓
       error_handling  reporting    results
```

### Service Integration
- **Interactive Menu**: Rich-formatted guided interface (`aws-cleanup-menu`)
- **Direct CLI**: Command-line interface (`aws-cleanup`)
- **Independent Modules**: Each service can run standalone
- **Shared Configuration**: Common config patterns across services
- **Unified Reporting**: Consistent output format and structure
- **Cross-Service Dependencies**: EC2 cleanup includes EBS volumes

### Data Flow
1. **Configuration Loading**: YAML → Python objects
2. **Resource Discovery**: AWS APIs → Resource lists
3. **Filtering**: Rules → Filtered resources
4. **Operation**: Dry-run/Apply → Results
5. **Reporting**: Results → JSON/Text output

## Extension Points

### Adding New Services
1. Create `{service}_cleanup.py` module
2. Implement standard cleanup interface
3. Add configuration section to YAML schema
4. Register in main CLI dispatcher

### Custom Filters
- Extend filter methods in service modules
- Add new configuration options
- Implement tag-based or metadata filtering
- Support regex patterns and complex rules

### Output Formats
- Extend reporting methods
- Add new output formatters
- Implement custom report templates
- Support external integrations (webhooks, APIs)