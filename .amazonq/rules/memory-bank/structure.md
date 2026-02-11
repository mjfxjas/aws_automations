# AWS Automations - Project Structure

## Directory Organization

```
aws_automations/
├── aws_automations/          # Main package directory
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Multi-service orchestrator entry point
│   ├── menu.py              # Interactive CLI menu system
│   ├── start.py             # Interactive menu launcher
│   ├── config.py            # Configuration management and validation
│   ├── s3_cleanup.py        # S3 service cleanup implementation
│   ├── ec2_cleanup.py       # EC2 service cleanup implementation
│   ├── lambda_cleanup.py    # Lambda service cleanup implementation
│   ├── iam_cleanup.py       # IAM service cleanup implementation
│   ├── ebs_cleanup.py       # EBS service cleanup implementation
│   └── cloudwatch_cleanup.py # CloudWatch service cleanup implementation
├── tests/                   # Test suite
│   └── test_s3_cleanup.py   # S3 cleanup unit tests
├── data_sources/            # Documentation and reference materials
│   └── data_sources.md      # Data source documentation
├── .github/workflows/       # CI/CD pipeline definitions
│   └── test.yml            # GitHub Actions test workflow
├── config.example.yaml      # Example configuration template
├── config.yaml             # Active configuration file
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── setup.py               # Legacy setuptools configuration
├── pyproject.toml         # Modern Python project configuration
└── test_integration.py    # Integration test suite
```

## Core Components

### Entry Points
- **main.py** - Multi-service orchestrator supporting all AWS services
- **menu.py** - Interactive CLI interface for guided operations
- **start.py** - Simplified launcher for interactive menu
- **Individual service modules** - Direct service-specific cleanup tools

### Service Modules
Each service module follows a consistent pattern:
- **Configuration parsing** - Service-specific settings validation
- **Resource discovery** - AWS API integration for resource enumeration
- **Filtering logic** - Apply inclusion/exclusion rules and age gates
- **Safety checks** - Validate operations against safety switches
- **Execution engine** - Perform dry-run or actual deletions with progress tracking

### Configuration System
- **config.py** - Centralized configuration management
- **YAML-based configuration** - Human-readable service settings
- **Environment-specific configs** - Support for multiple deployment targets
- **Validation framework** - Ensure configuration integrity before execution

## Architectural Patterns

### Command Pattern
Each service implements a consistent command interface:
- Parse arguments and configuration
- Validate safety requirements
- Execute discovery phase
- Apply filtering rules
- Present plan to user
- Execute with appropriate safety controls

### Factory Pattern
Service selection and instantiation through:
- Dynamic module loading based on service parameter
- Consistent interface across all service implementations
- Centralized error handling and logging

### Strategy Pattern
Multiple execution strategies:
- **Dry-run strategy** - Simulation mode with detailed reporting
- **Interactive strategy** - User confirmation for each operation
- **Batch strategy** - Automated execution with safety controls
- **Live UI strategy** - Real-time progress display

### Observer Pattern
Progress tracking and reporting:
- Live table updates during execution
- JSON output for programmatic consumption
- Logging integration for audit trails
- Error aggregation and reporting

## Component Relationships

### Orchestrator Layer
- **main.py** coordinates multiple service modules
- Provides unified configuration and execution context
- Handles cross-service dependencies and ordering

### Service Layer
- Individual service modules operate independently
- Share common configuration and safety frameworks
- Implement service-specific AWS API interactions

### Interface Layer
- **menu.py** provides guided user experience
- Command-line interfaces support automation scenarios
- Output formatters support both human and machine consumption

### Configuration Layer
- **config.py** provides centralized settings management
- YAML files enable environment-specific customization
- Validation ensures operational safety

## Extension Points

### Adding New Services
1. Create new service module following existing patterns
2. Implement standard interface methods
3. Add service configuration schema
4. Update orchestrator service registry
5. Add corresponding menu options

### Custom Filtering
- Extend filtering logic in service modules
- Add new configuration parameters
- Implement custom tag-based rules
- Support complex resource selection criteria

### Output Formats
- Add new formatters for different output needs
- Integrate with external reporting systems
- Support custom audit trail formats
- Enable integration with monitoring tools