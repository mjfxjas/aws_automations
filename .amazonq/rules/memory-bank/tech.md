# AWS Automations - Technology Stack

## Programming Languages
- **Python 3.8+**: Primary language with modern features
- **YAML**: Configuration format for service settings
- **Shell**: Development and deployment scripts

## Core Dependencies

### Production Dependencies
- **boto3 (>=1.29)**: AWS SDK for Python with service clients
- **PyYAML (>=6.0)**: YAML configuration parsing
- **rich (>=13.7)**: Enhanced terminal output and formatting

### Development Dependencies
- **pytest (>=7.0)**: Testing framework with fixtures
- **pytest-cov (>=4.0)**: Code coverage reporting
- **black (>=22.0)**: Code formatting and style enforcement
- **flake8 (>=5.0)**: Linting and style checking
- **mypy (>=1.0)**: Static type checking

## Build System

### Modern Packaging (pyproject.toml)
```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"
```

### Legacy Support (setup.py)
- Fallback for older Python environments
- Console script entry point registration
- Package discovery and installation

### Version Management
- **Version**: 0.1.0 (Beta release)
- **Python Support**: 3.8, 3.9, 3.10, 3.11
- **Semantic Versioning**: Major.Minor.Patch format

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install package in development mode
pip install -e .
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
python -m pytest

# Coverage report
pytest --cov=aws_automations --cov-report=html
```

### Application Usage
```bash
# Interactive menu (recommended)
aws-cleanup-menu

# Direct CLI - Dry-run all services
aws-cleanup --config config.yaml

# Apply changes to specific service
aws-cleanup --config config.yaml --service s3 --apply

# Interactive approval mode
aws-cleanup --config config.yaml --interactive

# JSON output with verbose logging
aws-cleanup --config config.yaml --json --verbose

# Live progress display
aws-cleanup --config config.yaml --live
```

## AWS Integration

### Supported Services
- **S3**: Buckets, objects, versioning, lifecycle
- **EC2**: Instances, volumes, snapshots, AMIs
- **Lambda**: Functions, versions, aliases, layers
- **EBS**: Volumes, snapshots, encryption
- **CloudWatch**: Log groups, log streams, metrics
- **IAM**: Roles, users, policies, access keys

### Authentication Methods
- **AWS Credentials**: ~/.aws/credentials file
- **Environment Variables**: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
- **IAM Roles**: EC2 instance profiles, cross-account roles
- **AWS CLI Profiles**: Named profile support

### Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "ec2:*",
        "lambda:*",
        "logs:*",
        "iam:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Configuration Management

### YAML Schema
- **Global Settings**: region_name, output preferences
- **Service Blocks**: Individual service configuration
- **Filter Options**: retention_days, patterns, tags
- **Safety Settings**: batch limits, force flags

### Environment Variables
- **AWS_REGION**: Override default region
- **AWS_PROFILE**: Use specific AWS CLI profile
- **CONFIG_PATH**: Custom configuration file location

## Testing Strategy

### Unit Tests
- **Service Modules**: Individual cleanup logic testing
- **Configuration**: YAML parsing and validation
- **Filters**: Resource filtering and selection logic
- **Mocking**: AWS API responses with boto3 stubber

### Integration Tests
- **End-to-End**: Full cleanup workflow testing
- **AWS Services**: Real AWS resource interaction
- **Configuration**: Multiple config scenario testing
- **Error Handling**: Failure mode and recovery testing

### CI/CD Pipeline
- **GitHub Actions**: Automated testing on push/PR
- **Multi-Python**: Test across Python 3.8-3.11
- **Code Quality**: Linting, formatting, type checking
- **Coverage**: Minimum coverage thresholds

## Performance Considerations

### Batch Operations
- **S3**: 1000 objects per delete request
- **EC2**: Parallel instance termination
- **Lambda**: Concurrent function deletion
- **Pagination**: Efficient large dataset handling

### Rate Limiting
- **AWS API Limits**: Respect service throttling
- **Exponential Backoff**: Retry failed requests
- **Concurrent Requests**: Balanced parallelism
- **Resource Quotas**: Account limit awareness