#!/usr/bin/env python3
"""Simple integration test to verify all modules load correctly."""

import sys
from pathlib import Path

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all cleanup modules can be imported."""
    try:
        from aws_automations import (
            run_s3_cleanup,
            run_ec2_cleanup,
            run_lambda_cleanup,
            run_ebs_cleanup,
            run_cloudwatch_cleanup,
            run_iam_cleanup,
            main
        )
        print("✓ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_config_loading():
    """Test that config can be loaded."""
    try:
        from aws_automations.main import load_config
        config = load_config("config.yaml")
        
        # Check that all service configs are present
        services = ["s3", "ec2", "lambda", "ebs", "cloudwatch", "iam"]
        for service in services:
            if service not in config:
                print(f"✗ Missing {service} config")
                return False
        
        print("✓ Config loaded and validated successfully")
        return True
    except Exception as e:
        print(f"✗ Config error: {e}")
        return False

if __name__ == "__main__":
    print("Running integration tests...")
    
    tests = [test_imports, test_config_loading]
    passed = 0
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! The AWS automation tool is ready to use.")
    else:
        print("❌ Some tests failed. Check the errors above.")
        sys.exit(1)