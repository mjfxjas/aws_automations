from setuptools import setup, find_packages

setup(
    name="aws-automations",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "boto3>=1.26.0",
        "PyYAML>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "aws-cleanup=aws_automations.main:main",
            "aws-cleanup-menu=aws_automations.start:interactive_menu",
        ],
    },
    python_requires=">=3.8",
)