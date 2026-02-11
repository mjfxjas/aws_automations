# AWS Automations - Product Overview

## Purpose
AWS Automations is a portfolio-ready multi-service AWS resource cleanup tool designed for safe, controlled deletion of unused AWS resources. The tool prioritizes safety through dry-run defaults, interactive approvals, and comprehensive safety switches.

## Key Features

### Safety-First Design
- **Dry-run by default** - All operations require explicit `--apply` flag for actual deletions
- **Interactive approval** - Per-bucket/resource confirmation before deletion
- **Safety switches** - Guards against zero retention and delete-all configurations
- **Age gates** - Configurable retention periods for buckets and objects

### Multi-Service Support
- **S3 Cleanup** - Buckets, objects, and versioned objects with prefix filtering
- **EC2 Cleanup** - Instance termination and volume management
- **Lambda Cleanup** - Function and layer cleanup
- **IAM Cleanup** - Role, policy, and user management
- **EBS Cleanup** - Volume and snapshot management
- **CloudWatch Cleanup** - Log group and metric cleanup

### Flexible Operation Modes
- **Direct service execution** - Target specific AWS services individually
- **Multi-service orchestrator** - Clean up all services with unified configuration
- **Interactive menu** - Guided cleanup through CLI interface
- **Live CLI view** - Real-time Rich table display with opt-out capability

### Advanced Filtering
- **Prefix-based filtering** - Target specific bucket/resource naming patterns
- **Target/ignore lists** - Explicit inclusion/exclusion of resources
- **Tag-based filtering** - Optional tag requirements for cleanup eligibility
- **Batch processing** - Efficient handling of large resource sets

## Target Users

### DevOps Engineers
- Managing development and staging environments
- Cleaning up after CI/CD pipeline runs
- Cost optimization through resource lifecycle management

### Cloud Administrators
- Regular maintenance of AWS accounts
- Compliance with data retention policies
- Bulk cleanup operations with audit trails

### Developers
- Personal AWS account maintenance
- Sandbox environment cleanup
- Learning AWS resource management best practices

## Use Cases

### Development Environment Cleanup
- Remove temporary buckets and objects after testing
- Clean up EC2 instances from development workflows
- Manage Lambda functions from experimental deployments

### Cost Optimization
- Identify and remove unused resources across multiple services
- Implement automated cleanup policies with safety controls
- Generate reports on resource usage patterns

### Compliance and Governance
- Enforce data retention policies across AWS services
- Maintain audit trails of cleanup operations
- Ensure consistent resource naming and tagging standards

### Disaster Recovery Testing
- Clean up resources after DR testing scenarios
- Validate backup and restore procedures
- Maintain clean baseline environments

## Value Proposition
AWS Automations provides enterprise-grade safety controls for AWS resource cleanup while maintaining the flexibility needed for diverse operational requirements. The tool's dry-run first approach and comprehensive safety switches make it suitable for production environments where accidental deletions could be catastrophic.