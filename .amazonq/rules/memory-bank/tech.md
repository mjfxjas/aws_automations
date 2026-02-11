# AWS Automations - Technology Stack

## Programming Languages

### Python 3.8+
- **Primary language** for all implementation
- **Minimum version**: Python 3.8
- **Supported versions**: 3.8, 3.9, 3.10, 3.11
- **Type hints** used throughout codebase for better IDE support

## Core Dependencies

### Production Dependencies
- **boto3 >= 1.26.0** - AWS SDK for Python
  - Primary interface for all AWS service interactions
  - Handles authentication, pagination, and error handling
- **PyYAML >= 6.0** - YAML configuration file parsing
  - Human-readable configuration format
  - Supports complex nested structures

### Development Dependencies
- **pytest >= 7.0.0** - Testing framework
- **pytest-cov >= 4.0.0** - Code coverage reporting
- **black >= 22.0.0** - Code formatting
- **flake8 >= 5.0.0** - Linting and style checking
- **mypy >= 1.0.0** - Static type checking

## Build System

### Modern Python Packaging
- **pyproject.toml** - Primary project configuration
- **setuptools >= 45** - Build backend
- **wheel** - Distribution format

### Legacy Support
- **setup.py** - Maintained for backward compatibility
- **requirements.txt** - Production dependency pinning
- **requirements-dev.txt** - Development dependency management

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install development dependencies
pip install -r requirements-dev.txt
```

### Code Quality
```bash
# Format code
black aws_automations/ tests/

# Lint code
flake8 aws_automations/ tests/

# Type checking
mypy aws_automations/

# Run tests
pytest

# Run tests with coverage
pytest --cov=aws_automations --cov-report=html
```

### Package Installation
```bash
# Development installation
pip install -e .

# Production installation
pip install .
```

## Console Scripts

### Entry Points
- **aws-cleanup** - Multi-service orchestrator (`aws_automations.main:main`)
- **aws-menu** - Interactive menu interface (`aws_automations.menu:interactive_menu`)

### Usage Examples
```bash
# Multi-service cleanup
aws-cleanup --config config.yaml --service all --apply

# Interactive menu
aws-menu
```

## Configuration Management

### YAML Configuration
- **config.yaml** - Active configuration
- **config.example.yaml** - Template with documentation
- Supports environment-specific overrides
- Validation through Python schema checking

### Environment Variables
- **AWS credentials** - Standard AWS credential chain
- **AWS_PROFILE** - Profile selection
- **AWS_REGION** - Default region override

## Testing Framework

### Test Structure
- **Unit tests** - Individual component testing
- **Integration tests** - End-to-end workflow validation
- **Mock testing** - AWS service interaction simulation

### Test Configuration
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

## Code Style

### Black Configuration
```toml
[tool.black]
line-length = 120
target-version = ['py38']
```

### MyPy Configuration
```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
```

## CI/CD Pipeline

### GitHub Actions
- **test.yml** - Automated testing workflow
- Runs on multiple Python versions
- Includes code quality checks
- Generates coverage reports

### Workflow Triggers
- Pull request validation
- Main branch protection
- Release automation support

## AWS Integration

### Authentication Methods
- **IAM roles** - Recommended for production
- **Access keys** - Development and testing
- **AWS CLI profiles** - Local development
- **Instance profiles** - EC2-based execution

### Required Permissions
Service-specific IAM permissions for:
- Resource enumeration (List* operations)
- Resource deletion (Delete* operations)
- Tag-based filtering (Get* operations)

### Rate Limiting
- Built-in retry logic with exponential backoff
- Respects AWS API rate limits
- Batch operations for efficiency

## Deployment Options

### Local Execution
- Direct Python module execution
- Virtual environment isolation
- Configuration file management

### Container Deployment
- Dockerfile support (can be added)
- Environment variable configuration
- Credential mounting strategies

### Lambda Deployment
- Serverless execution model
- Event-driven cleanup schedules
- CloudWatch integration for monitoring