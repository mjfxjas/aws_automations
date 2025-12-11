# AWS Automations - Product Overview

## Purpose
AWS Automations is a portfolio-ready multi-service cleanup tool that automatically identifies and removes unused AWS resources across 6 core services. Built with a safety-first approach, it provides comprehensive resource management with configurable rules and dry-run capabilities.

## Value Proposition
- **Cost Optimization**: Automatically identifies and removes unused AWS resources to reduce monthly bills
- **Safety First**: Dry-run by default with explicit `--apply` flag required for actual deletions
- **Multi-Service Coverage**: Single tool handles S3, EC2, Lambda, EBS, CloudWatch Logs, and IAM cleanup
- **Enterprise Ready**: Configurable filters, batch operations, and detailed reporting for production use

## Key Features

### Core Capabilities
- **Dry-Run Mode**: All operations preview changes before execution
- **Configurable Filters**: Age-based retention, name patterns, tag requirements, and service-specific rules
- **Batch Operations**: Efficient processing with AWS pagination and batching
- **Detailed Reporting**: Comprehensive output with JSON format support
- **Safety Switches**: Force flags required for destructive operations

### Service Coverage
1. **S3**: Bucket and object cleanup with versioning support
2. **EC2**: Instance termination and volume cleanup
3. **Lambda**: Function deletion with version management
4. **EBS**: Volume and snapshot cleanup
5. **CloudWatch Logs**: Log group and stream management
6. **IAM**: Role, user, and policy cleanup with dependency handling

### Advanced Features
- **Live Planning**: Real-time TTY rendering for S3 operations
- **Service-Specific Logic**: Tailored cleanup rules per AWS service
- **Dependency Management**: Automatic cleanup of related resources
- **Usage Analytics**: Lambda invocation history and CloudWatch metrics integration

## Target Users

### DevOps Engineers
- Automate resource cleanup in development and staging environments
- Implement cost optimization strategies across AWS accounts
- Maintain clean infrastructure with scheduled cleanup jobs

### Cloud Architects
- Design cost-effective resource lifecycle management
- Implement governance policies for resource retention
- Ensure compliance with organizational cleanup standards

### Development Teams
- Clean up temporary resources from testing and experimentation
- Maintain organized development environments
- Reduce AWS costs through automated resource management

## Use Cases

### Development Environment Cleanup
- Remove temporary EC2 instances and volumes after testing
- Clean up S3 buckets from development workflows
- Delete unused Lambda functions and their logs

### Cost Optimization
- Identify and remove aged resources across all services
- Clean up orphaned EBS volumes and snapshots
- Remove inactive IAM roles and policies

### Compliance and Governance
- Enforce retention policies across AWS services
- Maintain audit trails of cleanup operations
- Ensure consistent resource naming and tagging standards